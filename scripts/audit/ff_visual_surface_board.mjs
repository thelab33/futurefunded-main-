#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import { chromium } from "playwright";


/**
 * FF_VISUAL_CAPTURE_STABILIZER_V1
 * Stabilizes Playwright screenshots so sticky headers, web fonts, lazy images,
 * and mobile conversion docks do not create misleading visual captures.
 */
async function stabilizeVisualCapture(page, options = {}) {
  const {
    scrollY = 0,
    hideFloating = false,
    reducedMotion = true,
  } = options;

  await page.emulateMedia({
    reducedMotion: reducedMotion ? "reduce" : "no-preference",
  }).catch(() => {});

  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForLoadState("networkidle", { timeout: 6000 }).catch(() => {});

  await page.evaluate(async ({ scrollY, hideFloating }) => {
    document.documentElement.style.scrollBehavior = "auto";
    document.body.style.scrollBehavior = "auto";

    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; } catch (_) {}
    }

    window.scrollTo(0, scrollY);

    if (hideFloating) {
      const style = document.createElement("style");
      style.setAttribute("data-ff-visual-capture-stabilizer", "true");
      style.textContent = `
        .ff-mobileDonateBar,
        .ff-mobileRail,
        .ff-mobileDonateDock,
        [data-ff-mobile-rail],
        [data-ff-mobile-conversion-rail],
        [data-ff-sticky-donate],
        [data-ff-floating-donate] {
          opacity: 0 !important;
          pointer-events: none !important;
          transform: translateY(140%) !important;
        }
      `;
      document.head.appendChild(style);
    }

    // Force a couple of frames so sticky/fixed layout settles.
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, { scrollY, hideFloating });

  await page.waitForTimeout(350);
}

const ROOT = process.cwd();
const base = process.env.FF_VISUAL_BASE || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const port = Number(process.env.FF_VISUAL_PORT || 8765);

const outRoot = path.join(ROOT, "audit_outputs", "visual-board");
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const outDir = path.join(outRoot, stamp);
const latestDir = path.join(outRoot, "latest");

const surfaces = [
  ["platform", "Platform homepage", `${base}/platform/`, ["Launch a premium fundraising page"]],
  ["campaign", "Campaign page", `${base}/c/connect-atx-elite`, ["Fuel the season", "data-ff-open-checkout"]],
  ["onboarding", "Launch workspace", `${base}/platform/onboarding`, ["Campaign essentials"]],
  ["dashboard-locked", "Dashboard locked", `${base}/platform/dashboard`, ["Operator access required"]],
  ["login", "Operator login", `${base}/platform/login`, ["data-ff-login-root", "data-ff-login-submit"]],
];

if (token) {
  surfaces.push([
    "dashboard-private",
    "Operator dashboard",
    `${base}/platform/dashboard?token=${encodeURIComponent(token)}`,
    ["Pending sponsor recognition", "Review sponsor"],
  ]);
}

const viewports = [
  ["desktop", 1440, 2200],
  ["mobile", 390, 1800],
];

function esc(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function redact(url) {
  return String(url).replace(/token=[^&]+/gi, "token=REDACTED");
}

await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
});

const results = [];

for (const [key, label, url, checks] of surfaces) {
  for (const [vpName, width, height] of viewports) {
    const context = await browser.newContext({
      viewport: { width, height },
      deviceScaleFactor: 1,
    });

    const page = await context.newPage();

    const result = {
      key,
      label,
      viewport: vpName,
      width,
      url: redact(url),
      status: null,
      ok: false,
      overflowX: false,
      screenshot: "",
      checks: [],
      error: "",
    };

    try {
      page.setDefaultTimeout(12000);

      const response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 18000,
      });

      result.status = response ? response.status() : null;

      await page.addStyleTag({
        content: `
          *,*::before,*::after {
            animation: none !important;
            transition: none !important;
            scroll-behavior: auto !important;
            caret-color: transparent !important;
          }
        `,
      }).catch(() => {});

      await page.waitForLoadState("networkidle", { timeout: 7000 }).catch(() => {});
      await page.waitForTimeout(900);

      const html = await page.content();
      const text = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");

      const metrics = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));

      result.overflowX = metrics.scrollWidth > metrics.clientWidth + 3;

      result.checks = checks.map((check) => ({
        label: check,
        found: html.includes(check) || text.includes(check),
      }));

      const file = `${key}-${vpName}.png`;

      await stabilizeVisualCapture(page, { scrollY: 0, hideFloating: process.env.FF_VISUAL_HIDE_FLOATING === "1" });
      // FF_VISUAL_CAPTURE_STABILIZER_CALLS_V1
      await page.screenshot({
        path: path.join(outDir, file),
        fullPage: false,
        timeout: 15000,
      });

      result.screenshot = file;
      const expectedLocked = key === "dashboard-locked" && result.status === 403;

      result.ok =
        ((result.status >= 200 && result.status < 400) || expectedLocked) &&
        !result.overflowX &&
        result.checks.every((c) => c.found);
    } catch (err) {
      result.error = err?.message || String(err);
    } finally {
      results.push(result);
      await context.close().catch(() => {});
    }
  }
}

await browser.close();

const pass = results.filter((r) => r.ok).length;
const fail = results.length - pass;
const overflow = results.filter((r) => r.overflowX).length;

await fs.writeFile(
  path.join(outDir, "summary.json"),
  JSON.stringify({ generatedAt: new Date().toISOString(), base, totals: { captures: results.length, pass, fail, overflow }, results }, null, 2)
);

const cards = results.map((r) => `
  <article class="card ${r.ok ? "pass" : "fail"}">
    <header>
      <div>
        <p>${esc(r.viewport)} · ${esc(r.width)}px</p>
        <h2>${esc(r.label)}</h2>
        <small>${esc(r.url)}</small>
      </div>
      <strong>${r.ok ? "PASS" : "CHECK"}</strong>
    </header>
    <div class="meta">
      <span>Status: ${esc(r.status ?? "n/a")}</span>
      <span>Overflow X: ${r.overflowX ? "YES" : "No"}${r.key === "dashboard-locked" && r.status === 403 ? " · Protected 403 expected" : ""}</span>
    </div>
    ${r.error ? `<pre>${esc(r.error)}</pre>` : ""}
    <ul>${r.checks.map(c => `<li class="${c.found ? "ok" : "bad"}">${c.found ? "✓" : "×"} ${esc(c.label)}</li>`).join("")}</ul>
    ${r.screenshot ? `<a href="./${esc(r.screenshot)}" target="_blank"><img src="./${esc(r.screenshot)}" alt="${esc(r.label)} ${esc(r.viewport)}"></a>` : ""}
  </article>
`).join("");

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FutureFunded Visual Surface Board</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Inter,ui-sans-serif,system-ui;background:#f6eadb;color:#17110d}
.shell{width:min(1800px,calc(100vw - 32px));margin:auto;padding:28px 0 56px}
.hero{margin-bottom:20px;padding:24px;border-radius:28px;background:rgba(255,255,255,.82);border:1px solid rgba(40,25,15,.12);box-shadow:0 24px 70px rgba(50,35,20,.14)}
.eyebrow{margin:0 0 8px;color:#f05a1f;font-weight:900;letter-spacing:.12em;text-transform:uppercase;font-size:12px}
h1{margin:0;max-width:900px;font-size:clamp(38px,6vw,82px);line-height:.86;letter-spacing:-.075em}
.summary{margin-top:14px;color:#695f55;font-weight:800}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:start}
.card{overflow:hidden;border-radius:24px;background:rgba(255,255,255,.9);border:1px solid rgba(40,25,15,.12);box-shadow:0 18px 54px rgba(50,35,20,.13)}
.card header{display:flex;justify-content:space-between;gap:16px;padding:16px;border-bottom:1px solid rgba(40,25,15,.1)}
.card header p{margin:0 0 6px;color:#f05a1f;font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}
.card h2{margin:0;font-size:22px;letter-spacing:-.045em;line-height:.95}
.card small{display:block;margin-top:8px;color:#766b61;font-weight:700;overflow-wrap:anywhere}
.card strong{align-self:start;border-radius:999px;padding:8px 10px;background:rgba(8,127,91,.1);color:#087f5b;font-size:12px}
.card.fail strong{background:rgba(180,35,24,.1);color:#b42318}
.meta{display:flex;gap:10px;flex-wrap:wrap;padding:12px 16px 0;color:#766b61;font-weight:800;font-size:12px}
ul{margin:0;padding:12px 16px 16px;list-style:none;font-weight:800;font-size:13px}
li.ok{color:#087f5b}li.bad{color:#b42318}
pre{margin:12px 16px 0;padding:12px;white-space:pre-wrap;background:#fff4ef;color:#9f2d12;border-radius:14px;font-size:12px}
img{display:block;width:100%;height:auto;border-top:1px solid rgba(40,25,15,.1);background:white}
@media(max-width:1100px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<main class="shell">
  <section class="hero">
    <p class="eyebrow">FutureFunded Visual Surface Board</p>
    <h1>All launch surfaces in one QA view.</h1>
    <p class="summary">${pass}/${results.length} passing · ${fail} check flags · ${overflow} overflow flags</p>
  </section>
  <section class="grid">${cards}</section>
</main>
</body>
</html>`;

await fs.writeFile(path.join(outDir, "index.html"), html);

await fs.rm(latestDir, { force: true, recursive: true }).catch(() => {});
await fs.mkdir(latestDir, { recursive: true });

for (const file of await fs.readdir(outDir)) {
  await fs.copyFile(path.join(outDir, file), path.join(latestDir, file));
}

console.log("");
console.log("FutureFunded visual surface board complete");
console.log("==========================================");
console.log(`Output: ${outDir}`);
console.log(`Latest: ${latestDir}`);
console.log(`Open:   http://127.0.0.1:${port}/`);
console.log("");
console.log(`Passing: ${pass}/${results.length}`);
console.log(`Check flags: ${fail}`);
console.log(`Overflow flags: ${overflow}`);
console.log("");

for (const r of results) {
  console.log(`${r.ok ? "PASS" : "CHECK"} ${r.label} [${r.viewport}] status=${r.status ?? "n/a"} overflowX=${r.overflowX}`);
  if (r.error) console.log(`  error: ${r.error}`);
  for (const c of r.checks) if (!c.found) console.log(`  missing: ${c.label}`);
}

if (process.env.FF_VISUAL_SERVE === "1") {
  const server = http.createServer(async (req, res) => {
    const reqPath = decodeURIComponent((req.url || "/").split("?")[0]);
    const safePath = reqPath === "/" ? "/index.html" : reqPath;
    const filePath = path.normalize(path.join(latestDir, safePath));

    if (!filePath.startsWith(latestDir)) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    try {
      const data = await fs.readFile(filePath);
      const ext = path.extname(filePath).toLowerCase();
      const type = ext === ".html" ? "text/html" : ext === ".png" ? "image/png" : ext === ".json" ? "application/json" : "application/octet-stream";
      res.writeHead(200, { "content-type": type });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  });

  server.listen(port, "127.0.0.1", () => {
    console.log(`Serving visual board at http://127.0.0.1:${port}/`);
  });
}
