/*
 * Which pages to measure — gist §1: "the home page plus 3–5 key pages, chosen by scoring
 * same-origin links."
 *
 * This was missing entirely, and the SKILL said the opposite: that a person picks them. The cost
 * is not only coverage. §2 asks to "dedupe repeated chrome: any count that is identical on every
 * page (header and footer) is counted once", and with one page there is nothing to compare — so on
 * apple.com the legal footer's 68 024 characters won the `text` role outright. One missing step
 * produced a wrong colour, which is the sort of thing a reader of the guide cannot possibly spot.
 *
 * Returns the chosen URLs with the score and the reason, because a page nobody can explain is a
 * page nobody can argue with.
 *
 *     window.__PICK_PAGES__ = { limit: 4 };   // then load this file; read window.__PAGES__
 */
window.__PAGES__ = (function pick(options) {
  "use strict";
  var opt = options || {};
  var LIMIT = Math.max(1, Math.min(8, opt.limit || 4));
  var here = new URL(location.href);

  // The gist's own ranking: "Nav links and product, pricing, business and company pages score
  // highest. Skip legal, help, login and locale duplicates."
  var HIGH = /(product|pricing|price|plans|business|company|about|features?|solutions?|platform|shop|store|services?)/i;
  var SKIP = /(privacy|legal|terms|cookie|gdpr|imprint|help|support|faq|login|signin|sign-in|register|signup|account|cart|checkout|careers?|jobs|press|investor|sitemap|rss|feed)/i;
  // A locale duplicate is the same page in another language: /it/, /en-gb/, /fr_FR/.
  var LOCALE = /^\/([a-z]{2}([-_][a-z]{2})?)(\/|$)/i;

  function fromChrome(a) {
    return !!a.closest("nav, header, footer, [role='navigation'], [role='banner'], [role='contentinfo']");
  }

  // A link nobody can see without opening a menu is not the primary bar.
  function visibleLink(a) {
    try {
      var r = a.getBoundingClientRect();
      if (r.width < 8 || r.height < 8) return false;
      var cs = getComputedStyle(a);
      return cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity) > 0.05;
    } catch (e) { return false; }
  }

  // The bar, left to right: the visible links of the nav in the order a reader meets them.
  var _bar = null;
  function navBar(nav) {
    if (_bar) return _bar;
    _bar = Array.prototype.slice.call(nav.querySelectorAll("a[href]"))
      .filter(visibleLink)
      .sort(function (x, y) {
        var a = x.getBoundingClientRect(), b = y.getBoundingClientRect();
        return (a.top - b.top) || (a.left - b.left);
      });
    return _bar;
  }

  function sameOrigin(href) {
    try { return new URL(href, location.href).origin === here.origin; } catch (e) { return false; }
  }

  var seenPath = Object.create(null), rows = [];
  var links = document.querySelectorAll("a[href]");
  for (var i = 0; i < links.length; i += 1) {
    var a = links[i];
    var href = a.getAttribute("href") || "";
    if (!href || href[0] === "#" || /^(mailto|tel|javascript):/i.test(href)) continue;
    if (!sameOrigin(href)) continue;
    var u;
    try { u = new URL(href, location.href); } catch (e) { continue; }
    // The fragment and the query are the same page dressed differently.
    var path = u.pathname.replace(/\/+$/, "") || "/";
    if (path === (here.pathname.replace(/\/+$/, "") || "/")) continue;   // the home page is already in
    if (SKIP.test(path)) continue;
    if (/\.(pdf|zip|dmg|exe|jpe?g|png|gif|webp|svg|mp4|mov)$/i.test(path)) continue;

    // ONE PAGE PER TOP-LEVEL PATH, per the gist. A site with forty product pages would otherwise
    // fill the whole budget with forty variations of one layout.
    var top = path.split("/").filter(Boolean)[0] || "/";
    if (LOCALE.test(path)) {
      var rest = path.replace(LOCALE, "/");
      top = "locale:" + (rest.split("/").filter(Boolean)[0] || "/");
    }
    if (seenPath[top]) {
      // More links to it is evidence — but only from the CONTENT. The nav and the footer are the
      // chrome §2 asks to dedupe, and they are identical on every page by definition: apple.com's
      // mega-menu and footer point at its store 94 times between them, which made a redirect
      // outrank every product page. A link repeated in furniture is one link, not ninety-four.
      if (!fromChrome(a)) seenPath[top].count += 1;
      continue;
    }

    var nav = a.closest("nav, header, [role='navigation'], [role='banner']");
    var inFooter = !!a.closest("footer, [role='contentinfo']");
    var text = (a.textContent || "").trim().slice(0, 60);
    var score = 0;
    var why = [];
    if (nav && !inFooter) {
      // THE PRIMARY NAV IS THE SITE'S OWN ANSWER to "what are we". A regex cannot know that
      // `/iphone` matters — `iphone` is not a word any list contains — but the site put it in the
      // bar, and that is a measurement.
      //
      // VISIBLE links only, ordered LEFT TO RIGHT. apple.com's nav holds 235 anchors because the
      // mega-menu is in the DOM with the bar, so `/iphone` sits at DOM index 75 while being the
      // fourth thing a person sees. Reading the DOM order ranked a store redirect above every
      // product page. What a reader sees is the geometry.
      score += 60;
      why.push("in the nav");
      if (visibleLink(a)) {
        var bar = navBar(nav);
        var at = bar.indexOf(a);
        if (at >= 0 && at < 12) { score += 30 - at * 2; why.push("bar position " + (at + 1)); }
        else { score += 6; why.push("visible in the nav"); }
      }
    }
    if (HIGH.test(path) || HIGH.test(text)) { score += 25; why.push("product/pricing/company word"); }
    if (path.split("/").filter(Boolean).length === 1) { score += 15; why.push("top-level"); }
    if (text) { score += 5; }
    seenPath[top] = { url: u.origin + path, path: path, text: text, score: score,
                      why: why, count: fromChrome(a) ? 0 : 1, top: top };
    rows.push(seenPath[top]);
  }

  // A page many links point at is a page the site itself considers important.
  rows.forEach(function (r) { r.score += Math.min(14, r.count * 2); });
  rows.sort(function (a, b) { return b.score - a.score || a.path.length - b.path.length; });

  var chosen = rows.slice(0, LIMIT).map(function (r) {
    return { url: r.url, path: r.path, score: r.score,
             why: r.why.concat([r.count + " link(s) to it"]).join(", ") };
  });
  return {
    schema: 1,
    origin: here.origin,
    home: here.origin + (here.pathname.replace(/\/+$/, "") || "/"),
    considered: rows.length,
    chosen: chosen,
    // What was deliberately not considered, so the run log can say so rather than imply coverage.
    skipped: { reason: "legal, help, login, locale duplicates, assets, and one page per top-level path" },
  };
})(window.__PICK_PAGES__);
