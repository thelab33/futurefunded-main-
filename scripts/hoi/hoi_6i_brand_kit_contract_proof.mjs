#!/usr/bin/env node
import fs from "node:fs/promises";
import fss from "node:fs";
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
const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6i-brand-kit-contract");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");
const SHOTS_DIR = path.join(RUN_DIR, "screenshots");

const CONTRACT_KEY = "futurefunded:brand-kit-contract:v1";
const PRESETS = ["elite", "school", "club", "nonprofit"];

function urlFor(route) {
  return new URL(route, `${BASE_URL}/`).toString();
}

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

async function ensureDirs() {
  await fs.mkdir(SHOTS_DIR, { recursive: true });
}

async function runPreset(browser, preset) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
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

  const findings = [];

  const onboardingUrl = urlFor("/platform/onboarding");
  const campaignUrl = urlFor("/c/connect-atx-elite");

  const onboardingResponse = await page.goto(onboardingUrl, {
    waitUntil: "domcontentloaded",
    timeout: 45000,
  });

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  await page.waitForTimeout(250);

  const buttonFound = await page.locator(`[data-ff-theme-preset][data-preset="${preset}"]`).count();

  if (!buttonFound) {
    findings.push(`Missing onboarding preset button: ${preset}`);
  } else {
    await page.locator(`[data-ff-theme-preset][data-preset="${preset}"]`).first().click();
  }

  const saveCount = await page.locator("[data-ff-save-onboarding]").count();
  if (saveCount) {
    await page.locator("[data-ff-save-onboarding]").first().click();
  }

  await page.waitForTimeout(250);

  const onboardingState = await page.evaluate((key) => {
    const root = document.querySelector("[data-ff-onboard-root]");
    let contract = null;

    try {
      contract = JSON.parse(window.localStorage.getItem(key) || "null");
    } catch {}

    return {
      rootPreset: root?.getAttribute("data-ff-brand-preset") || "",
      saved: root?.getAttribute("data-ff-brand-contract-saved") || "",
      contract,
    };
  }, CONTRACT_KEY);

  if (onboardingResponse?.status() !== 200) {
    findings.push(`Onboarding returned ${onboardingResponse?.status()}`);
  }

  if (onboardingState.rootPreset !== preset) {
    findings.push(`Onboarding root preset expected ${preset}, got ${onboardingState.rootPreset}`);
  }

  if (onboardingState.contract?.preset !== preset) {
    findings.push(`Saved contract preset expected ${preset}, got ${onboardingState.contract?.preset}`);
  }

  await page.screenshot({
    path: path.join(SHOTS_DIR, `onboarding-${preset}-mobile.png`),
    fullPage: true,
  });

  const campaignResponse = await page.goto(campaignUrl, {
    waitUntil: "domcontentloaded",
    timeout: 45000,
  });

  await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
  await page.evaluate(() => document.fonts?.ready).catch(() => {});
  await page.waitForTimeout(350);

  const campaignState = await page.evaluate(() => {
    const root =
      document.querySelector("[data-ff-page-root]") ||
      document.querySelector(".ff-campaign") ||
      document.body;

    const checkout =
      document.querySelector("[data-ff-open-checkout]") ||
      document.querySelector("[data-ff-donate-trigger]") ||
      document.querySelector("[data-ff-payment-trigger]");

    const rootStyle = root ? window.getComputedStyle(root) : null;
    const checkoutStyle = checkout ? window.getComputedStyle(checkout) : null;

    return {
      rootPreset: root?.getAttribute("data-ff-brand-preset") || "",
      bodyPreset: document.body?.getAttribute("data-ff-brand-preset") || "",
      source: root?.getAttribute("data-ff-brand-kit-source") || "",
      primary: rootStyle?.getPropertyValue("--ff-brand-primary").trim() || "",
      campaignPrimary: rootStyle?.getPropertyValue("--ff-campaign-primary").trim() || "",
      checkoutBackground: checkoutStyle?.backgroundImage || checkoutStyle?.backgroundColor || "",
    };
  });

  if (campaignResponse?.status() !== 200) {
    findings.push(`Campaign returned ${campaignResponse?.status()}`);
  }

  if (campaignState.rootPreset !== preset && campaignState.bodyPreset !== preset) {
    findings.push(
      `Campaign preset expected ${preset}, got root=${campaignState.rootPreset || "<empty>"} body=${campaignState.bodyPreset || "<empty>"}`
    );
  }

  await page.screenshot({
    path: path.join(SHOTS_DIR, `campaign-${preset}-mobile.png`),
    fullPage: true,
  });

  const actionableConsole = consoleErrors.filter((text) => {
    return !/favicon/i.test(text);
  });

  if (actionableConsole.length) {
    findings.push(`Console errors: ${actionableConsole.slice(0, 3).join(" | ")}`);
  }

  if (pageErrors.length) {
    findings.push(`Page errors: ${pageErrors.slice(0, 3).join(" | ")}`);
  }

  await context.close();

  return {
    preset,
    ok: findings.length === 0,
    findings,
    onboarding: onboardingState,
    campaign: campaignState,
  };
}

function markdown(report) {
  const lines = [
    "# FutureFunded HOI 6I — Brand Kit Contract Proof",
    "",
    `**Status:** ${report.ok ? "PASS ✅" : "REVIEW ⚠️"}`,
    `**Base URL:** ${report.baseUrl}`,
    `**Checked:** ${report.checkedAt}`,
    "",
    "## Summary",
    "",
    `- Presets checked: ${report.results.length}`,
    `- Errors: ${report.errorCount}`,
    `- Screenshots: \`${report.screenshotsDir}\``,
    "",
    "| Preset | Result | Onboarding root | Campaign root | Source |",
    "|---|---:|---:|---:|---:|",
    ...report.results.map((r) => {
      return `| ${r.preset} | ${r.ok ? "PASS ✅" : "REVIEW ⚠️"} | ${r.onboarding.rootPreset || "—"} | ${r.campaign.rootPreset || r.campaign.bodyPreset || "—"} | ${r.campaign.source || "—"} |`;
    }),
    "",
  ];

  for (const result of report.results) {
    lines.push(`## ${result.preset}`);
    lines.push("");

    if (!result.findings.length) {
      lines.push("- ✅ No findings.");
    } else {
      for (const finding of result.findings) {
        lines.push(`- ❌ ${finding}`);
      }
    }

    lines.push("");
  }

  return lines.join("\n");
}

await ensureDirs();

const browser = await chromium.launch({ headless: true });
const results = [];

for (const preset of PRESETS) {
  console.log(`Checking brand kit preset: ${preset}`);
  results.push(await runPreset(browser, preset));
}

await browser.close();

const errorCount = results.reduce((sum, result) => sum + result.findings.length, 0);

const report = {
  ok: errorCount === 0,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  screenshotsDir: SHOTS_DIR,
  errorCount,
  results,
};

await fs.writeFile(path.join(RUN_DIR, "report.json"), JSON.stringify(report, null, 2) + "\n");
await fs.writeFile(path.join(RUN_DIR, "report.md"), markdown(report));

await fs.rm(LATEST_DIR, { recursive: true, force: true });
await fs.cp(RUN_DIR, LATEST_DIR, { recursive: true });

console.log("");
console.log(fss.readFileSync(path.join(LATEST_DIR, "report.md"), "utf8"));
console.log("");
console.log(`Report: ${path.join(LATEST_DIR, "report.md")}`);

process.exit(report.ok ? 0 : 1);
