#!/usr/bin/env node
import { chromium } from "playwright";

const base = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const url = `${base}/c/connect-atx-elite`;
const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

const browser = await chromium.launch({ headless: true });

for (const [name, viewport] of viewports) {
  const page = await browser.newPage({ viewport });

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForLoadState("load", { timeout: 12000 }).catch(() => {});

  await page.evaluate(() => {
    for (const img of document.images) {
      img.loading = "eager";
      img.decoding = "sync";
    }
  });

  const count = await page.locator("img").count();
  for (let i = 0; i < count; i += 1) {
    await page.locator("img").nth(i).scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(80);
  }

  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(500);

  const report = await page.evaluate(() => {
    return Array.from(document.images).map((img) => ({
      src: img.getAttribute("src"),
      currentSrc: img.currentSrc,
      alt: img.alt,
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      broken: Boolean(img.currentSrc || img.src) && (!img.complete || img.naturalWidth <= 0),
    }));
  });

  const broken = report.filter((x) => x.broken);
  console.log(`\n=== ${name.toUpperCase()} IMAGE REPORT ===`);
  console.log(JSON.stringify({ total: report.length, brokenCount: broken.length, broken }, null, 2));

  await page.close();
}

await browser.close();
