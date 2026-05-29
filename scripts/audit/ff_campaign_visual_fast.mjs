#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = process.cwd();
const base = process.env.FF_VISUAL_BASE || "http://127.0.0.1:5000";
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const hideFloating = process.env.FF_VISUAL_HIDE_FLOATING === "1";
const fullPage = process.env.FF_VISUAL_FULL_PAGE === "1";

const outDir = path.join(ROOT, "audit_outputs", "campaign-fast");
await fs.mkdir(outDir, { recursive: true });

const viewports = [
  ["desktop", 1440, 1600],
  ["mobile", 390, 1400],
];

const browser = await chromium.launch({
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
});

const started = Date.now();
const context = await browser.newContext({
  deviceScaleFactor: 1,
});

for (const [name, width, height] of viewports) {
  const page = await context.newPage();
  page.setDefaultTimeout(8000);

  await page.setViewportSize({ width, height });

  const url = `${base}/c/${slug}?visual_fast=${Date.now()}`;
  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 12000,
  });

  await page.addStyleTag({
    content: `
      *,*::before,*::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
        caret-color: transparent !important;
      }

      ${hideFloating ? `
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
      ` : ""}
    `,
  }).catch(() => {});

  await page.evaluate(async () => {
    document.documentElement.style.scrollBehavior = "auto";
    document.body.style.scrollBehavior = "auto";
    if (document.fonts?.ready) {
      try { await document.fonts.ready; } catch {}
    }
    window.scrollTo(0, 0);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });

  await page.waitForTimeout(250);

  const metrics = await page.evaluate(() => ({
    statusText: document.body?.innerText?.slice(0, 120) || "",
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    scrollHeight: document.documentElement.scrollHeight,
  }));

  const file = `campaign-${name}.png`;
  await page.screenshot({
    path: path.join(outDir, file),
    fullPage,
    timeout: 10000,
  });

  console.log(
    `${response?.status() ?? "n/a"} ${name} saved ${path.join(outDir, file)} overflowX=${metrics.scrollWidth > metrics.clientWidth + 3} height=${metrics.scrollHeight}`
  );

  await page.close();
}

await context.close();
await browser.close();

console.log(`Done in ${((Date.now() - started) / 1000).toFixed(1)}s`);
