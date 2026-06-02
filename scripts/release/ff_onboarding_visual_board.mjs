import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseURL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const route = process.env.FF_ONBOARDING_ROUTE || "/platform/onboarding";
const url = new URL(route, baseURL).toString();

const outDir = path.join("audit_outputs", "onboarding-polish", "visual-board-latest");

const viewports = [
  { name: "mobile", width: 390, height: 1400, deviceScaleFactor: 2, isMobile: true },
  { name: "tablet", width: 768, height: 1500, deviceScaleFactor: 1, isMobile: false },
  { name: "desktop", width: 1440, height: 1100, deviceScaleFactor: 1, isMobile: false },
];

function esc(value = "") {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[ch]);
}

function isIgnoredConsoleNoise(text = "") {
  return [
    /Applying inline style violates/i,
    /Refused to apply inline style/i,
    /violates the following Content Security Policy/i,
    /A listener indicated an asynchronous response/i,
    /Extension context invalidated/i,
    /chrome-extension:\/\//i,
    /moz-extension:\/\//i,
  ].some((pattern) => pattern.test(String(text || "")));
}

async function main() {
  await fs.rm(outDir, { recursive: true, force: true });
  await fs.mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: viewport.deviceScaleFactor,
      isMobile: viewport.isMobile,
      colorScheme: "light",
      reducedMotion: "reduce",
    });

    const page = await context.newPage();
    const consoleErrors = [];
    const requestFailures = [];

    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      if (!isIgnoredConsoleNoise(text)) consoleErrors.push(text);
    });

    page.on("requestfailed", (req) => {
      requestFailures.push(`${req.method()} ${req.url()} :: ${req.failure()?.errorText || "failed"}`);
    });

    const target = `${url}?visual_board=${Date.now()}_${viewport.name}`;
    console.log(`Capturing onboarding ${viewport.name}: ${target}`);

    const response = await page.goto(target, {
      waitUntil: "domcontentloaded",
      timeout: 60000,
    });

    await page.waitForTimeout(1200);

    const data = await page.evaluate(() => {
      const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const one = (selector) => document.querySelector(selector);
      const all = (selector) => Array.from(document.querySelectorAll(selector));
      const html = document.documentElement;
      const body = document.body;
      const text = clean(body?.innerText || "").toLowerCase();

      const contracts = {
        pageRoot: all("[data-ff-onboard-root], [data-ff-onboarding-root]").length,
        hero: all(".ffOnboardV2__hero").length,
        readiness: all(".ffOnboardV2__readiness").length,
        formSections: all("[data-ff-onboard-form-section]").length,
        themePicker: all("[data-ff-theme-picker]").length,
        saveButton: all("[data-ff-save-onboarding]").length,
        campaignBasics: all('[data-ff-onboard-section="campaign-basics"]').length,
        givingReadiness: all('[data-ff-onboard-section="giving-readiness"]').length,
        sponsorPackages: all('[data-ff-onboard-section="sponsor-packages"]').length,
      };

      return {
        title: document.title,
        h1: clean(one("h1")?.textContent),
        h1Count: all("h1").length,
        width: window.innerWidth,
        height: window.innerHeight,
        scrollWidth: Math.max(html.scrollWidth, body?.scrollWidth || 0),
        scrollHeight: Math.max(html.scrollHeight, body?.scrollHeight || 0),
        overflowX: Math.max(html.scrollWidth, body?.scrollWidth || 0) > window.innerWidth + 2,
        hasPrivateCopy: text.includes("public campaign content stays private"),
        hasNoPaymentCopy: text.includes("no payment") || text.includes("private launch workspace"),
        contracts,
      };
    });

    const image = `onboarding-${viewport.name}-full.png`;
    await page.screenshot({
      path: path.join(outDir, image),
      fullPage: true,
    });

    results.push({
      name: viewport.name,
      width: viewport.width,
      height: viewport.height,
      status: response?.status() || null,
      ok: response?.ok() || false,
      image,
      data,
      consoleErrors,
      requestFailures,
    });

    await context.close();
  }

  await browser.close();

  const review = [
    "# FutureFunded Onboarding Visual Review",
    "",
    `Generated: ${new Date().toISOString()}`,
    `URL: ${url}`,
    "",
    "## Screenshots",
    "",
    ...results.flatMap((r) => [
      `### ${r.name} — ${r.width}×${r.height}`,
      "",
      `- Screenshot: \`${r.image}\``,
      `- Status: ${r.status}`,
      `- H1: ${r.data.h1 || "MISSING"}`,
      `- H1 count: ${r.data.h1Count}`,
      `- Horizontal overflow: ${r.data.overflowX ? "REVIEW" : "none detected"}`,
      `- Console errors: ${r.consoleErrors.length}`,
      `- Request failures: ${r.requestFailures.length}`,
      `- Page height: ${r.data.scrollHeight}px`,
      `- Private copy: ${r.data.hasPrivateCopy}`,
      `- Reassurance copy: ${r.data.hasNoPaymentCopy}`,
      "",
      "| Contract | Status | Count |",
      "|---|---:|---:|",
      ...Object.entries(r.data.contracts).map(([k, count]) => `| ${k} | ${count ? "PASS" : "MISSING"} | ${count} |`),
      "",
      `![${r.name}](${r.image})`,
      "",
    ]),
  ].join("\n");

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FutureFunded Onboarding Visual Board</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6efe5; color: #17120f; }
    main { width: min(1600px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 64px; }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 5vw, 56px); letter-spacing: -.06em; }
    .meta { color: rgba(23,18,15,.62); margin-bottom: 28px; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; align-items: start; }
    article { background: rgba(255,255,255,.72); border: 1px solid rgba(72,44,25,.12); border-radius: 24px; padding: 14px; box-shadow: 0 20px 70px rgba(72,44,25,.1); }
    .badge { display:inline-flex; border-radius:999px; padding:6px 10px; font-weight:900; font-size:12px; background:#047857; color:#fff; }
    .badge.bad { background:#b91c1c; }
    dl { display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:12px; }
    dt { color:rgba(23,18,15,.58); font-weight:800; }
    dd { margin:0; font-weight:900; }
    img { width:100%; height:auto; border-radius:18px; border:1px solid rgba(72,44,25,.12); background:#fff; }
    @media (max-width: 1100px) { .grid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
<main>
  <h1>Onboarding screenshot board</h1>
  <p class="meta">${esc(url)}</p>
  <div class="grid">
    ${results.map((r) => {
      const bad = !r.ok || r.data.overflowX || r.consoleErrors.length || r.requestFailures.length || r.data.h1Count !== 1;
      return `<article>
        <span class="badge ${bad ? "bad" : ""}">${bad ? "REVIEW" : "PASS"}</span>
        <h2>${esc(r.name)} · ${r.width}×${r.height}</h2>
        <dl>
          <dt>Height</dt><dd>${esc(r.data.scrollHeight)}px</dd>
          <dt>H1s</dt><dd>${esc(r.data.h1Count)}</dd>
          <dt>Overflow</dt><dd>${esc(r.data.overflowX)}</dd>
          <dt>Console</dt><dd>${esc(r.consoleErrors.length)}</dd>
        </dl>
        <img src="${esc(r.image)}" alt="${esc(r.name)} onboarding screenshot">
      </article>`;
    }).join("")}
  </div>
</main>
</body>
</html>`;

  await fs.writeFile(path.join(outDir, "review.md"), review);
  await fs.writeFile(path.join(outDir, "index.html"), html);
  await fs.writeFile(path.join(outDir, "results.json"), JSON.stringify({ url, results }, null, 2));

  const failed = results.filter((r) =>
    !r.ok ||
    r.data.overflowX ||
    r.consoleErrors.length ||
    r.requestFailures.length ||
    r.data.h1Count !== 1 ||
    !r.data.contracts.pageRoot ||
    !r.data.contracts.hero ||
    !r.data.contracts.readiness ||
    !r.data.contracts.saveButton
  );

  console.log(`ONBOARDING_BOARD_OUT=${outDir}`);
  console.log(`ONBOARDING_BOARD_REVIEW=${path.join(outDir, "review.md")}`);
  console.log(failed.length ? `ONBOARDING_VISUAL_BOARD=FAIL failures=${failed.length}` : "ONBOARDING_VISUAL_BOARD=PASS");

  if (failed.length) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
