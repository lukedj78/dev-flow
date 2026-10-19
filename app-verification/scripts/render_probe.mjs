#!/usr/bin/env node
// render_probe.mjs — measure a running page in headless Chrome, the things no source scan can see.
//
//   node render_probe.mjs <url> [--widths 1440,768,390] [--json] [--strict] [--out DIR] [--timeout SECONDS]
//                             [--throttle slow|fast-3g|<kbps>]   slower network, so a skeleton stays up long enough
//   node render_probe.mjs --find-browser
//
// shadscan, check.py and the design lint read source. This opens the page and measures it at each width:
//   overflow-x      the page is wider than the viewport, with the outermost elements causing it      FAIL
//   headline-lines  a heading wraps to more than two lines (h1 FAIL, h2–h6 WARN)                      FAIL/WARN
//   reduced-hidden  text visible normally stays invisible with prefers-reduced-motion: reduce          FAIL
//   font-fallback   a declared @font-face used on the page failed to load                              WARN
//   broken-image    an <img> finished loading with no picture                                          FAIL
//   sidebar-phone   on a phone (≤ 480px) a sidebar covers more than 30% of the width                   FAIL
//   layout-shift    the page jumps while it loads — a skeleton or a late block that is not the size of what
//                   replaces it: cumulative layout shift > 0.05 WARN, > 0.1 FAIL, with the elements that moved
//
// Adapted from the idea of taste-skill v2's inspector (Leonxlnx/taste-skill, MIT) — not its code and not its rules —
// with one deliberate difference: it serves no files. Give it the dev server's URL (or a file:// path); a probe that
// served the working directory would expose .env to every script on the page.
//
// Zero dependencies: Node >= 22 (built-in WebSocket) and an installed Chrome, Chromium or Edge (CHROME_PATH to choose).
// A throwaway profile, removed on exit; nothing written outside --out. A measurement: exit 0, unless --strict and a
// FAIL (1). Exit 2 bad input, 3 the environment (no browser, Node too old, the browser would not start), 4 the page
// (cannot load, timed out, crashed) — so "environment missing, skip" is never confused with a broken run.

import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const USAGE = "usage: node render_probe.mjs <http(s):// or file:// url> [--widths 1440,768,390] [--json] [--strict] [--out DIR] [--timeout SECONDS] [--throttle slow|fast-3g|<kbps>]";
// web-vitals: CLS <= 0.1 is "good". dev-flow's target for a measured skeleton is 0.05.
const CLS_WARN = 0.05, CLS_FAIL = 0.1;
// Chrome DevTools' presets, in bytes per second and ms of latency.
const THROTTLE = {
  "slow": { latency: 400, downloadThroughput: (400 * 1024) / 8, uploadThroughput: (400 * 1024) / 8 },
  "fast-3g": { latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 },
};
const SETTLE_MS = 500;
// A cold `next dev` compile of a first route can take well over 30 s; the default leaves room for it.
const DEFAULT_TIMEOUT_S = 60;

class PageError extends Error {}  // exit 4: the page, not the machine

function fail(code, message) {
  process.stderr.write(message + "\n");
  process.exit(code);
}

function parseArgs(argv) {
  const opts = { widths: [1440, 768, 390], json: false, strict: false, out: null, url: null, findBrowser: false,
    timeoutMs: DEFAULT_TIMEOUT_S * 1000, throttle: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") opts.json = true;
    else if (a === "--strict") opts.strict = true;
    else if (a === "--find-browser") opts.findBrowser = true;
    else if (a === "--widths") opts.widths = String(argv[++i] || "").split(",").map(Number).filter((n) => n > 0);
    else if (a === "--out") opts.out = argv[++i];
    else if (a === "--throttle") {
      const v = String(argv[++i] || "");
      const kbps = Number(v);
      if (THROTTLE[v]) opts.throttle = THROTTLE[v];
      else if (kbps > 0) opts.throttle = { latency: 150, downloadThroughput: (kbps * 1024) / 8, uploadThroughput: (kbps * 1024) / 8 };
      else fail(2, "--throttle takes slow, fast-3g or a number of kbit/s");
    }
    else if (a === "--timeout") {
      const s = Number(argv[++i]);
      if (!(s > 0)) fail(2, "--timeout needs a number of seconds");
      opts.timeoutMs = s * 1000;
    }
    else if (a === "-h" || a === "--help") { process.stdout.write(USAGE + "\n"); process.exit(0); }
    else if (!opts.url) opts.url = a;
    else fail(2, `unexpected argument: ${a}\n${USAGE}`);
  }
  return opts;
}

function findBrowser() {
  if (process.env.CHROME_PATH) return existsSync(process.env.CHROME_PATH) ? process.env.CHROME_PATH : null;
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/snap/bin/chromium", "/usr/bin/microsoft-edge",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ];
  return candidates.find((p) => existsSync(p)) || null;
}

// ─── a minimal CDP client over the browser's WebSocket ──────────────────────────────────────────────────────────

function launch(browser) {
  const profile = mkdtempSync(join(tmpdir(), "render-probe-"));
  const child = spawn(browser, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars",
    "--mute-audio", "--disable-breakpad", "--disable-crash-reporter", "about:blank",
    // Its own process group: Chrome's helpers (zygote, GPU, crashpad) outlive the main process on Linux and keep
    // writing into the profile; the cleanup signals the whole group.
  ], { stdio: ["ignore", "ignore", "pipe"], detached: process.platform !== "win32" });
  const exited = new Promise((resolve) => child.once("exit", resolve));
  // Chrome's helpers keep writing into the profile for a moment after the main process dies: wait for the exit,
  // then remove with retries — an immediate rmSync left `Default/Reporting and NEL-journal` behind in 2 of 20 runs.
  const signal = (sig) => {
    try { process.platform === "win32" ? child.kill(sig) : process.kill(-child.pid, sig); } catch {}
  };
  const cleanup = async () => {
    if (child.exitCode === null && child.signalCode === null) {
      signal("SIGTERM");
      await Promise.race([exited, new Promise((r) => setTimeout(r, 3000))]);
    }
    signal("SIGKILL");  // whatever of the group is still alive
    // Remove until it is gone: a helper finishing its last write can recreate a file after the first pass.
    for (let i = 0; i < 20 && existsSync(profile); i++) {
      try { rmSync(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 50 }); } catch {}
      if (existsSync(profile)) await new Promise((r) => setTimeout(r, 150));
    }
  };
  const ws = new Promise((resolve, reject) => {
    let buf = "";
    const timer = setTimeout(() => reject(new Error("the browser did not open a DevTools socket within 20s")), 20000);
    child.stderr.on("data", (d) => {
      buf += d;
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
    child.on("error", (e) => { clearTimeout(timer); reject(e); });
    child.on("exit", (code) => { clearTimeout(timer); reject(new Error(`the browser exited (${code}) before it was ready`)); });
  });
  return { ws, cleanup };
}

function connect(url) {
  const sock = new WebSocket(url);
  let nextId = 1;
  const pending = new Map();
  const listeners = [];
  sock.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method) {
      for (const l of listeners) l(msg);
    }
  };
  const ready = new Promise((resolve, reject) => { sock.onopen = resolve; sock.onerror = () => reject(new Error("cannot reach the DevTools socket")); });
  // A browser that crashes closes the socket: every call still waiting fails instead of hanging the probe.
  sock.onclose = () => {
    for (const { reject } of pending.values()) reject(new PageError("the browser closed the DevTools connection"));
    pending.clear();
  };
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    sock.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const once = (method, sessionId, timeoutMs) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new PageError(`timed out after ${timeoutMs / 1000}s waiting for ${method}`)), timeoutMs);
    const l = (msg) => {
      if (msg.method === method && msg.sessionId === sessionId) {
        clearTimeout(timer);
        listeners.splice(listeners.indexOf(l), 1);
        resolve(msg.params);
      }
    };
    listeners.push(l);
  });
  return { ready, send, once, close: () => sock.close() };
}

// ─── what runs in the page ──────────────────────────────────────────────────────────────────────────────────────
// Kept as one function so it is evaluated, not injected as a script tag: the page's CSP does not apply to it.

async function measureInPage() {
  const vw = window.innerWidth;
  // The comparison key between the normal and the reduced-motion load: tag + position only. Classes change with
  // state (a reveal script adds `.in` only when motion is allowed), so a key with classes never matches across loads.
  const key = (el) => {
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) {
      if (e.id) { parts.unshift(`#${e.id}`); break; }
      const i = e.parentElement ? [...e.parentElement.children].indexOf(e) + 1 : 1;
      parts.unshift(`${e.tagName.toLowerCase()}:nth-child(${i})`);
    }
    return parts.join(">");
  };
  const path = (el) => {
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) {
      let s = e.tagName.toLowerCase();
      if (e.id) { parts.unshift(`${s}#${e.id}`); break; }
      if (e.classList.length) s += "." + [...e.classList].slice(0, 2).join(".");
      const sib = e.parentElement ? [...e.parentElement.children].filter((c) => c.tagName === e.tagName) : [];
      if (sib.length > 1) s += `:nth-of-type(${sib.indexOf(e) + 1})`;
      parts.unshift(s);
    }
    return parts.join(" > ");
  };
  const hiddenByAncestor = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === "none" || cs.visibility === "hidden" || e.getAttribute("aria-hidden") === "true" || e.hidden) return true;
    }
    return false;
  };
  const opacity = (el) => {
    let o = 1;
    for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    return o;
  };
  const clippedX = (el) => {
    for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
      const ox = getComputedStyle(e).overflowX;
      if (ox !== "visible") return true;
    }
    return false;
  };
  const ownText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 1);

  // overflow-x: outermost elements whose box crosses the right edge, outside any element that clips them
  const pageWidth = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const culprits = [];
  if (pageWidth > vw + 1) {
    for (const el of document.body.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.right <= vw + 1 || hiddenByAncestor(el) || clippedX(el)) continue;
      if (getComputedStyle(el).position === "fixed" && r.left >= vw) continue; // parked off-canvas
      if (culprits.some((c) => c.contains(el))) continue;
      culprits.push(el);
    }
  }

  // headings: count distinct line boxes of the text
  const headings = [];
  for (const h of document.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
    if (hiddenByAncestor(h) || !h.textContent.trim()) continue;
    // Lines from the heading's text only, clustered by half a line height: an inline icon or a small badge makes
    // line boxes of different heights, and a Set of rounded tops counted a two-line h1 with both as five lines.
    const cs = getComputedStyle(h);
    const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
    const tops = [];
    const walker = document.createTreeWalker(h, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      for (const r of range.getClientRects()) if (r.width > 1) tops.push(r.top + r.height / 2);
    }
    tops.sort((a, b) => a - b);
    let lines = 0, last = -Infinity;
    for (const y of tops) { if (y - last > lh * 0.5) { lines++; last = y; } }
    headings.push({ tag: h.tagName.toLowerCase(), lines, text: h.textContent.trim().slice(0, 60), el: path(h) });
  }

  // text elements and their visibility, keyed by path (compared across the normal and the reduced-motion load)
  const text = {};
  for (const el of document.body.querySelectorAll("*")) {
    if (!ownText(el) || hiddenByAncestor(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    text[key(el)] = { visible: opacity(el) >= 0.05, label: path(el) };
  }

  // fonts that failed and are in use
  const usedFamilies = new Set();
  for (const el of document.body.querySelectorAll("*")) {
    if (!ownText(el) || hiddenByAncestor(el)) continue;
    const first = getComputedStyle(el).fontFamily.split(",")[0].trim().replace(/^["']|["']$/g, "");
    usedFamilies.add(first.toLowerCase());
  }
  const failedFonts = [...document.fonts]
    .filter((f) => f.status === "error" && usedFamilies.has(f.family.replace(/^["']|["']$/g, "").toLowerCase()))
    .map((f) => f.family.replace(/^["']|["']$/g, ""));

  const brokenImages = [...document.images]
    .filter((img) => img.complete && img.naturalWidth === 0 && (img.currentSrc || img.src) && !hiddenByAncestor(img))
    .map((img) => `${path(img)} (${(img.currentSrc || img.src).slice(0, 80)})`);

  const sidebars = [];
  if (vw <= 480) {
    for (const el of document.querySelectorAll('aside, [data-sidebar="sidebar"], [role="complementary"]')) {
      const r = el.getBoundingClientRect();
      if (hiddenByAncestor(el) || r.width === 0 || r.right <= 0 || r.left >= vw || opacity(el) < 0.05) continue;
      const visible = Math.min(r.right, vw) - Math.max(r.left, 0);
      if (visible > 0.3 * vw) sidebars.push({ el: path(el), share: Math.round((100 * visible) / vw) });
    }
  }

  // Layout shifts since navigation (buffered), the way web-vitals counts them: shifts within 500 ms of user input
  // are excluded, and transforms (entrances) never produce one.
  const shifts = await new Promise((resolve) => {
    const out = [];
    try {
      const po = new PerformanceObserver((list) => { out.push(...list.getEntries()); });
      po.observe({ type: "layout-shift", buffered: true });
      setTimeout(() => { po.disconnect(); resolve(out); }, 100);
    } catch { resolve(out); }
  });
  let cls = 0;
  const moved = new Map();
  for (const s of shifts) {
    if (s.hadRecentInput) continue;
    cls += s.value;
    for (const src of s.sources || []) {
      const el = src.node && (src.node.nodeType === 1 ? src.node : src.node.parentElement);
      if (el && el.isConnected) moved.set(path(el), (moved.get(path(el)) || 0) + s.value);
    }
  }
  const movedTop = [...moved.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([p]) => p);

  return {
    pageWidth, vw, href: location.href, cls: Math.round(cls * 1000) / 1000, moved: movedTop,
    culprits: culprits.slice(0, 5).map((el) => `${path(el)} (${Math.round(el.getBoundingClientRect().right)}px)`),
    headings, text, failedFonts: [...new Set(failedFonts)], brokenImages, sidebars,
  };
}

// Scroll through once so scroll-triggered reveals and lazy images get their chance, then back to the top.
async function scrollThrough() {
  const step = Math.max(200, Math.floor(window.innerHeight * 0.8));
  for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 60));
  }
  window.scrollTo(0, 0);
  await new Promise((r) => setTimeout(r, 60));
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  // Wait for every finite animation to end (entrances, reveals), capped: a fixed sleep raced the first one.
  const finite = document.getAnimations().filter((a) => {
    const end = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming().endTime : Infinity;
    return a.playState !== "finished" && Number.isFinite(end);
  });
  await Promise.race([
    Promise.all(finite.map((a) => a.finished.catch(() => null))),
    new Promise((r) => setTimeout(r, 3000)),
  ]);
  return true;
}

// ─── the run ────────────────────────────────────────────────────────────────────────────────────────────────────

async function navigate(cdp, sessionId, url, timeoutMs) {
  const loaded = cdp.once("Page.loadEventFired", sessionId, timeoutMs);
  const nav = await cdp.send("Page.navigate", { url }, sessionId);
  if (nav.errorText) { loaded.catch(() => {}); throw new PageError(`cannot load ${url}: ${nav.errorText}`); }
  await loaded;
}

async function evaluate(cdp, sessionId, expression) {
  const res = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, sessionId);
  if (res.exceptionDetails) throw new PageError(`measuring failed: ${res.exceptionDetails.text}`);
  return res.result.value;
}

async function probePage(cdp, sessionId, url, width, reduced, timeoutMs, throttle) {
  const phone = width <= 480;
  // Throttled only in the normal pass, which is the one that measures layout shift; the reduced-motion pass compares
  // visibility after load and gains nothing from waiting longer.
  await cdp.send("Network.emulateNetworkConditions", throttle && !reduced
    ? { offline: false, ...throttle }
    : { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }, sessionId);
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width, height: phone ? 844 : 900, deviceScaleFactor: 1, mobile: false }, sessionId);
  await cdp.send("Emulation.setEmulatedMedia",
    { features: [{ name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" }] }, sessionId);
  // Through about:blank every time: navigating to the same URL with a #fragment is same-document — no load event,
  // and the second pass would wait for one that never comes.
  await navigate(cdp, sessionId, "about:blank", timeoutMs);
  await navigate(cdp, sessionId, url, timeoutMs);
  // A client-side redirect after load destroys the context mid-measure: wait for the new page and measure that.
  for (let attempt = 0; ; attempt++) {
    try {
      await evaluate(cdp, sessionId, `(${scrollThrough})()`);
      await new Promise((r) => setTimeout(r, SETTLE_MS));
      return await evaluate(cdp, sessionId, `(${measureInPage})()`);
    } catch (err) {
      if (attempt >= 2 || !/navigated|context|destroyed|not found/i.test(err.message)) throw err;
      await cdp.once("Page.loadEventFired", sessionId, timeoutMs).catch(() => {});
    }
  }
}

function findingsFor(width, normal, reduced) {
  const out = [];
  const add = (level, id, message, elements = []) => out.push({ level, id, width, message, elements });
  if (normal.pageWidth > normal.vw + 1) {
    add("FAIL", "overflow-x", `the page is ${normal.pageWidth}px wide in a ${normal.vw}px viewport`, normal.culprits);
  }
  for (const h of normal.headings) {
    if (h.lines > 2) {
      add(h.tag === "h1" ? "FAIL" : "WARN", "headline-lines", `${h.tag} wraps to ${h.lines} lines: "${h.text}"`, [h.el]);
    }
  }
  const hidden = Object.keys(reduced.text).filter((k) => !reduced.text[k].visible && normal.text[k] && normal.text[k].visible);
  if (hidden.length) {
    add("FAIL", "reduced-hidden", `${hidden.length} text element(s) visible normally stay invisible with reduced motion`,
      hidden.slice(0, 5).map((k) => reduced.text[k].label));
  }
  if (normal.failedFonts.length) {
    add("WARN", "font-fallback", `declared font(s) failed to load and fell back: ${normal.failedFonts.join(", ")}`);
  }
  if (normal.brokenImages.length) {
    add("FAIL", "broken-image", `${normal.brokenImages.length} image(s) loaded with no picture`, normal.brokenImages.slice(0, 5));
  }
  for (const s of normal.sidebars) {
    add("FAIL", "sidebar-phone", `a sidebar covers ${s.share}% of a ${normal.vw}px phone`, [s.el]);
  }
  if (normal.cls > CLS_WARN) {
    add(normal.cls > CLS_FAIL ? "FAIL" : "WARN", "layout-shift",
      `the page shifts while it loads (CLS ${normal.cls}; target ≤ ${CLS_WARN}) — size the skeleton or the late block to what replaces it`,
      normal.moved);
  }
  return out;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (typeof WebSocket === "undefined") fail(3, `render_probe needs Node >= 22 (built-in WebSocket); this is ${process.version}.`);
  const browser = findBrowser();
  if (opts.findBrowser) {
    if (!browser) fail(3, "no Chrome, Chromium or Edge found — install one or set CHROME_PATH.");
    process.stdout.write(browser + "\n");
    return 0;
  }
  if (!opts.url || !/^(https?|file):\/\//i.test(opts.url)) fail(2, USAGE);
  if (!opts.widths.length) fail(2, "--widths needs comma-separated pixel widths, e.g. 1440,768,390");
  if (!browser) {
    fail(3, process.env.CHROME_PATH
      ? `CHROME_PATH=${process.env.CHROME_PATH} does not exist — point it at a Chrome, Chromium or Edge binary.`
      : "no Chrome, Chromium or Edge found — install one or set CHROME_PATH.");
  }

  const { ws, cleanup } = launch(browser);
  for (const [sig, code] of [["SIGINT", 130], ["SIGTERM", 143], ["SIGHUP", 129]]) {
    process.on(sig, () => { cleanup().finally(() => process.exit(code)); });
  }
  let cdp;
  try {
    try {
      cdp = connect(await ws);
      await cdp.ready;
    } catch (err) {
      throw Object.assign(new Error(`the browser would not start: ${err.message}`), { exitCode: 3 });
    }
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);
    await cdp.send("Network.enable", {}, sessionId);

    const findings = [];
    const finalUrls = new Set();
    const cls = {};
    if (opts.out) mkdirSync(opts.out, { recursive: true });
    for (const width of opts.widths) {
      const normal = await probePage(cdp, sessionId, opts.url, width, false, opts.timeoutMs, opts.throttle);
      finalUrls.add(normal.href);
      cls[width] = normal.cls;
      if (opts.out) {
        const shot = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true }, sessionId);
        writeFileSync(join(opts.out, `probe-${width}.png`), Buffer.from(shot.data, "base64"));
      }
      const reduced = await probePage(cdp, sessionId, opts.url, width, true, opts.timeoutMs, null);
      findings.push(...findingsFor(width, normal, reduced));
    }

    const finalUrl = [...finalUrls][0] || opts.url;
    const strip = (u) => u.split("#")[0];
    const notes = strip(finalUrl) !== strip(opts.url)
      ? [`redirected: ${opts.url} → ${finalUrl} — the findings are about the page that was measured`] : [];
    const report = {
      url: opts.url, final_url: finalUrl, notes, widths: opts.widths, measured_at: new Date().toISOString(), cls, findings,
      summary: { fail: findings.filter((f) => f.level === "FAIL").length, warn: findings.filter((f) => f.level === "WARN").length },
    };
    if (opts.out) writeFileSync(join(opts.out, "probe.json"), JSON.stringify(report, null, 2) + "\n");
    if (opts.json) {
      process.stdout.write(JSON.stringify(report, null, 2) + "\n");
    } else {
      process.stdout.write(`render probe — ${opts.url} at ${opts.widths.join(", ")}px\n`);
      for (const n of notes) process.stdout.write(`  note: ${n}\n`);
      for (const f of findings) {
        process.stdout.write(`  ${f.level} ${f.id} @${f.width} — ${f.message}\n`);
        for (const el of f.elements) process.stdout.write(`      ${el}\n`);
      }
      process.stdout.write(findings.length ? `${report.summary.fail} FAIL, ${report.summary.warn} WARN\n`
        : "  ✓ nothing measured wrong (overflow, headings, reduced motion, fonts, images, phone sidebar, layout shift)\n");
    }
    return opts.strict && report.summary.fail ? 1 : 0;
  } finally {
    if (cdp) {
      try { await Promise.race([cdp.send("Browser.close"), new Promise((r) => setTimeout(r, 2000))]); } catch {}
      cdp.close();
    }
    await cleanup();
  }
}

main().then((code) => process.exit(code), (err) => fail(err.exitCode || 4, `render_probe: ${err.message}`));
