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
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6j-header-convergence");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");
const SHOTS_DIR = path.join(RUN_DIR, "screenshots");

const VIEWPORTS = [
  { key: "mobile", width: 390, height: 844 },
  { key: "desktop", width: 1440, height: 980 },
];

const PAGES = [
  ["platform", "Platform", "/platform/", 200, "marketing", "fundraising-platform", false],
  ["campaign", "Campaign", "/c/connect-atx-elite", 200, "campaign", "live-season-fund", false],
  ["login", "Login", "/platform/login", 200, "operator", "organizer-access", false],
  ["onboarding", "Onboarding", "/platform/onboarding", 200, "operator", "launch-workspace", false],
  ["dashboard_locked", "Dashboard locked", "/platform/dashboard", "protected", "", "", true],
];

if (TOKEN) {
  PAGES.push([
    "dashboard_token",
    "Dashboard token",
    `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}`,
    200,
    "operator",
    "operator-command-center",
    false,
  ]);
}

function urlFor(route) {
  return new URL(route, `${BASE_URL}/`).toString();
}

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

function redact(url) {
  return url.replace(/([?&](?:access_token|operator_token)=)[^&]+/g, "$1<redacted>");
}

await fs.mkdir(SHOTS_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const results = [];

for (const [key, label, route, expectedStatus, expectedMode, expectedContext, protectedPage] of PAGES) {
  for (const viewport of VIEWPORTS) {
    console.log(`Checking ${label} / ${viewport.key}`);

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

    let status = null;
    let navError = "";

    try {
      const response = await page.goto(urlFor(route), {
        waitUntil: "domcontentloaded",
        timeout: 45000,
      });
      status = response?.status() ?? null;
      await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
      await page.evaluate(() => document.fonts?.ready).catch(() => {});
      await page.waitForTimeout(250);
    } catch (error) {
      navError = error.message;
    }

    const screenshotName = `${key}-${viewport.key}.png`;
    await page.screenshot({
      path: path.join(SHOTS_DIR, screenshotName),
      fullPage: false,
    }).catch(() => {});

    const header = await page.evaluate(() => {
      const header =
        document.querySelector(".ffShellHeader[data-ff-header]") ||
        document.querySelector("[data-ff-header]");

      if (!header) return { found: false };

      const shell =
        header.querySelector(".ffShellHeader__shell") ||
        header.querySelector(".ff-siteHeader__shell") ||
        header;

      const brand =
        header.querySelector(".ffShellHeader__brand") ||
        header.querySelector(".ff-siteHeader__brand");

      const nav =
        header.querySelector(".ffShellHeader__nav") ||
        header.querySelector(".ff-siteHeader__nav");

      const actions =
        header.querySelector(".ffShellHeader__actions") ||
        header.querySelector(".ff-siteHeader__actions");

      const mark =
        header.querySelector(".ffShellHeader__mark") ||
        header.querySelector(".ff-brandMark__symbol") ||
        header.querySelector(".ff-brandMark__logo");

      const rect = shell.getBoundingClientRect();
      const markRect = mark?.getBoundingClientRect();

      return {
        found: true,
        className: header.className || "",
        mode: header.getAttribute("data-ff-header-mode") || "",
        context: header.getAttribute("data-ff-brand-context") || "",
        brandText: (brand?.innerText || brand?.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim(),
        navText: (nav?.innerText || "").replace(/\s+/g, " ").trim(),
        actionsText: (actions?.innerText || "").replace(/\s+/g, " ").trim(),
        height: Math.round(rect.height),
        width: Math.round(rect.width),
        markWidth: Math.round(markRect?.width || 0),
        markHeight: Math.round(markRect?.height || 0),
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      };
    }).catch((error) => ({
      found: false,
      evalError: error.message,
    }));

    await context.close();

    const findings = [];

    if (navError) findings.push(`Navigation failed: ${navError}`);

    if (protectedPage) {
      if (![401, 403].includes(status)) {
        findings.push(`Expected protected status 401/403, got ${status}`);
      }
    } else {
      if (status !== expectedStatus) {
        findings.push(`Expected HTTP ${expectedStatus}, got ${status}`);
      }

      if (!header.found) {
        findings.push("No shared header found.");
      }

      if (header.found && header.mode !== expectedMode) {
        findings.push(`Expected mode ${expectedMode}, got ${header.mode || "<empty>"}`);
      }

      if (header.found && header.context !== expectedContext) {
        findings.push(`Expected context ${expectedContext}, got ${header.context || "<empty>"}`);
      }

      if (header.found && !/FutureFunded|Connect|ATX|Elite/i.test(header.brandText || "")) {
        findings.push(`Brand text looks wrong: ${header.brandText || "<empty>"}`);
      }

      if (header.found && (header.height < 44 || header.height > 96)) {
        findings.push(`Header height out of range: ${header.height}px`);
      }

      if (header.found && header.markWidth && (header.markWidth < 30 || header.markWidth > 54)) {
        findings.push(`Logo mark width out of range: ${header.markWidth}px`);
      }
    }

    if ((header.scrollWidth || 0) > (header.clientWidth || 0) + 2) {
      findings.push(`Horizontal overflow: ${header.scrollWidth} > ${header.clientWidth}`);
    }

    const actionableConsole = consoleErrors.filter((text) => {
      if (protectedPage) return !/status of (401|403)/i.test(text);
      return true;
    });

    if (actionableConsole.length) {
      findings.push(`Console errors: ${actionableConsole.slice(0, 3).join(" | ")}`);
    }

    if (pageErrors.length) {
      findings.push(`Page errors: ${pageErrors.slice(0, 3).join(" | ")}`);
    }

    results.push({
      key,
      label,
      viewport: viewport.key,
      url: redact(urlFor(route)),
      status,
      ok: findings.length === 0,
      findings,
      header,
      screenshot: `screenshots/${screenshotName}`,
    });
  }
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
  "# FutureFunded HOI 6J - Header Convergence Proof",
  "",
  `Status: ${report.ok ? "PASS" : "REVIEW"}`,
  `Base URL: ${BASE_URL}`,
  `Checked: ${report.checkedAt}`,
  "",
  "| Page | Viewport | Status | Mode | Context | Height | Result |",
  "|---|---:|---:|---:|---:|---:|---:|",
  ...results.map((r) =>
    `| ${r.label} | ${r.viewport} | ${r.status} | ${r.header.mode || "-"} | ${r.header.context || "-"} | ${r.header.height || "-"} | ${r.ok ? "PASS" : "REVIEW"} |`
  ),
  "",
];

for (const r of results) {
  lines.push(`## ${r.label} / ${r.viewport}`);
  lines.push("");
  lines.push(`- URL: ${r.url}`);
  lines.push(`- Brand: ${r.header.brandText || "-"}`);
  lines.push(`- Nav: ${r.header.navText || "-"}`);
  lines.push(`- Actions: ${r.header.actionsText || "-"}`);
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

console.log("");
console.log(lines.join("\n"));
console.log("");
console.log(`Report: ${path.join(LATEST_DIR, "report.md")}`);

process.exit(report.ok ? 0 : 1);
