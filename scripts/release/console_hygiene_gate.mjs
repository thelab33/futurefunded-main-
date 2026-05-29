#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "audit_outputs", "console-hygiene");
fs.mkdirSync(OUT, { recursive: true });

const BASE = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";
const HEADLESS = process.env.PW_HEADLESS !== "0";

const pages = [
  { key: "platform", path: "/platform/", ok: [200] },
  { key: "campaign", path: "/c/connect-atx-elite", ok: [200] },
  { key: "login", path: "/platform/login", ok: [200] },
  { key: "dashboard-locked", path: "/platform/dashboard", ok: [200, 302, 401, 403], allow403Console: true },
  { key: "onboarding", path: "/platform/onboarding", ok: [200, 302, 401, 403, 404], optional: true },
];

if (TOKEN) {
  pages.push({
    key: "dashboard-token",
    path: `/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}`,
    shown: "/platform/dashboard?operator_token=<redacted>",
    ok: [200],
    optional: true,
  });
}

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

function redact(text) {
  return String(text || "").replace(/operator_token=[^&\s]+/g, "operator_token=<redacted>");
}

function isAllowedConsoleNoise(message, spec) {
  const msg = String(message || "");

  if (spec.allow403Console && /status of 403|403 \(FORBIDDEN\)|403 \(Forbidden\)/i.test(msg)) {
    return true;
  }

  // Browser extension / devtools noise; not app-owned.
  if (/chrome-extension:|ResizeObserver loop completed/i.test(msg)) {
    return true;
  }

  return false;
}

function classifyIssue(message) {
  const msg = String(message || "");

  if (/Content Security Policy|violates the following Content Security Policy|Refused to execute|Refused to apply/i.test(msg)) {
    return "csp";
  }

  if (/Uncaught|TypeError|ReferenceError|SyntaxError|is not defined|Cannot read properties/i.test(msg)) {
    return "runtime";
  }

  if (/Failed to load resource/i.test(msg)) {
    return "resource";
  }

  return "console";
}

const browser = await chromium.launch({ headless: HEADLESS });
const errors = [];
const warnings = [];
const results = [];

try {
  for (const [vpName, viewport] of viewports) {
    const context = await browser.newContext({ viewport, ignoreHTTPSErrors: true });

    for (const spec of pages) {
      const page = await context.newPage();
      const key = `${spec.key}-${vpName}`;
      const shown = spec.shown || spec.path;
      const consoleMessages = [];
      const pageErrors = [];

      page.on("console", (msg) => {
        if (["error", "warning"].includes(msg.type())) {
          consoleMessages.push({
            type: msg.type(),
            text: redact(msg.text()),
          });
        }
      });

      page.on("pageerror", (err) => {
        consoleMessages.push({
          type: "pageerror",
          text: redact(err?.message || String(err)),
        });
      });

      try {
        const res = await page.goto(`${BASE}${spec.path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
        await page.waitForLoadState("load", { timeout: 12000 }).catch(() => {});
        await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
        await page.waitForTimeout(350);

        const status = res?.status() || 0;
        if (!spec.ok.includes(status)) pageErrors.push(`unexpected status ${status}`);

        const meaningful = consoleMessages.filter((item) => !isAllowedConsoleNoise(item.text, spec));
        const csp = meaningful.filter((item) => classifyIssue(item.text) === "csp");
        const runtime = meaningful.filter((item) => classifyIssue(item.text) === "runtime");
        const resource = meaningful.filter((item) => classifyIssue(item.text) === "resource");
        const other = meaningful.filter((item) => !["csp", "runtime", "resource"].includes(classifyIssue(item.text)));

        if (csp.length) pageErrors.push(`${csp.length} CSP console violations`);
        if (runtime.length) pageErrors.push(`${runtime.length} runtime console errors`);
        if (resource.length) pageErrors.push(`${resource.length} resource console errors`);
        if (other.length) warnings.push(`${key}: ${other.length} console warnings`);

        const record = {
          key,
          path: shown,
          status,
          pageErrors,
          consoleMessages,
          meaningful,
          csp,
          runtime,
          resource,
          other,
        };

        fs.writeFileSync(path.join(OUT, `${key}.json`), JSON.stringify(record, null, 2));
        results.push(record);

        if (pageErrors.length && !spec.optional) {
          errors.push(`${key}: ${pageErrors.join("; ")}`);
          console.log(`❌ ${key}`);
        } else {
          if (pageErrors.length) warnings.push(`${key}: optional issue: ${pageErrors.join("; ")}`);
          console.log(`✅ ${key}`);
        }
      } catch (err) {
        const msg = `${key}: ${err?.message || err}`;
        if (spec.optional) warnings.push(msg);
        else errors.push(msg);
        console.log(`❌ ${msg}`);
      } finally {
        await page.close();
      }
    }

    await context.close();
  }
} finally {
  await browser.close();
}

const report = {
  ok: errors.length === 0,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE,
  errors,
  warnings,
  results: results.map((r) => ({
    key: r.key,
    path: r.path,
    status: r.status,
    pageErrors: r.pageErrors,
    csp: r.csp,
    runtime: r.runtime,
    resource: r.resource,
    other: r.other,
  })),
};

fs.writeFileSync(path.join(OUT, "latest.json"), JSON.stringify(report, null, 2));

const lines = [
  "# FutureFunded Console Hygiene Gate",
  "",
  `**Status:** ${report.ok ? "PASS ✅" : "FAIL ❌"}`,
  `**Checked:** ${report.checkedAt}`,
  "",
  "## Summary",
  "",
  `- Pages checked: ${results.length}`,
  `- Errors: ${errors.length}`,
  `- Warnings: ${warnings.length}`,
  "",
  "## Errors",
  "",
  ...(errors.length ? errors.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Warnings",
  "",
  ...(warnings.length ? warnings.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Pages",
  "",
  ...results.map((r) => `- **${r.key}** — ${r.path} — status ${r.status}`),
  "",
];

fs.writeFileSync(path.join(OUT, "latest.md"), `${lines.join("\n")}\n`);
console.log("\n" + fs.readFileSync(path.join(OUT, "latest.md"), "utf8"));
console.log(`Report: ${path.join(OUT, "latest.json")}`);

if (!report.ok) process.exit(1);
