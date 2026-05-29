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
const TOKEN =
  process.env.FF_OPERATOR_ACCESS_TOKEN ||
  process.env.FF_DASHBOARD_ACCESS_TOKEN ||
  process.env.FF_OPERATOR_TOKEN ||
  "";

const OUT_ROOT = path.join(ROOT, "audit_outputs", "hoi-6g-onboarding-operator");
const STAMP = new Date().toISOString().replace(/[:.]/g, "-");
const RUN_DIR = path.join(OUT_ROOT, STAMP);
const LATEST_DIR = path.join(OUT_ROOT, "latest");
const SHOTS_DIR = path.join(RUN_DIR, "screenshots");

const VIEWPORTS = [
  { key: "mobile", width: 390, height: 844 },
  { key: "desktop", width: 1440, height: 1100 },
];

function urlFor(route) {
  return new URL(route, `${BASE_URL}/`).toString();
}

function redact(url) {
  return url.replace(/([?&](?:access_token|operator_token)=)[^&]+/g, "$1<redacted>");
}

function clean(value = "") {
  return String(value).replace(/\s+/g, " ").trim();
}

function pageList() {
  const pages = [
    {
      key: "onboarding",
      label: "Onboarding",
      route: "/platform/onboarding",
      expect: 200,
      mustContainAny: ["launch", "campaign", "workspace", "setup"],
    },
    {
      key: "dashboard_locked",
      label: "Dashboard locked",
      route: "/platform/dashboard",
      expectAny: [401, 403],
      mustContainAny: ["operator", "access", "dashboard", "required"],
    },
  ];

  if (TOKEN) {
    pages.push(
      {
        key: "dashboard_access_token",
        label: "Dashboard access_token",
        route: `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}`,
        expect: 200,
        mustContainAny: ["dashboard", "operator", "ledger", "sponsor", "donation"],
      },
      {
        key: "dashboard_operator_token",
        label: "Dashboard operator_token",
        route: `/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}`,
        expect: 200,
        mustContainAny: ["dashboard", "operator", "ledger", "sponsor", "donation"],
      }
    );
  }

  return pages;
}

async function ensureDirs() {
  await fs.mkdir(SHOTS_DIR, { recursive: true });
}

async function audit(browser, pageDef, viewport) {
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

  const url = urlFor(pageDef.route);
  let status = null;
  let navError = "";

  try {
    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 45000,
    });
    status = response?.status() ?? null;
    await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});
    await page.evaluate(() => document.fonts?.ready).catch(() => {});
    await page.waitForTimeout(300);
  } catch (error) {
    navError = error.message;
  }

  const shotName = `${pageDef.key}-${viewport.key}.png`;
  const shotPath = path.join(SHOTS_DIR, shotName);
  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});

  const dom = await page.evaluate(() => {
    const visible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };

    const textOf = (el) =>
      [
        el.innerText,
        el.getAttribute("aria-label"),
        el.getAttribute("title"),
        el.getAttribute("value"),
      ]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

    const bodyText = document.body?.innerText?.replace(/\s+/g, " ").trim() || "";

    const controls = [
      ...document.querySelectorAll("a,button,[role='button'],input[type='submit'],input[type='button']"),
    ]
      .filter(visible)
      .map(textOf)
      .filter(Boolean)
      .slice(0, 30);

    const hooks = [...document.querySelectorAll("*")]
      .flatMap((el) =>
        [...el.attributes]
          .filter((a) => a.name.startsWith("data-ff"))
          .map((a) => `${a.name}${a.value ? `=${a.value}` : ""}`)
      )
      .sort()
      .slice(0, 120);

    return {
      title: document.title || "",
      bodyText,
      h1: [...document.querySelectorAll("h1")].filter(visible).map(textOf),
      controls,
      hooks,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  }).catch((error) => ({
    evalError: error.message,
    bodyText: "",
    h1: [],
    controls: [],
    hooks: [],
    scrollWidth: 0,
    clientWidth: 0,
  }));

  await context.close();

  const findings = [];

  if (navError) findings.push(`Navigation failed: ${navError}`);

  if (pageDef.expect && status !== pageDef.expect) {
    findings.push(`Expected HTTP ${pageDef.expect}, got ${status}`);
  }

  if (pageDef.expectAny && !pageDef.expectAny.includes(status)) {
    findings.push(`Expected HTTP ${pageDef.expectAny.join("/")} got ${status}`);
  }

  if (dom.scrollWidth > dom.clientWidth + 2) {
    findings.push(`Horizontal overflow: ${dom.scrollWidth} > ${dom.clientWidth}`);
  }

  const lower = (dom.bodyText || "").toLowerCase();
  const copyHits = (pageDef.mustContainAny || []).filter((token) => lower.includes(token.toLowerCase()));

  if (status === 200 && pageDef.mustContainAny?.length && copyHits.length === 0) {
    findings.push(`Expected copy missing: ${pageDef.mustContainAny.join(", ")}`);
  }

  const actionableConsole = consoleErrors.filter((text) => {
    if (pageDef.expectAny?.includes(403) || pageDef.expectAny?.includes(401)) {
      return !/Failed to load resource: the server responded with a status of (401|403)/i.test(text);
    }
    return true;
  });

  if (actionableConsole.length) {
    findings.push(`Console errors: ${actionableConsole.slice(0, 3).join(" | ")}`);
  }

  if (pageErrors.length) {
    findings.push(`Page errors: ${pageErrors.slice(0, 3).join(" | ")}`);
  }

  return {
    key: pageDef.key,
    label: pageDef.label,
    viewport: viewport.key,
    url: redact(url),
    status,
    ok: findings.length === 0,
    findings,
    h1: dom.h1,
    controls: dom.controls,
    hooks: dom.hooks,
    screenshot: path.relative(RUN_DIR, shotPath),
  };
}

function markdown(report) {
  const lines = [
    "# FutureFunded HOI 6G — Onboarding + Operator Dashboard Proof",
    "",
    `**Status:** ${report.ok ? "PASS ✅" : "REVIEW ⚠️"}`,
    `**Base URL:** ${report.baseUrl}`,
    `**Checked:** ${report.checkedAt}`,
    `**Operator token provided:** ${report.tokenProvided ? "yes" : "no"}`,
    "",
    "## Summary",
    "",
    `- Results: ${report.results.length}`,
    `- Errors: ${report.errorCount}`,
    `- Screenshots: \`${report.screenshotsDir}\``,
    "",
    "| Surface | Viewport | Status | Result | Screenshot |",
    "|---|---:|---:|---:|---|",
    ...report.results.map((r) =>
      `| ${r.label} | ${r.viewport} | ${r.status} | ${r.ok ? "PASS ✅" : "REVIEW ⚠️"} | \`${r.screenshot}\` |`
    ),
    "",
  ];

  for (const result of report.results) {
    lines.push(`## ${result.label} / ${result.viewport}`);
    lines.push("");
    lines.push(`- URL: ${result.url}`);
    lines.push(`- Status: ${result.status}`);
    lines.push(`- H1: ${result.h1.join(" | ") || "none"}`);

    if (!result.findings.length) {
      lines.push("- ✅ No findings.");
    } else {
      for (const finding of result.findings) {
        lines.push(`- ❌ ${finding}`);
      }
    }

    lines.push("");
  }

  if (!report.tokenProvided) {
    lines.push(
      "## Token note",
      "",
      "No operator token was provided. Set `FF_OPERATOR_ACCESS_TOKEN` to prove the unlocked dashboard.",
      ""
    );
  }

  return lines.join("\n");
}

await ensureDirs();

const browser = await chromium.launch({ headless: true });
const results = [];

for (const pageDef of pageList()) {
  for (const viewport of VIEWPORTS) {
    console.log(`Checking ${pageDef.label} / ${viewport.key}`);
    results.push(await audit(browser, pageDef, viewport));
  }
}

await browser.close();

const errorCount = results.reduce((sum, r) => sum + r.findings.length, 0);
const tokenProvided = Boolean(TOKEN);
const tokenResults = results.filter((r) => r.key.includes("token"));
const tokenOk = !tokenProvided || tokenResults.some((r) => r.status === 200 && r.ok);

const report = {
  ok: errorCount === 0 && tokenOk,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  tokenProvided,
  errorCount,
  screenshotsDir: SHOTS_DIR,
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
