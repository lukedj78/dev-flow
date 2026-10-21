/*
 * extract.js — measure a rendered page, emit one JSON snapshot.
 *
 * ONE file, TWO delivery paths, deliberately:
 *   1. injected   — the agent evaluates this in its own browser; the IIFE's value is the snapshot.
 *   2. pasted     — the user pastes it into their own DevTools console; it downloads snapshot.json.
 * The second path is what makes a login or a bot challenge a non-event: the browser is the user's,
 * they are already signed in, and nothing here touches a credential or defeats a check.
 *
 * It reads COMPUTED styles, never the authored CSS. A stylesheet declares what is possible; the DOM
 * says what is painted. On a Tailwind or CSS-in-JS site the stylesheet declares the whole utility
 * palette, so reading the source would report the framework's defaults as the brand's system.
 *
 * Nothing leaves the page. There is no fetch in this file.
 */
window.__SNAPSHOT__ = (function extract(options) {
  "use strict";

  var opt = options || {};
  var MODE = opt.mode === "app" ? "app" : "site";
  var DOWNLOAD = opt.download === true;
  var MAX_CANDIDATES = 24;

  var notes = [];
  function note(s) { if (notes.indexOf(s) === -1) notes.push(s); }

  /* ---------------------------------------------------------------- colour */

  // getComputedStyle hands back `oklch()` / `lab()` / `color-mix()` untouched in current engines, so
  // every colour is PAINTED on a 1x1 canvas and read back as bytes. Reading `ctx.fillStyle` is not
  // enough and the first version of this file got it wrong: Canvas2D now implements CSS Color 4, so
  // assigning `oklch(0.55 0.21 258)` and reading the property back returns that same string. Only
  // getImageData forces the engine to resolve it to sRGB, which is what a hex token needs.
  var cvs = document.createElement("canvas");
  cvs.width = cvs.height = 1;
  var ctx = cvs.getContext("2d", { willReadFrequently: true });

  var colorCache = Object.create(null);

  function hex2(n) { var s = n.toString(16); return s.length === 1 ? "0" + s : s; }

  function normColor(raw) {
    if (!raw) return null;
    var v = String(raw).trim();
    if (!v || v === "none" || v === "currentcolor" || v === "currentColor") return null;
    if (v === "transparent" || v === "rgba(0, 0, 0, 0)") return null;
    if (v in colorCache) return colorCache[v];
    var out = null;
    try {
      // Two probes with OPPOSITE resets. A value the engine rejects leaves fillStyle at the reset,
      // so the two reads come back black and white and disagree; a value it parses paints the same
      // pixel both times. Resetting to the same colour twice would report every invalid value as
      // that colour, which is how the first version of this would have logged a typo as black.
      var px1 = probe(v, "#000000");
      var px2 = probe(v, "#ffffff");
      if (px1 && px2 && px1 === px2) out = px1;
    } catch (e) { out = null; }
    colorCache[v] = out;
    return out;
  }

  function probe(value, reset) {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = reset;
    ctx.fillStyle = value;              // an invalid value leaves the reset in place
    ctx.fillRect(0, 0, 1, 1);
    var d = ctx.getImageData(0, 0, 1, 1).data;
    if (d[3] === 0) return null;        // fully transparent carries no design
    if (d[3] === 255) return "#" + hex2(d[0]) + hex2(d[1]) + hex2(d[2]);
    // Semi-transparent: the painted pixel is the value composited over `ground`, so flattening it to
    // hex would bake the ground in and lose the thing that matters. Kept as authored — the alpha IS
    // the token. `analyze.py` treats any value that does not start with `#` as translucent.
    return value;
  }

  /* ------------------------------------------------------- what to exclude */

  // A consent dialog is a third party's design sitting on top of the brand's. Measured with it in,
  // its greys and its 4px radius land in the palette and the radius scale.
  var CONSENT_WORDS = /(cookie|consent|gdpr|privacy[-_]?(banner|notice|prefs)|onetrust|cookiebot|usercentrics|klaro|didomi|iubenda|trustarc|cmp[-_]?(banner|container)|borlabs|complianz)/i;
  var CONSENT_TEXT = /(we use cookies|utilizziamo i cookie|questo sito utilizza|accept all|accetta tutti|manage (your )?(cookies|preferences)|gestisci (i )?cookie|reject all|rifiuta)/i;

  function isConsent(el) {
    for (var n = el; n && n !== document.documentElement; n = n.parentElement) {
      var id = n.id || "";
      var cls = (typeof n.className === "string") ? n.className : "";
      if (CONSENT_WORDS.test(id) || CONSENT_WORDS.test(cls)) return true;
      var role = n.getAttribute && n.getAttribute("role");
      if ((role === "dialog" || role === "alertdialog" || n.tagName === "DIALOG") &&
          CONSENT_TEXT.test((n.textContent || "").slice(0, 400))) return true;
    }
    return false;
  }

  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEMPLATE: 1, HEAD: 1, META: 1, LINK: 1, TITLE: 1, BR: 1, WBR: 1 };

  /* -------------------------------------------------------------- counters */

  function Bag() { this.m = Object.create(null); }
  Bag.prototype.add = function (key, weight) {
    if (key === null || key === undefined || key === "") return;
    var k = String(key);
    var e = this.m[k] || (this.m[k] = { elements: 0, weight: 0 });
    e.elements += 1;
    e.weight += (weight || 0);
  };
  Bag.prototype.list = function (weightName, limit) {
    var out = [];
    for (var k in this.m) {
      var row = { value: k, elements: this.m[k].elements };
      row[weightName || "weight"] = Math.round(this.m[k].weight);
      out.push(row);
    }
    out.sort(function (a, b) {
      var d = b[weightName || "weight"] - a[weightName || "weight"];
      return d !== 0 ? d : b.elements - a.elements;
    });
    return limit ? out.slice(0, limit) : out;
  };

  function Tally() { this.m = Object.create(null); }
  Tally.prototype.add = function (k) {
    if (k === null || k === undefined || k === "") return;
    this.m[String(k)] = (this.m[String(k)] || 0) + 1;
  };
  Tally.prototype.obj = function () { return this.m; };

  /* --------------------------------------------------------------- helpers */

  function px(v) {
    var n = parseFloat(v);
    return isFinite(n) ? Math.round(n * 100) / 100 : null;
  }

  function ownChars(el) {
    var n = 0;
    for (var i = 0; i < el.childNodes.length; i++) {
      var c = el.childNodes[i];
      if (c.nodeType === 3) n += (c.nodeValue || "").replace(/\s+/g, " ").trim().length;
    }
    return n;
  }

  function visible(el, cs, rect) {
    if (cs.display === "none" || cs.visibility === "hidden" || cs.visibility === "collapse") return false;
    if (parseFloat(cs.opacity) === 0) return false;
    if (rect.width <= 0 || rect.height <= 0) return false;
    return true;
  }

  // The painted layer is often a child of the <a>, so a button read off the anchor reports no
  // background and no radius. Walk down to the descendant that actually carries the paint.
  function paintedLayer(el) {
    var best = el, bestScore = -1, stack = [el], depth = 0;
    while (stack.length && depth < 400) {
      var n = stack.pop(); depth++;
      var cs; try { cs = getComputedStyle(n); } catch (e) { continue; }
      var bg = normColor(cs.backgroundColor);
      var bw = px(cs.borderTopWidth) || 0;
      var r = n.getBoundingClientRect();
      var score = (bg ? 2 : 0) + (bw > 0 ? 1 : 0) + ((px(cs.borderTopLeftRadius) || 0) > 0 ? 1 : 0);
      if (score > bestScore && r.width > 0 && r.height > 0) { best = n; bestScore = score; }
      for (var i = 0; i < n.children.length; i++) stack.push(n.children[i]);
    }
    return best;
  }

  function boxOf(el) {
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return {
      width: Math.round(r.width), height: Math.round(r.height),
      // WHERE it is, in page coordinates, so the component can be cropped out of a screenshot and
      // compared pixel for pixel against the same component rebuilt from the tokens. Without this
      // the only available check is "does the computed style equal the token", which passes happily
      // while the token itself is wrong — measured on adidas.it, where a pill-shaped system was
      // derived from one 24px dot and nothing in the pipeline objected.
      rect: { x: Math.round(r.left + window.scrollX), y: Math.round(r.top + window.scrollY),
              w: Math.round(r.width), h: Math.round(r.height) },
      font: cs.fontFamily, fontSize: px(cs.fontSize), fontWeight: cs.fontWeight,
      lineHeight: px(cs.lineHeight), letterSpacing: px(cs.letterSpacing),
      textTransform: cs.textTransform !== "none" ? cs.textTransform : null,
      color: normColor(cs.color), background: normColor(cs.backgroundColor),
      backgroundImage: cs.backgroundImage !== "none" ? cs.backgroundImage : null,
      borderWidth: px(cs.borderTopWidth), borderColor: normColor(cs.borderTopColor),
      borderStyle: cs.borderTopStyle !== "none" ? cs.borderTopStyle : null,
      radius: px(cs.borderTopLeftRadius),
      radiusIsPill: px(cs.borderTopLeftRadius) >= Math.round(r.height) / 2 && r.height > 0,
      padding: [px(cs.paddingTop), px(cs.paddingRight), px(cs.paddingBottom), px(cs.paddingLeft)],
      gap: cs.gap && cs.gap !== "normal" ? px(cs.rowGap) : null,
      shadow: cs.boxShadow !== "none" ? cs.boxShadow : null,
      transition: cs.transitionDuration !== "0s"
        ? { duration: cs.transitionDuration, easing: cs.transitionTimingFunction, property: cs.transitionProperty }
        : null,
      // The label, so a rebuilt control can be compared against the original INCLUDING its type —
      // which is where a brand is most itself. Capped and site-mode only: in `app` mode a control's
      // text is somebody's data, and the rule there is shape without strings.
      label: (MODE === "site"
              ? (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40)
              : null) || null
    };
  }

  /* ------------------------------------------------------------- the walk */

  var colors = { text: new Bag(), background: new Bag(), border: new Bag(), fill: new Bag() };
  var gradients = new Bag();
  var typeBag = Object.create(null);
  var padT = new Tally(), marT = new Tally(), gapT = new Tally(), radT = new Tally();
  var shadowBag = new Bag(), containerT = new Tally(), gridBag = new Bag();
  var fontFamilies = new Bag();
  var textShape = {
    headings: [], paragraphs: [], ctaLabels: [], you: 0, we: 0, exclamations: 0,
    digits: 0, upperHeadings: 0, titleHeadings: 0, commaPattern: 0
  };
  var samples = [];

  var counts = { elements: 0, visible: 0, skippedConsent: 0, skippedHidden: 0 };
  var all = document.querySelectorAll("body *");
  var vw = window.innerWidth, vh = window.innerHeight;
  var pageArea = Math.max(1, document.documentElement.scrollWidth *
                             Math.max(document.documentElement.scrollHeight, vh));
  var mediaArea = 0, mediaCounts = new Tally(), objectFit = new Tally(), fullBleed = 0;

  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    if (SKIP_TAGS[el.tagName]) continue;
    counts.elements += 1;

    var cs; try { cs = getComputedStyle(el); } catch (e) { continue; }
    var rect = el.getBoundingClientRect();
    if (!visible(el, cs, rect)) { counts.skippedHidden += 1; continue; }
    if (isConsent(el)) { counts.skippedConsent += 1; continue; }
    counts.visible += 1;

    var area = Math.round(rect.width * rect.height);
    var chars = ownChars(el);

    // Text is weighted by characters and backgrounds by painted area: a 1px border on every row and
    // a hero's background are both "one colour, many elements", and only the weight separates them.
    if (chars > 0) colors.text.add(normColor(cs.color), chars);
    colors.background.add(normColor(cs.backgroundColor), area);
    // Read the colour of a side only when THAT side has width. `borderTopColor` is defined even
    // when `borderTopWidth` is 0, and it falls back to the element's `color` — so a header with
    // only a bottom border reported its TEXT colour as the border colour, at the full page width,
    // and that outweighed the real grey. A border nobody can see is not a border.
    [["Top", rect.width], ["Bottom", rect.width], ["Left", rect.height], ["Right", rect.height]]
      .forEach(function (side) {
        if ((px(cs["border" + side[0] + "Width"]) || 0) > 0 &&
            cs["border" + side[0] + "Style"] !== "none") {
          colors.border.add(normColor(cs["border" + side[0] + "Color"]), Math.round(side[1]));
        }
      });
    if (el.tagName === "svg" || el.tagName === "path" || el.tagName === "circle") {
      colors.fill.add(normColor(cs.fill), area);
    }
    if (cs.backgroundImage && cs.backgroundImage !== "none" && /gradient\(/.test(cs.backgroundImage)) {
      gradients.add(cs.backgroundImage, area);
    }

    if (chars > 0) {
      var fam = (cs.fontFamily || "").split(",")[0].replace(/^['"]|['"]$/g, "").trim();
      fontFamilies.add(fam, chars);
      var key = [fam, px(cs.fontSize), cs.fontWeight, px(cs.lineHeight), px(cs.letterSpacing),
                 cs.textTransform].join("|");
      var t = typeBag[key] || (typeBag[key] = {
        family: fam, size: px(cs.fontSize), weight: cs.fontWeight,
        lineHeight: px(cs.lineHeight), letterSpacing: px(cs.letterSpacing),
        textTransform: cs.textTransform !== "none" ? cs.textTransform : null,
        chars: 0, elements: 0, tags: {}
      });
      t.chars += chars; t.elements += 1;
      t.tags[el.tagName.toLowerCase()] = (t.tags[el.tagName.toLowerCase()] || 0) + 1;
    }

    ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"].forEach(function (p) {
      var v = px(cs[p]); if (v > 0) padT.add(v);
    });
    ["marginTop", "marginBottom"].forEach(function (p) {
      var v = px(cs[p]); if (v > 0) marT.add(v);
    });
    if (cs.rowGap && cs.rowGap !== "normal") { var g = px(cs.rowGap); if (g > 0) gapT.add(g); }
    if (cs.columnGap && cs.columnGap !== "normal") { var g2 = px(cs.columnGap); if (g2 > 0) gapT.add(g2); }
    var rad = px(cs.borderTopLeftRadius);
    // A radius of ZERO is a decision, not missing data. Dropping it reported adidas.it — whose
    // corners are deliberately sharp — as having no radius at all, so the only value left was a
    // single 24px dot and the whole system came out pill-shaped.
    radT.add(rad > 0 && rad >= rect.height / 2 && rect.height > 0 ? "pill" : rad);
    if (cs.boxShadow && cs.boxShadow !== "none") shadowBag.add(cs.boxShadow, area);
    if (cs.display === "grid" && cs.gridTemplateColumns && cs.gridTemplateColumns !== "none") {
      gridBag.add(cs.gridTemplateColumns, area);
    }
    var mw = px(cs.maxWidth);
    if (mw && mw > 320 && mw < 2200 && (cs.marginLeft === cs.marginRight)) containerT.add(mw);

    if (el.tagName === "IMG" || el.tagName === "VIDEO" || el.tagName === "PICTURE" || el.tagName === "svg") {
      mediaCounts.add(el.tagName.toLowerCase());
      mediaArea += area;
      if (cs.objectFit && cs.objectFit !== "fill") objectFit.add(cs.objectFit);
      if (rect.width >= vw * 0.98) fullBleed += 1;
      if (el.tagName === "IMG" && MODE === "site") {
        var alt = (el.getAttribute("alt") || "").trim();
        if (alt && samples.length < 40) samples.push({ kind: "alt", text: alt.slice(0, 120) });
      }
    }

    // Text: SHAPE always, STRINGS only on a public marketing page. Inside a signed-in app the
    // strings are customer names, invoice numbers and email addresses, and they would travel into
    // the snapshot, the guide and the slides.
    if (chars > 0) {
      var txt = (el.textContent || "").replace(/\s+/g, " ").trim();
      var tag = el.tagName;
      if (/^H[1-6]$/.test(tag) && txt) {
        textShape.headings.push({ level: Number(tag[1]), words: txt.split(" ").length, chars: txt.length });
        if (txt === txt.toUpperCase() && /[A-Z]/.test(txt)) textShape.upperHeadings += 1;
        else if (/^[A-Z][^.!?]*$/.test(txt)) textShape.titleHeadings += 1;
        if (/,/.test(txt)) textShape.commaPattern += 1;
        if (MODE === "site" && samples.length < 40 && txt.split(" ").length <= 15) {
          samples.push({ kind: "heading", level: Number(tag[1]), text: txt.slice(0, 160) });
        }
      }
      if (tag === "P" && txt) textShape.paragraphs.push({ words: txt.split(" ").length, chars: txt.length });
      if ((tag === "BUTTON" || tag === "A") && txt && txt.length <= 40 && chars > 0) {
        textShape.ctaLabels.push({ words: txt.split(" ").length, chars: txt.length });
        if (MODE === "site" && samples.length < 40) samples.push({ kind: "cta", text: txt.slice(0, 60) });
      }
      textShape.you += (txt.match(/\b(you|your|tu|tuo|tua)\b/gi) || []).length;
      textShape.we += (txt.match(/\b(we|our|us|noi|nostro|nostra)\b/gi) || []).length;
      textShape.exclamations += (txt.match(/!/g) || []).length;
      textShape.digits += (txt.match(/\d/g) || []).length;
    }
  }

  /* ---------------------------------------------------------- candidates */

  function describeAll(selector, limit, extra) {
    var out = [], seen = 0;
    var nodes = document.querySelectorAll(selector);
    for (var j = 0; j < nodes.length && out.length < (limit || MAX_CANDIDATES); j++) {
      var n = nodes[j];
      var cs; try { cs = getComputedStyle(n); } catch (e) { continue; }
      var r = n.getBoundingClientRect();
      if (!visible(n, cs, r) || isConsent(n)) continue;
      seen += 1;
      var layer = paintedLayer(n);
      var row = boxOf(layer);
      row.selector = selector;
      row.tag = n.tagName.toLowerCase();
      row.paintedOnChild = layer !== n;
      if (extra) extra(row, n, cs);
      out.push(row);
    }
    return { total: seen, sample: out };
  }

  // The class list matters more than it looks. A first version matched `btn` and `button` only, and
  // missed `a.cta` — the one pill-shaped control on the test page, i.e. exactly the primary action a
  // brand spends its design on. When in doubt widen the net: a false candidate is cheap to drop in
  // analysis, a missing primary button changes the whole system.
  var candidates = {
    buttons: describeAll('button, [role="button"], input[type="submit"], ' +
      'a[class*="btn"], a[class*="Btn"], a[class*="button"], a[class*="Button"], ' +
      'a[class*="cta"], a[class*="Cta"], a[class*="CTA"], a[class*="action"]'),
    inputs: describeAll('input:not([type="hidden"]):not([type="submit"]), textarea, select'),
    cards: describeAll('article, [class*="card"], [class*="Card"]'),
    links: describeAll("nav a, header a", 12)
  };

  // The nav and the header are measured in both modes; what differs is whether they are then
  // deduplicated out of the usage share (see analyze.py: in `app` mode they are the product).
  var headerEl = document.querySelector('header, [role="banner"], [class*="header"]:not(body)');
  candidates.header = null;
  if (headerEl) {
    var hcs = getComputedStyle(headerEl);
    var hr = headerEl.getBoundingClientRect();
    candidates.header = boxOf(headerEl);
    candidates.header.sticky = (hcs.position === "sticky" || hcs.position === "fixed");
    candidates.header.position = hcs.position;
    candidates.header.height = Math.round(hr.height);
    var logo = headerEl.querySelector('img, svg, [class*="logo"], [class*="Logo"], [class*="wordmark"]');
    if (logo) {
      var lr = logo.getBoundingClientRect();
      candidates.header.logo = {
        tag: logo.tagName.toLowerCase(),
        width: Math.round(lr.width), height: Math.round(lr.height),
        color: normColor(getComputedStyle(logo).color) || normColor(getComputedStyle(logo).fill),
        // The logo is never copied. Its measured box and colour become a dashed placeholder.
        source: logo.tagName === "IMG" ? (logo.getAttribute("src") || "").slice(0, 300) : null
      };
    }
  }

  if (MODE === "app") {
    var sidebarEl = document.querySelector('[class*="sidebar"], [class*="Sidebar"], aside, [role="navigation"][class*="side"]');
    candidates.sidebar = sidebarEl ? boxOf(sidebarEl) : null;
    if (candidates.sidebar) {
      candidates.sidebar.width = Math.round(sidebarEl.getBoundingClientRect().width);
      candidates.sidebar.collapsedWidth = null;    // only a real collapsed render can supply this
      note("sidebar collapsed width not captured: re-run with the sidebar collapsed to measure it");
    }
    var tableEl = document.querySelector('table, [role="table"], [role="grid"]');
    if (tableEl) {
      candidates.table = boxOf(tableEl);
      var head = tableEl.querySelector("thead tr, [role=row]");
      var body = tableEl.querySelector("tbody tr, [role=row]:nth-of-type(2)");
      candidates.table.headerHeight = head ? Math.round(head.getBoundingClientRect().height) : null;
      candidates.table.rowHeight = body ? Math.round(body.getBoundingClientRect().height) : null;
      var cell = tableEl.querySelector("tbody td, [role=cell], [role=gridcell]");
      candidates.table.cell = cell ? boxOf(cell) : null;
    } else {
      candidates.table = null;
    }
    var dialogEl = document.querySelector('dialog[open], [role="dialog"], [class*="modal"], [class*="Modal"], [class*="drawer"], [class*="Drawer"]');
    candidates.dialog = (dialogEl && !isConsent(dialogEl)) ? boxOf(dialogEl) : null;
    var badgeEl = document.querySelectorAll('[class*="badge"], [class*="Badge"], [class*="chip"], [class*="tag"]');
    candidates.badges = { total: badgeEl.length, sample: [] };
    for (var b = 0; b < badgeEl.length && candidates.badges.sample.length < 12; b++) {
      var bcs = getComputedStyle(badgeEl[b]);
      var br = badgeEl[b].getBoundingClientRect();
      if (visible(badgeEl[b], bcs, br)) candidates.badges.sample.push(boxOf(badgeEl[b]));
    }
  }

  /* -------------------------------------------------------------- states */

  // A page shows one state at a time. `focus` and `disabled` can be read directly; `hover` cannot be
  // forced from script, so it is read off the stylesheets here and, where the stylesheets are
  // cross-origin, driven for real by the caller (see SKILL.md, the states pass).
  var states = {};

  function firstVisible(selector) {
    var nodes = document.querySelectorAll(selector);
    for (var k = 0; k < nodes.length; k++) {
      var cs; try { cs = getComputedStyle(nodes[k]); } catch (e) { continue; }
      var r = nodes[k].getBoundingClientRect();
      if (visible(nodes[k], cs, r) && !isConsent(nodes[k])) return nodes[k];
    }
    return null;
  }

  var focusTargets = [
    ["button", 'button, [role="button"]'],
    ["input", 'input:not([type="hidden"]):not([type="submit"]), textarea'],
    ["link", "nav a, header a, main a"]
  ];

  // Measured 2026-10-21 and it is the difference between a fact and a false negative: `.focus()`
  // does set `:focus-visible` and the ring is readable — but only while `document.hasFocus()`. In a
  // hidden or background page the same call reports `outline: none`, which reads exactly like a site
  // that ships no focus ring. An accessibility finding invented by a hidden tab is worse than none,
  // so when the document has no focus the focus states are not written at all.
  var docFocused = document.hasFocus();
  if (!docFocused) {
    note("document has no focus (hidden or background tab): focus states NOT measured — " +
         "front the tab and re-run, or drive a real Tab keypress");
  }

  var previouslyFocused = document.activeElement;
  if (docFocused) focusTargets.forEach(function (pair) {
    var el = firstVisible(pair[1]);
    if (!el) return;
    var before = boxOf(paintedLayer(el));
    try { el.focus({ preventScroll: true }); } catch (e) { return; }
    var after = boxOf(paintedLayer(el));
    var ring = getComputedStyle(el);
    states[pair[0] + ":focus"] = {
      rest: before, focus: after,
      outline: ring.outlineStyle !== "none"
        ? { width: px(ring.outlineWidth), color: normColor(ring.outlineColor), offset: px(ring.outlineOffset), style: ring.outlineStyle }
        : null,
      changed: JSON.stringify(before) !== JSON.stringify(after)
    };
    try { el.blur(); } catch (e) { /* nothing to restore */ }
  });
  if (previouslyFocused && previouslyFocused.focus) {
    try { previouslyFocused.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
  }

  var disabledEl = firstVisible("button[disabled], input[disabled], [aria-disabled=true]");
  states["button:disabled"] = disabledEl ? boxOf(paintedLayer(disabledEl)) : null;
  if (!disabledEl) note("no disabled control on this page: the disabled state is inferred, not measured");

  // Hover cannot be forced from script. Where the stylesheets are readable it is read declaratively,
  // which costs nothing; where they are cross-origin the caller drives a real pointer over a short
  // list of controls (SKILL.md, "the states pass"). Declared hover is labelled as declared, never
  // merged with a measured value — a `:hover` rule can be overridden by one this does not resolve.
  // The same pass answers a second question that turns out to matter more: did the page AUTHOR a
  // focus ring at all? Every focusable element reports an outline, because when the page declares
  // none the browser draws its own — `#e59700` here, which is the OS accent and no part of anyone's
  // design. Reading the declared rules is the only way to tell an authored ring from a default one,
  // and the alternative tried first (accept a ring whose colour is painted elsewhere) rejected the
  // test page's real `input:focus-visible` because that blue is used nowhere but the ring.
  var hoverRules = [], focusRules = [];
  for (var hs = 0; hs < document.styleSheets.length; hs++) {
    var hrules = null;
    try { hrules = document.styleSheets[hs].cssRules; } catch (e) { continue; }
    if (!hrules) continue;
    for (var hr = 0; hr < hrules.length; hr++) {
      var hrule = hrules[hr];
      if (hrule.type !== 1 || !hrule.selectorText) continue;
      var sel = hrule.selectorText;
      var isHover = sel.indexOf(":hover") !== -1;
      var isFocus = sel.indexOf(":focus") !== -1;
      if (!isHover && !isFocus) continue;
      if (isHover && hoverRules.length >= 40) continue;
      if (isFocus && focusRules.length >= 40) continue;
      var decl = {};
      for (var dp = 0; dp < hrule.style.length; dp++) {
        var dprop = hrule.style[dp];
        if (/color|background|border|box-shadow|opacity|transform|outline|translate|scale/.test(dprop)) {
          decl[dprop] = hrule.style.getPropertyValue(dprop).trim().slice(0, 120);
        }
      }
      if (!Object.keys(decl).length) continue;
      (isFocus ? focusRules : hoverRules).push({ selector: sel.slice(0, 160), declared: decl });
    }
  }
  states.hoverDeclared = hoverRules;
  states.focusDeclared = focusRules;

  /* ------------------------------------------------------------- declared */

  // Computed styles cover everything the DESIGN.md needs. The declared layer adds three things the
  // DOM cannot give: the custom-property NAMES, the @media breakpoints and the @font-face sources.
  // Cross-origin stylesheets throw on .cssRules, and that is reported rather than silently dropped.
  var declared = { customProperties: {}, breakpoints: [], fontFaces: [], sheets: 0, opaqueSheets: 0 };

  for (var s = 0; s < document.styleSheets.length; s++) {
    var sheet = document.styleSheets[s];
    declared.sheets += 1;
    var rules = null;
    try { rules = sheet.cssRules; } catch (e) { declared.opaqueSheets += 1; continue; }
    if (!rules) { declared.opaqueSheets += 1; continue; }
    (function walkRules(list, depth) {
      if (depth > 4) return;
      for (var r = 0; r < list.length; r++) {
        var rule = list[r];
        if (rule.type === 1 && rule.style) {                       // CSSStyleRule
          if (/^(:root|html)\b/.test(rule.selectorText || "")) {
            for (var p = 0; p < rule.style.length; p++) {
              var prop = rule.style[p];
              if (prop.indexOf("--") === 0) {
                declared.customProperties[prop] = rule.style.getPropertyValue(prop).trim().slice(0, 200);
              }
            }
          }
        } else if (rule.type === 4) {                               // CSSMediaRule
          var m = (rule.conditionText || rule.media.mediaText || "").match(/(min|max)-width:\s*([\d.]+)(px|rem|em)/g);
          if (m) {
            m.forEach(function (one) {
              var parts = one.match(/(min|max)-width:\s*([\d.]+)(px|rem|em)/);
              var n = parseFloat(parts[2]);
              if (parts[3] !== "px") n = n * 16;
              var entry = { edge: parts[1], px: Math.round(n) };
              if (!declared.breakpoints.some(function (b) { return b.edge === entry.edge && b.px === entry.px; })) {
                declared.breakpoints.push(entry);
              }
            });
          }
          if (rule.cssRules) walkRules(rule.cssRules, depth + 1);
        } else if (rule.type === 5 && rule.style) {                 // CSSFontFaceRule
          declared.fontFaces.push({
            family: (rule.style.getPropertyValue("font-family") || "").replace(/['"]/g, "").trim(),
            weight: rule.style.getPropertyValue("font-weight") || null,
            style: rule.style.getPropertyValue("font-style") || null,
            // The URL is recorded so the guide can LINK it. Font files are never downloaded.
            src: (rule.style.getPropertyValue("src") || "").slice(0, 300)
          });
        } else if (rule.cssRules) {
          walkRules(rule.cssRules, depth + 1);
        }
      }
    })(rules, 0);
  }
  if (declared.opaqueSheets > 0) {
    note(declared.opaqueSheets + " of " + declared.sheets +
         " stylesheets are cross-origin: custom-property names, breakpoints and @font-face from those are missing (the computed values are not)");
  }
  declared.breakpoints.sort(function (a, b) { return a.px - b.px; });

  /* ----------------------------------------------------------- type table */

  var typeRows = [];
  for (var tk in typeBag) {
    var row = typeBag[tk];
    var tags = [];
    for (var tg in row.tags) tags.push(tg);
    tags.sort(function (a, b) { return row.tags[b] - row.tags[a]; });
    row.tags = tags.slice(0, 4);
    typeRows.push(row);
  }
  typeRows.sort(function (a, b) { return b.size - a.size || b.chars - a.chars; });

  /* -------------------------------------------------------------- the box */

  var snapshot = {
    schema: 1,
    mode: MODE,
    url: location.href,
    origin: location.origin,
    path: location.pathname,
    title: MODE === "site" ? document.title.slice(0, 200) : null,
    capturedAt: new Date().toISOString(),
    viewport: { width: vw, height: vh, dpr: window.devicePixelRatio || 1 },
    colorScheme: (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light",
    documentHasFocus: docFocused,
    documentBackground: normColor(getComputedStyle(document.body).backgroundColor) ||
                        normColor(getComputedStyle(document.documentElement).backgroundColor),
    counts: counts,
    colors: {
      text: colors.text.list("chars", 60),
      background: colors.background.list("area", 60),
      border: colors.border.list("length", 40),
      fill: colors.fill.list("area", 30)
    },
    gradients: gradients.list("area", 12),
    fontFamilies: fontFamilies.list("chars", 10),
    type: typeRows.slice(0, 60),
    spacing: { padding: padT.obj(), margin: marT.obj(), gap: gapT.obj() },
    radius: radT.obj(),
    shadows: shadowBag.list("area", 12),
    containers: containerT.obj(),
    grids: gridBag.list("area", 12),
    media: {
      counts: mediaCounts.obj(),
      areaRatio: Math.round((mediaArea / pageArea) * 10000) / 10000,
      objectFit: objectFit.obj(),
      fullBleed: fullBleed
    },
    candidates: candidates,
    states: states,
    declared: declared,
    text: { shape: textShape, samples: MODE === "site" ? samples : [] },
    notes: notes
  };

  if (MODE === "app") {
    snapshot.notes.push("mode=app: no page text is stored, only its shape (counts, lengths, case). " +
                        "A signed-in app shows real data and it must not travel into the snapshot.");
  }

  // Getting the snapshot OUT of the page, in order of preference:
  //
  //   1. `collect: "http://127.0.0.1:<port>/collect"` — the page POSTs it straight to disk, nothing
  //      is downloaded and nothing passes through the agent. This is the path for any page the
  //      browser loads over http: a local dev server, a preview, these fixtures.
  //   2. `download: true` — the only mechanism left for a remote https page, because mixed content
  //      forbids it from reaching a localhost collector. The caller MOVES the file out of the
  //      browser's download folder immediately; leaving files in someone's ~/Downloads is not a
  //      side effect to accept quietly, and it is asked for the first time it happens.
  //   3. the return value — correct, and the most expensive: ~22 KB of JSON through the agent's
  //      context per page per viewport. Fine once, wrong twenty times.
  if (opt.collect) {
    return fetch(opt.collect, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(snapshot)
    }).then(function (r) {
      return r.ok ? "collected " + snapshot.path + " @" + vw : "collector refused: " + r.status;
    }).catch(function (e) {
      // Never silently fall back to a mechanism the caller did not choose: a collector that cannot
      // be reached is a fact the caller needs, not something to paper over with a download.
      return "collector unreachable (" + e.message + "): no snapshot was written";
    });
  }

  if (DOWNLOAD) {
    var blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "snapshot-" + location.hostname + "-" + MODE + "-" + vw + ".json";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    return "downloaded " + a.download;
  }

  return snapshot;
})(typeof __EXTRACT_OPTIONS__ !== "undefined" ? __EXTRACT_OPTIONS__ : {});
