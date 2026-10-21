/*
 * verify_page.js — the half of the gate that only a browser can answer.
 *
 * Runs inside the rendered guide, reads the COMPUTED style of each rebuilt control and compares it
 * with the token the control is supposed to be made of. A guide can look perfect and still be
 * lying: one literal where a `var()` belongs and the page stops reflecting the system, silently,
 * while everyone argues about a picture.
 *
 * Same two delivery paths as extract.js: POST to a local collector, or return the result.
 *
 *     window.__VERIFY_OPTIONS__ = { collect: "http://127.0.0.1:8781/collect" };
 */
window.__VERIFY__ = (function verifyPage(options) {
  "use strict";

  var opt = options || {};
  var root = getComputedStyle(document.documentElement);

  function token(name) {
    return (root.getPropertyValue(name) || "").trim();
  }

  // Comparing colours as strings fails for the wrong reason: a token may be authored in oklch and
  // reported by the engine in rgb, and those are the same colour. Both sides go through the same
  // 1x1 canvas, so the comparison is between painted pixels rather than between notations.
  var cvs = document.createElement("canvas");
  cvs.width = cvs.height = 1;
  var ctx = cvs.getContext("2d", { willReadFrequently: true });

  function pixel(value) {
    if (!value) return null;
    try {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = "#000000";
      ctx.fillStyle = value;
      ctx.fillRect(0, 0, 1, 1);
      var a = ctx.getImageData(0, 0, 1, 1).data.join(",");
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = "#ffffff";
      ctx.fillStyle = value;
      ctx.fillRect(0, 0, 1, 1);
      var b = ctx.getImageData(0, 0, 1, 1).data.join(",");
      return a === b ? a : null;      // disagreement means the engine rejected it
    } catch (e) { return null; }
  }

  function sameColour(computed, declared) {
    var a = pixel(computed), b = pixel(declared);
    return a !== null && a === b;
  }

  function sameLength(computed, declared) {
    var ca = parseFloat(computed), cb = parseFloat(declared);
    if (!isFinite(ca) || !isFinite(cb)) return false;
    return Math.abs(ca - cb) <= 0.6;   // sub-pixel rounding, not a different value
  }

  // control -> [property, token name, comparator]
  var EXPECT = {
    "button": [
      ["background-color", "--primary", sameColour],
      ["color", "--primary-foreground", sameColour],
      ["border-top-left-radius", "--radius-pill", sameLength]
    ],
    "button-secondary": [
      ["border-top-color", "--border", sameColour],
      ["border-top-left-radius", "--radius", sameLength]
    ],
    "card": [
      ["background-color", "--card", sameColour],
      ["border-top-color", "--border", sameColour],
      ["border-top-left-radius", "--radius", sameLength]
    ],
    "input": [
      ["border-top-color", "--border", sameColour],
      ["border-top-left-radius", "--radius", sameLength]
    ]
  };

  var rebuild = [];
  Object.keys(EXPECT).forEach(function (control) {
    var el = document.querySelector('[data-rebuild="' + control + '"]');
    if (!el) {
      rebuild.push({ control: control, property: "-", token: "-", computed: "-",
                     ok: false, note: "control not found in the guide" });
      return;
    }
    var cs = getComputedStyle(el);
    EXPECT[control].forEach(function (triple) {
      var prop = triple[0], name = triple[1], same = triple[2];
      var declared = token(name);
      if (!declared) {
        // The token is absent, so the control falls back. That is correct behaviour, not a
        // mismatch — but it is recorded, because a guide quietly running on fallbacks is worth
        // knowing about.
        rebuild.push({ control: control, property: prop, token: name, computed: cs[prop],
                       ok: true, note: "token not present: the control is on its fallback" });
        return;
      }
      var computed = cs.getPropertyValue(prop);
      rebuild.push({ control: control, property: prop, token: declared,
                     computed: computed.trim(), ok: same(computed, declared) });
    });
  });

  // 390px is where a guide about someone else's beautiful site usually falls apart.
  var de = document.documentElement;
  var result = {
    schema: 1,
    kind: "verify",
    url: location.href,
    checkedAt: new Date().toISOString(),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    rebuild: rebuild,
    scrollWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    noHorizontalScroll: de.scrollWidth <= de.clientWidth + 1,
    networkRequests: (function () {
      try {
        return performance.getEntriesByType("resource").filter(function (e) {
          return /^https?:/.test(e.name) && e.name.indexOf(location.origin) !== 0;
        }).length;
      } catch (e) { return null; }
    })()
  };

  if (opt.collect) {
    return fetch(opt.collect, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result)
    }).then(function (r) {
      var bad = result.rebuild.filter(function (x) { return !x.ok; }).length;
      return r.ok ? "verified: " + bad + " mismatch(es), " +
                    (result.noHorizontalScroll ? "no" : "HAS") + " horizontal scroll"
                  : "collector refused: " + r.status;
    }).catch(function (e) {
      return "collector unreachable (" + e.message + "): nothing was written";
    });
  }
  return result;
})(typeof __VERIFY_OPTIONS__ !== "undefined" ? __VERIFY_OPTIONS__ : {});
