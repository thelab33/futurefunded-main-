#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";

let playwright;
try {
  playwright = await import("@playwright/test");
} catch {
  playwright = await import("playwright");
}

const { chromium } = playwright;

const ROOT = process.cwd();
const BASE_URL = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/+$/, "");
const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6m-campaign-cta-compression");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");
const SHOTS_DIR = path.join(RUN_DIR, "screenshots");

function urlFor(route) {
  return new URL(route, `${BASE_URL}/`).toString();
}

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

await fs.mkdir(SHOTS_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const results = [];

for (const viewport of [
  { key: "mobile", width: 390, height: 844 },
  { key: "desktop", width: 1440, height: 980 },
]) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });

  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(clean(msg.text()));
  });

  page.on("pageerror", (err) => {
    pageErrors.push(clean(err.message));
  });

  const response = await page.goto(urlFor("/c/connect-atx-elite"), {
    waitUntil: "domcontentloaded",
    timeout: 45000,
  });

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  await page.waitForTimeout(350);

  await page.screenshot({
    path: path.join(SHOTS_DIR, `campaign-${viewport.key}.png`),
    fullPage: false,
  });

  const metrics = await page.evaluate(() => {
    const visible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };

    const controls = [...document.querySelectorAll("a,button,input,select,textarea,[role='button']")].filter(visible);

    return {
      h1: document.querySelector("h1")?.innerText?.replace(/\s+/g, " ").trim() || "",
      visibleControls: controls.length,
      checkoutTriggers: [...document.querySelectorAll("[data-ff-open-checkout]")].filter(visible).length,
      sponsorTriggers: [...document.querySelectorAll("[data-ff-open-sponsor],[data-ff-sponsor-trigger]")].filter(visible).length,
      shareTriggers: [...document.querySelectorAll("[data-ff-share-trigger]")].filter(visible).length,
      impactButtons: [...document.querySelectorAll(".ff-impactChip[data-ff-open-checkout]")].filter(visible).length,
      impactStaticCards: [...document.querySelectorAll(".ff-impactChip--static")].filter(visible).length,
      trustLines: [...document.querySelectorAll(".ff-campaignTrustLine")].filter(visible).length,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  });

  await context.close();

  const findings = [];

  if (response?.status() !== 200) findings.push(`Expected 200, got ${response?.status()}`);
  if (!/Fuel|Fund|season|future/i.test(metrics.h1)) findings.push(`Unexpected H1: ${metrics.h1}`);
  if (metrics.checkoutTriggers < 2) findings.push("Expected at least 2 visible checkout triggers.");
  if (metrics.sponsorTriggers < 1) findings.push("Expected at least 1 visible sponsor trigger.");
  if (metrics.shareTriggers < 1 && viewport.key === "desktop") findings.push("Expected desktop share trigger.");
  if (metrics.impactButtons !== 0) findings.push(`Impact chips still clickable checkout buttons: ${metrics.impactButtons}`);
  if (metrics.impactStaticCards < 4) findings.push(`Expected 4 static impact cards, got ${metrics.impactStaticCards}`);
  if (metrics.trustLines < 2) findings.push(`Expected trust lines, got ${metrics.trustLines}`);
  if (metrics.scrollWidth > metrics.clientWidth + 2) findings.push(`Horizontal overflow: ${metrics.scrollWidth} > ${metrics.clientWidth}`);
  if (consoleErrors.length) findings.push(`Console errors: ${consoleErrors.slice(0, 3).join(" | ")}`);
  if (pageErrors.length) findings.push(`Page errors: ${pageErrors.slice(0, 3).join(" | ")}`);

  results.push({
    viewport: viewport.key,
    ok: findings.length === 0,
    findings,
    status: response?.status() ?? null,
    metrics,
    screenshot: `screenshots/campaign-${viewport.key}.png`,
  });
}

await browser.close();

const errorCount = results.reduce((sum, r) => sum + r.findings.length, 0);
const report = {
  ok: errorCount === 0,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  errorCount,
  results,
};

const lines = [
  "# FutureFunded HOI 6M - Campaign CTA Compression Proof",
  "",
  `Status: ${report.ok ? "PASS" : "REVIEW"}`,
  `Base URL: ${BASE_URL}`,
  `Checked: ${report.checkedAt}`,
  "",
  "| Viewport | Status | Controls | Checkout | Sponsor | Share | Static impact | Result |",
  "|---|---:|---:|---:|---:|---:|---:|---:|",
  ...results.map((r) =>
    `| ${r.viewport} | ${r.status} | ${r.metrics.visibleControls} | ${r.metrics.checkoutTriggers} | ${r.metrics.sponsorTriggers} | ${r.metrics.shareTriggers} | ${r.metrics.impactStaticCards} | ${r.ok ? "PASS" : "REVIEW"} |`
  ),
  "",
];

for (const r of results) {
  lines.push(`## ${r.viewport}`);
  lines.push(`- Screenshot: ${r.screenshot}`);
  if (r.findings.length) {
    for (const finding of r.findings) lines.push(`- FAIL: ${finding}`);
  } else {
    lines.push("- No findings.");
  }
  lines.push("");
}

await fs.writeFile(path.join(RUN_DIR, "report.json"), JSON.stringify(report, null, 2) + "\n");
await fs.writeFile(path.join(RUN_DIR, "report.md"), lines.join("\n"));

await fs.rm(LATEST_DIR, { recursive: true, force: true });
await fs.cp(RUN_DIR, LATEST_DIR, { recursive: true });

console.log(lines.join("\n"));
console.log("");
console.log(`Report: ${path.join(LATEST_DIR, "report.md")}`);

process.exit(report.ok ? 0 : 1);
