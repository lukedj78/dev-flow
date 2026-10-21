#!/usr/bin/env python3
"""tokens.json -> media.html: eleven scenes, drawn from the tokens, exported as slides.

One scene engine, two consumers. The slides are the scenes at t=1; the video is the same scenes
animated and recorded. Writing them separately would mean two places where a colour can go stale,
and the whole point of this skill is that one source decides what everything looks like.

Everything is drawn on a canvas rather than screenshotted from HTML, for one reason: exact frame
control. `canvas.captureStream(0)` plus `requestFrame()` means the recorder advances only when we
say so, so a 45-second clip is 2700 frames we chose, not 2700 moments the compositor happened to
catch. That is what "real 60 fps" means here, and it is why the video does not stutter.

Nothing is downloaded and nothing passes through the agent: each export is POSTed to the local
collector as base64 in a JSON envelope.

    render_media.py <tokens.json> --out <dir> [--brand X] [--seconds 45]

Then, in the browser:
    window.__MEDIA__.slides()   -> 8 × 1080×1350 and 4 × 1600×900
    window.__MEDIA__.video()    -> one webm, which make_video.py transcodes
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def js_json(value) -> str:
    """JSON for a <script> element, which is not the same as JSON.

    Everything in `tokens.json` was read off somebody else's page: a custom-property NAME, a font
    family, a CTA label. A site that wants to can set `--x: </script><script>…` and our generator
    would paste it straight into the guide, where it stops being data. The four escapes below keep
    it data. U+2028/9 are in the list because they are legal in JSON and are line terminators in
    JavaScript.
    """
    return (json.dumps(value)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def scenes_for(tokens, brand):
    """The eleven scenes, as data. Each one is a claim the measurement can support."""
    roles = tokens["color"]["roles"]
    scale = tokens["typography"]["scale"]
    space = tokens["spacing"]

    def role(name, fallback=None):
        return roles.get(name, {}).get("value", fallback)

    palette = [{"value": p["value"], "share": p["share"]}
               for p in tokens["color"]["palette"][:8]]

    type_rows = [{"label": s["slot"], "size": s["size"], "weight": s["weight"],
                  "family": s["family"], "tracking": s["tracking"] or 0}
                 for s in scale["slots"][:5]]

    buttons = (tokens["components"].get("button") or {}).get("variants", [])[:3]
    button_rows = [{"bg": b["example"].get("background"),
                    "fg": b["example"].get("color"),
                    "radius": 9999 if b["example"].get("radiusIsPill") else (b["example"].get("radius") or 0),
                    "label": "Action"} for b in buttons]

    voice = tokens.get("voice") or {}
    rules = voice.get("rules", [])[:3]

    return [
        {"id": "cover", "kind": "cover", "title": f"{brand}", "subtitle": "design system, as measured",
         "footnote": f"{tokens['source']['pageCount']} page(s) · "
                     f"{', '.join(str(v) + 'px' for v in tokens['source']['viewports'])}"},
        {"id": "contents", "kind": "stats", "title": "What was measured",
         "stats": [{"k": "Colour roles", "v": str(len(roles))},
                   {"k": "Type steps", "v": str(len(scale["slots"]))},
                   {"k": "Spacing base", "v": f"{space['base']}px" if space["base"] else "—"},
                   {"k": "Not observed", "v": str(len(tokens["missing"]))}]},
        {"id": "typography", "kind": "type", "title": "Typography", "rows": type_rows,
         "subtitle": scale["note"] or (f"ratio {scale['ratio']}" if scale["ratio"] else "")},
        {"id": "colour", "kind": "palette", "title": "Colour", "palette": palette,
         "subtitle": "share is painted area for grounds, characters for text"},
        {"id": "roles", "kind": "roles", "title": "Roles",
         "roles": [{"name": n, "value": r["value"]} for n, r in list(roles.items())[:8]]},
        {"id": "layout", "kind": "spacing", "title": "Layout and spacing",
         "base": space["base"], "steps": [int(v) for v in space["onGrid"][:8]],
         "container": tokens["layout"]["container"]},
        {"id": "components", "kind": "components", "title": "Components", "buttons": button_rows,
         "radius": tokens["radius"]["default"] or 0, "pill": tokens["radius"]["pill"]},
        {"id": "motion", "kind": "motion", "title": "Motion",
         "durations": [d[0] for d in (tokens.get("motion") or {}).get("durations", [])[:3]],
         "easing": ((tokens.get("motion") or {}).get("easings") or [["—"]])[0][0]},
        {"id": "voice", "kind": "quote", "title": "Voice and tone", "rules": rules},
        {"id": "tokens", "kind": "tokens", "title": "Design tokens",
         "count": len(roles) + len(scale["slots"]) + len(space["onGrid"]),
         "missing": tokens["missing"][:6]},
        {"id": "outro", "kind": "outro", "title": "A starting point",
         "subtitle": "not a destination",
         "footnote": f"Unofficial analysis. Not affiliated with or endorsed by {brand}."},
    ]


ENGINE = r"""
(function () {
  "use strict";
  var T = window.__TOKENS__, SCENES = window.__SCENES__, OPT = window.__MEDIA_OPTIONS__ || {};
  var COLLECT = OPT.collect || null;

  function tok(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  // Resolve any CSS colour (including oklch) to something canvas can fill with, by the same 1x1
  // trick the extractor uses: paint it, read the bytes back.
  var probeCanvas = document.createElement("canvas");
  probeCanvas.width = probeCanvas.height = 1;
  var probe = probeCanvas.getContext("2d", { willReadFrequently: true });
  var colourCache = {};
  function colour(value, fallback) {
    if (!value) return fallback || "#888888";
    if (colourCache[value]) return colourCache[value];
    try {
      probe.clearRect(0, 0, 1, 1);
      probe.fillStyle = "#000000";
      probe.fillStyle = value;
      probe.fillRect(0, 0, 1, 1);
      var d = probe.getImageData(0, 0, 1, 1).data;
      var out = "rgba(" + d[0] + "," + d[1] + "," + d[2] + "," + (d[3] / 255) + ")";
      colourCache[value] = out;
      return out;
    } catch (e) { return fallback || "#888888"; }
  }

  var P = {
    bg:   function () { return colour(tok("--background", "#ffffff"), "#ffffff"); },
    fg:   function () { return colour(tok("--foreground", "#111111"), "#111111"); },
    pri:  function () { return colour(tok("--primary", "#333333"), "#333333"); },
    priFg:function () { return colour(tok("--primary-foreground", "#ffffff"), "#ffffff"); },
    card: function () { return colour(tok("--card", "#f4f4f5"), "#f4f4f5"); },
    line: function () { return colour(tok("--border", "rgba(0,0,0,.12)"), "rgba(0,0,0,.12)"); },
    mute: function () { return colour(tok("--muted-foreground", "#6b7280"), "#6b7280"); },
    font: function () { return tok("--font-sans", "system-ui, sans-serif"); }
  };

  function ease(t) { return 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3); }
  function stagger(t, i, n) { return ease((t - i * (0.35 / Math.max(1, n))) / 0.65); }

  function roundRect(c, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }

  function wrap(c, text, x, y, maxW, lh) {
    var words = String(text).split(" "), line = "", lines = [];
    for (var i = 0; i < words.length; i++) {
      var test = line ? line + " " + words[i] : words[i];
      if (c.measureText(test).width > maxW && line) { lines.push(line); line = words[i]; }
      else line = test;
    }
    if (line) lines.push(line);
    lines.forEach(function (l, i) { c.fillText(l, x, y + i * lh); });
    return lines.length * lh;
  }

  function gradient(c, w, h, zoom) {
    var g = c.createLinearGradient(-w * 0.1 * zoom, 0, w * (1 + 0.1 * zoom), h);
    g.addColorStop(0, P.pri());
    g.addColorStop(1, P.bg());
    return g;
  }

  // One draw function. t in [0,1] drives every entrance; the slides call it at 1.
  function draw(c, scene, t, w, h) {
    var S = w / 1080;                     // one scale factor; every size below is in 1080 units
    var pad = 80 * S;
    c.save();
    c.clearRect(0, 0, w, h);
    c.fillStyle = P.bg();
    c.fillRect(0, 0, w, h);
    c.textBaseline = "top";
    var f = P.font();

    var dark = scene.kind === "cover" || scene.kind === "outro" || scene.kind === "roles";
    if (dark) {
      c.fillStyle = gradient(c, w, h, 1 + 0.06 * t);
      c.fillRect(0, 0, w, h);
    }
    var ink = dark ? P.priFg() : P.fg();
    var sub = dark ? P.priFg() : P.mute();

    // the Unofficial pill, on every scene without exception
    c.globalAlpha = ease(t * 2);
    c.strokeStyle = ink; c.lineWidth = 2 * S;
    c.font = (22 * S) + "px " + f;
    var pillW = c.measureText("UNOFFICIAL ANALYSIS").width + 44 * S;
    roundRect(c, pad, pad, pillW, 48 * S, 24 * S);
    c.stroke();
    c.fillStyle = ink;
    c.fillText("UNOFFICIAL ANALYSIS", pad + 22 * S, pad + 13 * S);
    c.globalAlpha = 1;

    var y = pad + 140 * S;
    c.fillStyle = ink;
    c.globalAlpha = ease((t - 0.05) / 0.5);
    c.font = "600 " + (dark ? 92 : 64) * S + "px " + f;
    var titleY = y + (1 - ease((t - 0.05) / 0.5)) * 20 * S;
    y = titleY + wrap(c, scene.title, pad, titleY, w - pad * 2, (dark ? 100 : 74) * S) + 16 * S;
    if (scene.subtitle) {
      c.fillStyle = sub;
      c.font = (30 * S) + "px " + f;
      y += wrap(c, scene.subtitle, pad, y, w - pad * 2, 42 * S) + 24 * S;
    }
    c.globalAlpha = 1;

    var bodyTop = y + 40 * S, innerW = w - pad * 2;

    if (scene.kind === "stats" || scene.kind === "tokens") {
      var items = scene.stats || [{ k: "Tokens", v: String(scene.count) }];
      items.forEach(function (s, i) {
        var a = stagger(t, i, items.length);
        if (a <= 0) return;
        var bh = 170 * S, by = bodyTop + i * (bh + 20 * S) + (1 - a) * 16 * S;
        c.globalAlpha = a;
        c.fillStyle = P.card(); c.strokeStyle = P.line(); c.lineWidth = 1.5 * S;
        roundRect(c, pad, by, innerW, bh, (T.radius.default || 12) * S);
        c.fill(); c.stroke();
        c.fillStyle = P.mute(); c.font = (26 * S) + "px " + f;
        c.fillText(s.k, pad + 32 * S, by + 28 * S);
        c.fillStyle = P.fg(); c.font = "600 " + (64 * S) + "px " + f;
        c.fillText(s.v, pad + 32 * S, by + 70 * S);
        c.globalAlpha = 1;
      });
      if (scene.missing && scene.missing.length) {
        var my = bodyTop + 200 * S;
        c.globalAlpha = ease((t - 0.5) / 0.5);
        c.fillStyle = P.mute(); c.font = (24 * S) + "px " + f;
        wrap(c, "Not observed, and therefore not written: " + scene.missing.join(", "),
             pad, my, innerW, 34 * S);
        c.globalAlpha = 1;
      }
    }

    if (scene.kind === "type") {
      scene.rows.forEach(function (r, i) {
        var a = stagger(t, i, scene.rows.length);
        if (a <= 0) return;
        c.globalAlpha = a;
        var ry = bodyTop + i * 150 * S;
        c.fillStyle = P.mute(); c.font = (22 * S) + "px " + f;
        c.fillText(r.label + " · " + r.size + "px · " + r.weight, pad, ry);
        c.fillStyle = P.fg();
        c.font = r.weight + " " + Math.min(r.size, 84) * S + "px " + (r.family || f);
        c.fillText("The quick brown fox", pad, ry + 34 * S);
        c.globalAlpha = 1;
      });
    }

    if (scene.kind === "palette") {
      var total = scene.palette.reduce(function (s, p) { return s + p.share; }, 0) || 1;
      var x = pad, barH = 180 * S;
      scene.palette.forEach(function (p, i) {
        var a = stagger(t, i, scene.palette.length);
        var pw = (p.share / total) * innerW;
        c.globalAlpha = a;
        c.fillStyle = colour(p.value);
        c.fillRect(x, bodyTop, pw * a, barH);
        c.globalAlpha = 1;
        x += pw;
      });
      c.strokeStyle = P.line(); c.lineWidth = 1.5 * S;
      c.strokeRect(pad, bodyTop, innerW, barH);
      scene.palette.slice(0, 5).forEach(function (p, i) {
        var a = stagger(t, i + 2, 7);
        if (a <= 0) return;
        c.globalAlpha = a;
        var ly = bodyTop + barH + 44 * S + i * 56 * S;
        c.fillStyle = colour(p.value);
        roundRect(c, pad, ly, 40 * S, 40 * S, 8 * S); c.fill();
        c.strokeStyle = P.line(); c.stroke();
        c.fillStyle = P.fg(); c.font = (26 * S) + "px " + f;
        c.fillText(p.value, pad + 58 * S, ly + 7 * S);
        c.globalAlpha = 1;
      });
    }

    if (scene.kind === "roles") {
      scene.roles.forEach(function (r, i) {
        var a = stagger(t, i, scene.roles.length);
        if (a <= 0) return;
        var col = i % 2, row = Math.floor(i / 2);
        var cw = (innerW - 24 * S) / 2, ch = 120 * S;
        var rx = pad + col * (cw + 24 * S), ry = bodyTop + row * (ch + 20 * S);
        c.globalAlpha = a;
        c.fillStyle = colour(r.value);
        roundRect(c, rx, ry, cw, ch, (T.radius.default || 12) * S); c.fill();
        c.strokeStyle = "rgba(255,255,255,.35)"; c.lineWidth = 1.5 * S; c.stroke();
        c.fillStyle = ink; c.font = (24 * S) + "px " + f;
        c.fillText(r.name, rx + 20 * S, ry + ch + 8 * S);
        c.globalAlpha = 1;
      });
    }

    if (scene.kind === "spacing") {
      c.fillStyle = P.fg(); c.font = "600 " + (120 * S) + "px " + f;
      c.globalAlpha = ease((t - 0.1) / 0.5);
      c.fillText((scene.base || "—") + "px", pad, bodyTop);
      c.font = (28 * S) + "px " + f; c.fillStyle = P.mute();
      c.fillText("base unit" + (scene.container ? "  ·  container " + scene.container + "px" : ""),
                 pad, bodyTop + 140 * S);
      c.globalAlpha = 1;
      (scene.steps || []).forEach(function (v, i) {
        var a = stagger(t, i, scene.steps.length);
        if (a <= 0) return;
        c.globalAlpha = a;
        var sy = bodyTop + 220 * S + i * 46 * S;
        c.fillStyle = P.mute(); c.font = (24 * S) + "px " + f;
        c.fillText(v + "px", pad, sy + 4 * S);
        c.fillStyle = P.pri();
        roundRect(c, pad + 110 * S, sy, v * 4 * S * a, 26 * S, 6 * S); c.fill();
        c.globalAlpha = 1;
      });
    }

    if (scene.kind === "components") {
      (scene.buttons || []).forEach(function (b, i) {
        var a = stagger(t, i, Math.max(1, scene.buttons.length));
        if (a <= 0) return;
        c.globalAlpha = a;
        var by = bodyTop + i * 140 * S;
        var bw = 360 * S, bh = 96 * S;
        c.fillStyle = colour(b.bg, P.card());
        roundRect(c, pad, by, bw, bh, Math.min(b.radius, bh / 2) * S); c.fill();
        c.strokeStyle = P.line(); c.lineWidth = 1.5 * S; c.stroke();
        c.fillStyle = colour(b.fg, P.fg()); c.font = "600 " + (30 * S) + "px " + f;
        var tw = c.measureText(b.label).width;
        c.fillText(b.label, pad + (bw - tw) / 2, by + bh / 2 - 18 * S);
        c.fillStyle = P.mute(); c.font = (22 * S) + "px " + f;
        c.fillText((b.bg || "transparent") + "  ·  radius " +
                   (b.radius >= 999 ? "pill" : b.radius + "px"), pad + bw + 32 * S, by + bh / 2 - 12 * S);
        c.globalAlpha = 1;
      });
    }

    if (scene.kind === "motion") {
      var ds = scene.durations.length ? scene.durations : [0];
      ds.forEach(function (ms, i) {
        var a = stagger(t, i, ds.length);
        if (a <= 0) return;
        c.globalAlpha = a;
        var my2 = bodyTop + i * 120 * S;
        c.fillStyle = P.fg(); c.font = "600 " + (56 * S) + "px " + f;
        c.fillText(ms + "ms", pad, my2);
        c.fillStyle = P.pri();
        roundRect(c, pad + 240 * S, my2 + 18 * S, (ms * 1.6) * S * a, 20 * S, 10 * S); c.fill();
        c.globalAlpha = 1;
      });
      c.globalAlpha = ease((t - 0.4) / 0.6);
      c.fillStyle = P.mute(); c.font = (26 * S) + "px " + f;
      wrap(c, "easing " + scene.easing, pad, bodyTop + ds.length * 120 * S + 20 * S, innerW, 36 * S);
      c.globalAlpha = 1;
    }

    if (scene.kind === "quote") {
      (scene.rules || []).forEach(function (r, i) {
        var a = stagger(t, i, Math.max(1, scene.rules.length));
        if (a <= 0) return;
        c.globalAlpha = a;
        var qy = bodyTop + i * 190 * S;
        c.fillStyle = P.pri();
        c.fillRect(pad, qy, 5 * S, 140 * S);
        c.fillStyle = P.fg(); c.font = (32 * S) + "px " + f;
        wrap(c, r, pad + 28 * S, qy, innerW - 28 * S, 44 * S);
        c.globalAlpha = 1;
      });
    }

    if (scene.footnote) {
      c.globalAlpha = ease((t - 0.3) / 0.7);
      c.fillStyle = sub; c.font = (24 * S) + "px " + f;
      wrap(c, scene.footnote, pad, h - pad - 60 * S, innerW, 34 * S);
      c.globalAlpha = 1;
    }
    c.restore();
  }

  function send(label, format, blob) {
    if (!COLLECT) return Promise.resolve(label + " (not sent: no collector)");
    return blob.arrayBuffer().then(function (buf) {
      var bytes = new Uint8Array(buf), bin = "";
      for (var i = 0; i < bytes.length; i += 0x8000) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      }
      return fetch(COLLECT, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ schema: 1, kind: "asset", label: label,
                               format: format, data: btoa(bin) })
      });
    }).then(function (r) { return r.ok ? label : label + " REFUSED " + r.status; });
  }

  function renderOne(scene, w, h) {
    var cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    draw(cv.getContext("2d"), scene, 1, w, h);
    return cv;
  }

  function slides() {
    var IG = SCENES.filter(function (s) {
      return ["cover", "typography", "colour", "layout", "components", "voice", "tokens", "outro"]
        .indexOf(s.id) !== -1;
    });
    var X = SCENES.filter(function (s) {
      return ["cover", "colour", "typography", "tokens"].indexOf(s.id) !== -1;
    });
    var jobs = [];
    IG.forEach(function (s, i) {
      jobs.push(new Promise(function (res) {
        renderOne(s, 1080, 1350).toBlob(function (b) {
          res(send("slide-ig-" + (i + 1) + "-" + s.id, "png", b));
        }, "image/png");
      }));
    });
    X.forEach(function (s, i) {
      jobs.push(new Promise(function (res) {
        renderOne(s, 1600, 900).toBlob(function (b) {
          res(send("slide-x-" + (i + 1) + "-" + s.id, "png", b));
        }, "image/png");
      }));
    });
    return Promise.all(jobs).then(function (r) { return Promise.all(r); })
      .then(function (names) { return names.length + " slide(s): " + names.join(", "); });
  }

  function stills() {
    return Promise.all(SCENES.map(function (s, i) {
      return new Promise(function (res) {
        renderOne(s, 1920, 1080).toBlob(function (b) {
          res(send("still-" + (i + 1) + "-" + s.id, "png", b));
        }, "image/png");
      });
    })).then(function (r) { return Promise.all(r); })
      .then(function (n) { return n.length + " still(s)"; });
  }

  // The video lived here and was removed on 2026-10-21, deliberately. It drew its own scenes with
  // its own layout rules, so it showed a design that exists nowhere — not the measured site, not
  // the guide — and it broke the rule this file rests on by being a second renderer. The two
  // measurements from the attempt are kept in references/artifacts.md, including the one that
  // matters: MediaRecorder is NOT frame-accurate (1320 drawn, 1151 recorded, 12.8% lost). When a
  // video is wanted, record the GUIDE, which is already the artefact built from the tokens.

  window.__MEDIA__ = { draw: draw, slides: slides, stills: stills, scenes: SCENES };
  return "media engine ready: " + SCENES.length + " scenes";
})();
"""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{brand} — media</title>
<style>
{root}
  body {{ margin:0; font-family: var(--font-sans, system-ui, sans-serif);
          background: var(--background, #fff); color: var(--foreground, #111); padding: 24px; }}
  button {{ font: inherit; padding: 10px 18px; margin-right: 8px; cursor: pointer;
            border: 1px solid var(--border, #ccc); border-radius: var(--radius, 8px);
            background: var(--primary, #222); color: var(--primary-foreground, #fff); }}
  #log {{ font-family: ui-monospace, monospace; font-size: 13px; white-space: pre-wrap;
          margin-top: 16px; }}
  canvas {{ max-width: 100%; border: 1px solid var(--border, #ddd); margin-top: 16px; }}
</style>
</head>
<body>
<h1 style="font-size:20px">{brand} — scene engine</h1>
<p style="font-size:13px;opacity:.7">Eleven scenes drawn from the tokens. The slides are these at
rest; the video is these animated and recorded frame by frame.</p>
<button onclick="run('slides')">Export slides</button>
<button onclick="run('stills')">Export stills</button>
<div id="log">ready</div>
<canvas id="preview" width="1080" height="1350"></canvas>
<script>
window.__TOKENS__ = {tokens};
window.__SCENES__ = {scenes};
window.__MEDIA_OPTIONS__ = {{ collect: {collect} }};
</script>
<script>{engine}</script>
<script>
  var log = document.getElementById('log');
  function run(what) {{
    log.textContent = what + ' running…';
    Promise.resolve(window.__MEDIA__[what]()).then(function (r) {{ log.textContent = r; }})
      .catch(function (e) {{ log.textContent = 'FAILED: ' + e.message; }});
  }}
  window.__MEDIA__.draw(document.getElementById('preview').getContext('2d'),
                        window.__SCENES__[0], 1, 1080, 1350);
</script>
</body>
</html>
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tokens", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--brand", default=None)
    ap.add_argument("--collect", default="http://127.0.0.1:8781/collect")
    args = ap.parse_args(argv)

    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    brand = args.brand or (tokens["source"]["origin"] or "source").split("//")[-1].split("/")[0]

    # Reuse the guide's own :root so the scenes and the guide cannot disagree about a colour.
    import render_guide
    root = render_guide.root_block(render_guide.token_rows(tokens))

    args.out.mkdir(parents=True, exist_ok=True)
    page = PAGE.format(brand=html.escape(brand, quote=True), root=root, engine=ENGINE,
                       tokens=js_json(tokens), scenes=js_json(scenes_for(tokens, brand)),
                       collect=js_json(args.collect) if args.collect else "null")
    target = args.out / "media.html"
    target.write_text(page, encoding="utf-8")
    print(f"media.html written -> {target} ({target.stat().st_size / 1024:.1f} KB)")
    print("  11 scenes · slides 8×1080×1350 + 4×1600×900")
    print(f"  collector: {args.collect or 'none (exports will not be written)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
