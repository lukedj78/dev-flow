#!/usr/bin/env node
// render_probe.mjs — measure a running page in headless Chrome, the things no source scan can see.
//
//   node render_probe.mjs <url> [--widths 1440,768,390] [--json] [--strict] [--out DIR]
//   node render_probe.mjs --find-browser
//
// shadscan, check.py and the design lint read source. This opens the page and measures it at each width:
//   overflow-x      the page is wider than the viewport, with the outermost elements causing it      FAIL
//   headline-lines  a heading wraps to more than two lines (h1 FAIL, h2–h6 WARN)                      FAIL/WARN
//   reduced-hidden  text visible normally stays invisible with prefers-reduced-motion: reduce          FAIL
//   font-fallback   a declared @font-face used on the page failed to load                              WARN
//   broken-image    an <img> finished loading with no picture                                          FAIL
//   sidebar-phone   on a phone (≤ 480px) a sidebar covers more than 30% of the width                   FAIL
//
// Adapted from the idea of taste-skill v2's inspector (Leonxlnx/taste-skill, MIT) — not its code and not its rules —
// with one deliberate difference: it serves no files. Give it the dev server's URL (or a file:// path); a probe that
// served the working directory would expose .env to every script on the page.
//
// Zero dependencies: Node >= 22 (built-in WebSocket) and an installed Chrome, Chromium or Edge (CHROME_PATH to choose).
// A throwaway profile, removed on exit; nothing written outside --out. A measurement: exit 0, unless --strict and a
// FAIL (1). Exit 2 bad input, 3 no browser or Node too old.

import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const USAGE = "usage: node render_probe.mjs <http(s):// or file:// url> [--widths 1440,768,390] [--json] [--strict] [--out DIR]";
const SETTLE_MS = 500;
const NAV_TIMEOUT_MS = 30000;

function fail(code, message) {
  process.stderr.write(message + "\n");
  process.exit(code);
}

function parseArgs(argv) {
  const opts = { widths: [1440, 768, 390], json: false, strict: false, out: null, url: null, findBrowser: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") opts.json = true;
    else if (a === "--strict") opts.strict = true;
    else if (a === "--find-browser") opts.findBrowser = true;
    else if (a === "--widths") opts.widths = String(argv[++i] || "").split(",").map(Number).filter((n) => n > 0);
    else if (a === "--out") opts.out = argv[++i];
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
    "--mute-audio", "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });
  const cleanup = () => {
    try { child.kill("SIGKILL"); } catch {}
    try { rmSync(profile, { recursive: true, force: true }); } catch {}
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
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    sock.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const once = (method, sessionId, timeoutMs) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timed out waiting for ${method}`)), timeoutMs);
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

function measureInPage() {
  const vw = window.innerWidth;
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
    const range = document.createRange();
    range.selectNodeContents(h);
    const tops = new Set([...range.getClientRects()].filter((r) => r.width > 1).map((r) => Math.round(r.top)));
    headings.push({ tag: h.tagName.toLowerCase(), lines: tops.size, text: h.textContent.trim().slice(0, 60), el: path(h) });
  }

  // text elements and their visibility, keyed by path (compared across the normal and the reduced-motion load)
  const text = {};
  for (const el of document.body.querySelectorAll("*")) {
    if (!ownText(el) || hiddenByAncestor(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    text[path(el)] = opacity(el) >= 0.05;
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

  return {
    pageWidth, vw,
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

async function probePage(cdp, sessionId, url, width, reduced) {
  const phone = width <= 480;
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width, height: phone ? 844 : 900, deviceScaleFactor: 1, mobile: false }, sessionId);
  await cdp.send("Emulation.setEmulatedMedia",
    { features: [{ name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" }] }, sessionId);
  const loaded = cdp.once("Page.loadEventFired", sessionId, NAV_TIMEOUT_MS);
  const nav = await cdp.send("Page.navigate", { url }, sessionId);
  if (nav.errorText) throw new Error(`cannot load ${url}: ${nav.errorText}`);
  await loaded;
  await cdp.send("Runtime.evaluate", { expression: `(${scrollThrough})()`, awaitPromise: true }, sessionId);
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  const res = await cdp.send("Runtime.evaluate",
    { expression: `(${measureInPage})()`, returnByValue: true, awaitPromise: true }, sessionId);
  if (res.exceptionDetails) throw new Error(`measuring failed: ${res.exceptionDetails.text}`);
  return res.result.value;
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
  const hidden = Object.keys(reduced.text).filter((k) => reduced.text[k] === false && normal.text[k] === true);
  if (hidden.length) {
    add("FAIL", "reduced-hidden", `${hidden.length} text element(s) visible normally stay invisible with reduced motion`,
      hidden.slice(0, 5));
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
  process.on("SIGINT", () => { cleanup(); process.exit(130); });
  let cdp;
  try {
    cdp = connect(await ws);
    await cdp.ready;
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);

    const findings = [];
    if (opts.out) mkdirSync(opts.out, { recursive: true });
    for (const width of opts.widths) {
      const normal = await probePage(cdp, sessionId, opts.url, width, false);
      if (opts.out) {
        const shot = await cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true }, sessionId);
        writeFileSync(join(opts.out, `probe-${width}.png`), Buffer.from(shot.data, "base64"));
      }
      const reduced = await probePage(cdp, sessionId, opts.url, width, true);
      findings.push(...findingsFor(width, normal, reduced));
    }

    const report = {
      url: opts.url, widths: opts.widths, measured_at: new Date().toISOString(), findings,
      summary: { fail: findings.filter((f) => f.level === "FAIL").length, warn: findings.filter((f) => f.level === "WARN").length },
    };
    if (opts.out) writeFileSync(join(opts.out, "probe.json"), JSON.stringify(report, null, 2) + "\n");
    if (opts.json) {
      process.stdout.write(JSON.stringify(report, null, 2) + "\n");
    } else {
      process.stdout.write(`render probe — ${opts.url} at ${opts.widths.join(", ")}px\n`);
      for (const f of findings) {
        process.stdout.write(`  ${f.level} ${f.id} @${f.width} — ${f.message}\n`);
        for (const el of f.elements) process.stdout.write(`      ${el}\n`);
      }
      process.stdout.write(findings.length ? `${report.summary.fail} FAIL, ${report.summary.warn} WARN\n`
        : "  ✓ nothing measured wrong (overflow, headings, reduced motion, fonts, images, phone sidebar)\n");
    }
    return opts.strict && report.summary.fail ? 1 : 0;
  } finally {
    if (cdp) cdp.close();
    cleanup();
  }
}

main().then((code) => process.exit(code), (err) => fail(3, `render_probe: ${err.message}`));
