import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const baseURL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const route = process.env.FF_PLATFORM_ROUTE || "/platform/";
const url = new URL(route, baseURL).toString();

const stamp = new Date().toISOString().replaceAll(":", "-").replaceAll(".", "-");
const outDir = path.join("audit_outputs", "platform-homepage-screenshot-board", stamp);

const viewports = [
  { name: "mobile", width: 390, height: 844, deviceScaleFactor: 2, isMobile: true },
  { name: "tablet", width: 820, height: 1180, deviceScaleFactor: 1, isMobile: false },
  { name: "desktop", width: 1440, height: 1200, deviceScaleFactor: 1, isMobile: false },
];

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[ch]);
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const report = {
    url,
    outDir,
    generatedAt: new Date().toISOString(),
    results: [],
  };

  for (const viewport of viewports) {
    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: viewport.deviceScaleFactor,
      isMobile: viewport.isMobile,
      reducedMotion: "reduce",
    });

    const page = await context.newPage();
    const consoleErrors = [];
    const requestFailures = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    page.on("requestfailed", (req) => {
      requestFailures.push(`${req.method()} ${req.url()} :: ${req.failure()?.errorText || "failed"}`);
    });

    const response = await page.goto(`${url}?board_v=${Date.now()}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });

    await page.evaluate(() => {
      window.scrollTo(0, 0);
    });

    await page.waitForTimeout(650);

    const metrics = await page.evaluate(() => {
      const text = document.body?.innerText || "";
      const normalized = text.replace(/\\s+/g, " ").trim().toLowerCase();
      const h1 = [...document.querySelectorAll("h1")].map((el) => el.innerText.trim());
      const h2 = [...document.querySelectorAll("h2")].map((el) => el.innerText.trim());
      const marker = Boolean(document.querySelector("[data-ff-platform-product-page]"));
      const hero = normalized.includes("launch sponsor-ready fundraising pages people trust");
      const cockpit = normalized.includes("futurefunded campaign cockpit");
      const sponsor = normalized.includes("turn sponsor interest into a premium partner experience");
      const operator = normalized.includes("operator command center");
      const caseStudy = normalized.includes("connect atx elite is the live flagship campaign");
      return {
        title: document.title,
        bodyChars: text.length,
        h1,
        h2Count: h2.length,
        marker,
        hero,
        cockpit,
        sponsor,
        operator,
        caseStudy,
        scrollHeight: document.documentElement.scrollHeight,
        viewportHeight: window.innerHeight,
        overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
      };
    });

    const fullShot = `platform-homepage-${viewport.name}-full.png`;
    const topShot = `platform-homepage-${viewport.name}-top.png`;

    await page.screenshot({
      path: path.join(outDir, fullShot),
      fullPage: true,
    });

    await page.screenshot({
      path: path.join(outDir, topShot),
      fullPage: false,
    });

    const result = {
      viewport,
      status: response?.status() || null,
      ok: response?.ok() || false,
      fullShot,
      topShot,
      metrics,
      consoleErrors,
      requestFailures,
    };

    report.results.push(result);
    await context.close();
  }

  await browser.close();

  await fs.writeFile(path.join(outDir, "report.json"), JSON.stringify(report, null, 2));

  const md = [
    "# FutureFunded Platform Homepage Screenshot Board",
    "",
    `URL: ${url}`,
    `Generated: ${report.generatedAt}`,
    "",
    "## Results",
    "",
    ...report.results.flatMap((r) => [
      `### ${r.viewport.name}`,
      "",
      `- Status: ${r.status}`,
      `- Title: ${r.metrics.title}`,
      `- H1: ${r.metrics.h1.join(" | ")}`,
      `- H2 count: ${r.metrics.h2Count}`,
      `- Product marker: ${r.metrics.marker}`,
      `- Hero copy: ${r.metrics.hero}`,
      `- Cockpit: ${r.metrics.cockpit}`,
      `- Sponsor engine: ${r.metrics.sponsor}`,
      `- Operator panel: ${r.metrics.operator}`,
      `- Case study: ${r.metrics.caseStudy}`,
      `- Horizontal overflow: ${r.metrics.overflowX}`,
      `- Console errors: ${r.consoleErrors.length}`,
      `- Request failures: ${r.requestFailures.length}`,
      "",
      `![${r.viewport.name} top](${r.topShot})`,
      "",
      `![${r.viewport.name} full](${r.fullShot})`,
      "",
    ]),
  ].join("\n");

  await fs.writeFile(path.join(outDir, "report.md"), md);

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FutureFunded Platform Homepage Screenshot Board</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e5e7eb; }
    main { width: min(1440px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 64px; }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 5vw, 56px); letter-spacing: -0.06em; }
    .meta { color: #94a3b8; margin-bottom: 28px; }
    .grid { display: grid; gap: 24px; }
    article { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); border-radius: 24px; padding: 18px; }
    h2 { margin: 0 0 12px; }
    dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px 16px; margin: 0 0 16px; }
    dt { color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    dd { margin: 3px 0 0; font-weight: 800; }
    img { width: 100%; height: auto; border-radius: 18px; border: 1px solid rgba(255,255,255,.12); background: #fff; }
    .shots { display: grid; grid-template-columns: minmax(0, .5fr) minmax(0, 1fr); gap: 18px; align-items: start; }
    @media (max-width: 900px) { .shots { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Platform Homepage Screenshot Board</h1>
    <p class="meta">${escapeHtml(url)} · ${escapeHtml(report.generatedAt)}</p>
    <div class="grid">
      ${report.results.map((r) => `
        <article>
          <h2>${escapeHtml(r.viewport.name)}</h2>
          <dl>
            <div><dt>Status</dt><dd>${escapeHtml(r.status)}</dd></div>
            <div><dt>H1 count</dt><dd>${escapeHtml(r.metrics.h1.length)}</dd></div>
            <div><dt>H2 count</dt><dd>${escapeHtml(r.metrics.h2Count)}</dd></div>
            <div><dt>Overflow X</dt><dd>${escapeHtml(r.metrics.overflowX)}</dd></div>
            <div><dt>Console errors</dt><dd>${escapeHtml(r.consoleErrors.length)}</dd></div>
            <div><dt>Request failures</dt><dd>${escapeHtml(r.requestFailures.length)}</dd></div>
          </dl>
          <div class="shots">
            <div>
              <h3>Top fold</h3>
              <img src="${escapeHtml(r.topShot)}" alt="${escapeHtml(r.viewport.name)} top fold">
            </div>
            <div>
              <h3>Full page</h3>
              <img src="${escapeHtml(r.fullShot)}" alt="${escapeHtml(r.viewport.name)} full page">
            </div>
          </div>
        </article>
      `).join("")}
    </div>
  </main>
</body>
</html>`;

  await fs.writeFile(path.join(outDir, "index.html"), html);

  const failed = report.results.filter((r) =>
    !r.ok ||
    !r.metrics.marker ||
    !r.metrics.hero ||
    !r.metrics.cockpit ||
    !r.metrics.sponsor ||
    !r.metrics.operator ||
    !r.metrics.caseStudy ||
    r.metrics.h1.length !== 1 ||
    r.metrics.overflowX ||
    r.consoleErrors.length ||
    r.requestFailures.length
  );

  console.log(`BOARD_OUT=${outDir}`);
  console.log(`BOARD_INDEX=${path.join(outDir, "index.html")}`);
  console.log(`BOARD_REPORT=${path.join(outDir, "report.md")}`);

  if (failed.length) {
    console.error(`PLATFORM_HOMEPAGE_SCREENSHOT_BOARD=FAIL failures=${failed.length}`);
    process.exit(1);
  }

  console.log("PLATFORM_HOMEPAGE_SCREENSHOT_BOARD=PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
