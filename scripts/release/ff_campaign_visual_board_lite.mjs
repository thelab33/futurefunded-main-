#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { chromium } from "playwright";

const ROOT = process.cwd();
const BASE_URL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const URL = `${BASE_URL.replace(/\/$/, "")}/c/connect-atx-elite`;
const OUT = path.join(ROOT, "audit_outputs", "visual-review-board", "latest");

const viewports = [
  ["mobile", 390, 1400],
  ["tablet", 768, 1500],
  ["desktop", 1440, 1100],
];

const contracts = {
  pageRoot: ".ff-campaignPage",
  header: "[data-ff-header]",
  donateCta: "[data-ff-donate-cta]",
  checkoutTrigger: "[data-ff-open-checkout], [data-ff-payment-trigger]",
  sponsorCta: "[data-ff-sponsor-cta], [data-ff-open-sponsor]",
  shareTrigger: "[data-ff-share], [data-ff-share-trigger]",
  progressBar: "[data-ff-progress-bar], .ff-progressBar",
};

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function healthy() {
  try {
    const res = await fetch(`${BASE_URL}/healthz`);
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureServer() {
  if (await healthy()) return;

  const result = spawnSync("bash", ["scripts/demo/ff-demo-start.sh"], {
    cwd: ROOT,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    throw new Error("Could not start local demo.");
  }

  for (let i = 0; i < 30; i++) {
    if (await healthy()) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error("Local demo did not become healthy.");
}

mkdirp(OUT);
await ensureServer();

const browser = await chromium.launch({ headless: true });
const results = [];

for (const [name, width, height] of viewports) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    isMobile: name === "mobile",
    hasTouch: name === "mobile",
  });

  const page = await context.newPage();

  await page.addStyleTag({
    content: `
      *,*::before,*::after{
        scroll-behavior:auto!important;
        animation-duration:.001ms!important;
        animation-iteration-count:1!important;
        transition-duration:.001ms!important;
      }
    `,
  });

  const url = `${URL}?visual_board=${Date.now()}_${name}`;
  console.log(`Capturing ${name}: ${url}`);

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  
  await page.waitForTimeout(1200);
  await page.evaluate(async () => {
    const imgs = Array.from(document.images);
    await Promise.allSettled(imgs.map((img) => {
      if (img.complete) return Promise.resolve();
      return new Promise((resolve) => {
        img.addEventListener("load", resolve, { once: true });
        img.addEventListener("error", resolve, { once: true });
        setTimeout(resolve, 1600);
      });
    }));
  });

  await page.waitForTimeout(650);

  const data = await page.evaluate(async (contracts) => {
    const one = (sel) => document.querySelector(sel);
    const all = (sel) => Array.from(document.querySelectorAll(sel));
    const clean = (txt) => String(txt || "").replace(/\s+/g, " ").trim();

    const contractStatus = {};
    for (const [key, selector] of Object.entries(contracts)) {
      contractStatus[key] = {
        selector,
        present: Boolean(one(selector)),
        count: all(selector).length,
      };
    }

    const html = document.documentElement;
    const body = document.body;

    return {
      title: document.title,
      h1: clean(one("h1")?.textContent),
      pageMode: html.getAttribute("data-ff-page") || "",
      bodyClass: body?.className || "",
      width: window.innerWidth,
      height: window.innerHeight,
      scrollWidth: Math.max(html.scrollWidth, body?.scrollWidth || 0),
      scrollHeight: Math.max(html.scrollHeight, body?.scrollHeight || 0),
      overflowX: Math.max(html.scrollWidth, body?.scrollWidth || 0) > window.innerWidth + 2,
      images: document.images.length,
      brokenImages: await Promise.all(Array.from(document.images).map(async (img) => {
        const src = img.currentSrc || img.src || "";
        if (!src) return "";

        // Fast path: browser decoded it as a real image.
        if (img.complete && img.naturalWidth > 0) return "";

        // Slow path: prove the URL is actually loadable. This avoids false positives
        // caused by fallback swaps, delayed decode, or headless image timing.
        try {
          const probe = new Image();
          probe.decoding = "async";
          probe.src = src;

          await new Promise((resolve) => {
            if (probe.complete && probe.naturalWidth > 0) return resolve();
            probe.addEventListener("load", resolve, { once: true });
            probe.addEventListener("error", resolve, { once: true });
            setTimeout(resolve, 2200);
          });

          if (probe.complete && probe.naturalWidth > 0) return "";
        } catch {}

        // Final network proof. Static media may be valid even if the DOM image was
        // swapped during runtime fallback.
        try {
          const res = await fetch(src, { cache: "no-store" });
          const type = res.headers.get("content-type") || "";
          if (res.ok && type.startsWith("image/")) return "";
        } catch {}

        return src;
      })).then((items) => items.filter(Boolean)),
      contracts: contractStatus,
      headings: Array.from(document.querySelectorAll("h1,h2,h3"))
        .slice(0, 30)
        .map((node) => `${node.tagName.toLowerCase()}: ${clean(node.textContent).slice(0, 120)}`),
    };
  }, contracts);

  const image = `campaign-${name}-full.png`;
  await page.screenshot({
    path: path.join(OUT, image),
    fullPage: true,
    animations: "disabled",
  });

  results.push({ name, width, height, image, data });

  await context.close();
}

await browser.close();

fs.writeFileSync(
  path.join(OUT, "dom-contract.json"),
  JSON.stringify({ generatedAt: new Date().toISOString(), url: URL, results }, null, 2)
);

const md = [
  "# FutureFunded Campaign Visual Review",
  "",
  `Generated: ${new Date().toISOString()}`,
  `URL: ${URL}`,
  "",
  "## Screenshots",
  "",
  ...results.flatMap((r) => [
    `### ${r.name} — ${r.width}×${r.height}`,
    "",
    `- Screenshot: \`${r.image}\``,
    `- H1: ${r.data.h1 || "MISSING"}`,
    `- Horizontal overflow: ${r.data.overflowX ? "REVIEW" : "none detected"}`,
    `- Broken images: ${r.data.brokenImages.length}`,
    ...(r.data.brokenImages.length
      ? ["", "Broken image URLs:", ...r.data.brokenImages.map((src) => `- ${src}`)]
      : []),
    `- Page height: ${r.data.scrollHeight}px`,
    "",
    "| Contract | Status | Count |",
    "|---|---:|---:|",
    ...Object.entries(r.data.contracts).map(([k, v]) => `| ${k} | ${v.present ? "PASS" : "MISSING"} | ${v.count} |`),
    "",
  ]),
].join("\n");

fs.writeFileSync(path.join(OUT, "review.md"), md);

const cards = results.map((r) => {
  const rows = Object.entries(r.data.contracts).map(([k, v]) => `
    <tr>
      <td>${esc(k)}</td>
      <td>${v.present ? "✅ PASS" : "❌ MISSING"}</td>
      <td>${v.count}</td>
      <td><code>${esc(v.selector)}</code></td>
    </tr>
  `).join("");

  return `
    <section class="card">
      <div class="head">
        <div>
          <p>${esc(r.name)} • ${r.width}×${r.height}</p>
          <h2>${esc(r.data.h1 || "Campaign screenshot")}</h2>
        </div>
        <strong class="${r.data.overflowX || r.data.brokenImages.length ? "bad" : "ok"}">
          ${r.data.overflowX || r.data.brokenImages.length ? "REVIEW" : "PASS"}
        </strong>
      </div>
      <div class="metrics">
        <span>Overflow: ${r.data.overflowX ? "Yes" : "No"}</span>
        <span>Images: ${r.data.images}</span>
        <span>Broken: ${r.data.brokenImages.length}</span>
        <span>Height: ${r.data.scrollHeight}px</span>
      </div>
      <details open>
        <summary>DOM contracts</summary>
        <table>
          <thead><tr><th>Contract</th><th>Status</th><th>Count</th><th>Selector</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </details>
      <a href="./${esc(r.image)}" target="_blank">Open full screenshot</a>
      <img src="./${esc(r.image)}" alt="${esc(r.name)} screenshot">
    </section>
  `;
}).join("");

const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FutureFunded Campaign Visual Board</title>
  <style>
    body{margin:0;background:#f6ead8;color:#170f0a;font-family:Inter,system-ui,sans-serif}
    main{width:min(100% - 28px,1480px);margin:auto;padding:28px 0 60px}
    .hero,.card{border:1px solid rgba(72,44,25,.14);border-radius:28px;background:rgba(255,255,255,.86);box-shadow:0 24px 70px rgba(55,36,20,.12);padding:24px;margin:18px 0}
    h1{font-size:clamp(2.3rem,4vw,4.8rem);line-height:.9;letter-spacing:-.075em;margin:0}
    h2{font-size:clamp(1.5rem,2.4vw,3rem);line-height:.92;letter-spacing:-.06em;margin:0}
    p{color:rgba(44,31,21,.66);font-weight:750}
    .head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}
    .ok{color:#127c6f}.bad{color:#b42318}
    .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0}
    .metrics span{border:1px solid rgba(72,44,25,.14);border-radius:14px;background:#fff;padding:10px;font-weight:850}
    table{width:100%;border-collapse:collapse;margin-top:10px;font-size:.85rem}
    th,td{border-top:1px solid rgba(72,44,25,.14);padding:8px;text-align:left;vertical-align:top}
    code{background:#fff;border:1px solid rgba(72,44,25,.14);border-radius:999px;padding:2px 7px}
    a{display:inline-flex;margin:12px 0;border:1px solid rgba(72,44,25,.14);border-radius:999px;background:#fff;color:#170f0a;text-decoration:none;font-weight:900;padding:9px 14px}
    img{display:block;width:100%;border:1px solid rgba(72,44,25,.14);border-radius:22px;background:white}
    @media(max-width:760px){.head,.metrics{display:grid;grid-template-columns:1fr}}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p>FutureFunded Visual Review Board</p>
      <h1>Campaign page screenshot authority.</h1>
      <p>Generated from <code>${esc(URL)}</code>. Use this before touching CSS.</p>
      <p><a href="./review.md">Review markdown</a> <a href="./dom-contract.json">DOM contract JSON</a></p>
    </section>
    ${cards}
  </main>
</body>
</html>`;

fs.writeFileSync(path.join(OUT, "index.html"), html);

console.log("");
console.log("✅ Visual review board generated");
console.log(`HTML: ${path.join(OUT, "index.html")}`);
console.log(`Markdown: ${path.join(OUT, "review.md")}`);
