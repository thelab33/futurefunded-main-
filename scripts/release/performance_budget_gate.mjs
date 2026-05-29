#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "audit_outputs", "performance-budget");
fs.mkdirSync(OUT, { recursive: true });

const BASE = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";
const HEADLESS = process.env.PW_HEADLESS !== "0";
const STRICT = process.env.FF_PERF_STRICT === "1";

const KB = 1024;

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

const defaultBudget = {
  requests: 90,
  totalKB: 2200,
  htmlKB: 450,
  cssKB: 850,
  jsKB: 1200,
  imageKB: 2200,
  fontKB: 500,
  loadMs: 6500,
  domContentLoadedMs: 3500,
};

const pages = [
  {
    key: "platform",
    path: "/platform/",
    ok: [200],
    budget: { ...defaultBudget, totalKB: 2400, cssKB: 950, loadMs: 6500 },
  },
  {
    key: "campaign",
    path: "/c/connect-atx-elite",
    ok: [200],
    budget: { ...defaultBudget, totalKB: 2800, cssKB: 1100, jsKB: 1400, imageKB: 2600, requests: 105, loadMs: 7000 },
  },
  {
    key: "login",
    path: "/platform/login",
    ok: [200],
    budget: { ...defaultBudget, totalKB: 1800, cssKB: 850, requests: 75, loadMs: 5500 },
  },
  {
    key: "dashboard-locked",
    path: "/platform/dashboard",
    ok: [200, 302, 401, 403],
    budget: { ...defaultBudget, totalKB: 1400, requests: 55, loadMs: 4500 },
  },
  {
    key: "onboarding",
    path: "/platform/onboarding",
    ok: [200, 302, 401, 403, 404],
    optional: true,
    budget: { ...defaultBudget, totalKB: 2200, requests: 90, loadMs: 6500 },
  },
];

if (TOKEN) {
  pages.push({
    key: "dashboard-token",
    path: `/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}`,
    shown: "/platform/dashboard?operator_token=<redacted>",
    ok: [200],
    optional: true,
    budget: { ...defaultBudget, totalKB: 2600, requests: 105, loadMs: 7000 },
  });
}

function classify(url, contentType, resourceType) {
  const u = String(url || "").split("?")[0].toLowerCase();
  const ct = String(contentType || "").toLowerCase();

  if (resourceType === "document" || ct.includes("text/html")) return "html";
  if (ct.includes("text/css") || u.endsWith(".css")) return "css";
  if (ct.includes("javascript") || u.endsWith(".js") || u.endsWith(".mjs")) return "js";
  if (ct.startsWith("image/") || /\.(png|jpe?g|webp|gif|svg|avif)$/i.test(u)) return "image";
  if (ct.includes("font") || /\.(woff2?|ttf|otf)$/i.test(u)) return "font";
  return "other";
}

function kb(bytes) {
  return Math.round((bytes / KB) * 10) / 10;
}

function redactUrl(url) {
  return String(url || "").replace(/operator_token=[^&]+/g, "operator_token=<redacted>");
}

function topByBytes(items, count = 12) {
  return [...items].sort((a, b) => b.bytes - a.bytes).slice(0, count).map((x) => ({
    url: redactUrl(x.url),
    type: x.type,
    status: x.status,
    kb: kb(x.bytes),
    contentType: x.contentType,
  }));
}

function summarize(records) {
  const totals = {
    requests: records.length,
    totalBytes: 0,
    htmlBytes: 0,
    cssBytes: 0,
    jsBytes: 0,
    imageBytes: 0,
    fontBytes: 0,
    otherBytes: 0,
  };

  for (const r of records) {
    totals.totalBytes += r.bytes;
    if (r.type === "html") totals.htmlBytes += r.bytes;
    else if (r.type === "css") totals.cssBytes += r.bytes;
    else if (r.type === "js") totals.jsBytes += r.bytes;
    else if (r.type === "image") totals.imageBytes += r.bytes;
    else if (r.type === "font") totals.fontBytes += r.bytes;
    else totals.otherBytes += r.bytes;
  }

  return {
    requests: totals.requests,
    totalKB: kb(totals.totalBytes),
    htmlKB: kb(totals.htmlBytes),
    cssKB: kb(totals.cssBytes),
    jsKB: kb(totals.jsBytes),
    imageKB: kb(totals.imageBytes),
    fontKB: kb(totals.fontBytes),
    otherKB: kb(totals.otherBytes),
  };
}

function budgetErrors(summary, timing, budget) {
  const errors = [];
  const warnings = [];

  const checks = [
    ["requests", summary.requests, budget.requests, "requests"],
    ["totalKB", summary.totalKB, budget.totalKB, "total KB"],
    ["htmlKB", summary.htmlKB, budget.htmlKB, "HTML KB"],
    ["cssKB", summary.cssKB, budget.cssKB, "CSS KB"],
    ["jsKB", summary.jsKB, budget.jsKB, "JS KB"],
    ["imageKB", summary.imageKB, budget.imageKB, "image KB"],
    ["fontKB", summary.fontKB, budget.fontKB, "font KB"],
    ["loadMs", timing.loadMs, budget.loadMs, "load ms"],
    ["domContentLoadedMs", timing.domContentLoadedMs, budget.domContentLoadedMs, "DOMContentLoaded ms"],
  ];

  for (const [key, actual, max, label] of checks) {
    if (actual > max) {
      const msg = `${label} ${actual} > ${max}`;
      if (STRICT || ["totalKB", "cssKB", "jsKB", "imageKB", "requests"].includes(key)) errors.push(msg);
      else warnings.push(msg);
    }
  }

  return { errors, warnings };
}

const browser = await chromium.launch({ headless: HEADLESS });
const errors = [];
const warnings = [];
const results = [];

try {
  for (const [vpName, viewport] of viewports) {
    const context = await browser.newContext({
      viewport,
      ignoreHTTPSErrors: true,
      bypassCSP: false,
    });

    for (const spec of pages) {
      const page = await context.newPage();
      const key = `${spec.key}-${vpName}`;
      const shown = spec.shown || spec.path;
      const records = [];
      const jobs = [];
      const consoleErrors = [];

      page.on("console", (msg) => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
      });

      page.on("response", (res) => {
        jobs.push((async () => {
          try {
            const req = res.request();
            const url = res.url();
            if (!url.startsWith(BASE) && !url.startsWith("http://127.0.0.1") && !url.startsWith("http://localhost")) return;

            const headers = res.headers();
            let bytes = Number(headers["content-length"] || 0);

            if (!bytes) {
              try {
                const body = await res.body();
                bytes = body?.length || 0;
              } catch (_) {
                bytes = 0;
              }
            }

            const contentType = headers["content-type"] || "";
            records.push({
              url,
              status: res.status(),
              method: req.method(),
              resourceType: req.resourceType(),
              contentType,
              type: classify(url, contentType, req.resourceType()),
              bytes,
            });
          } catch (_) {}
        })());
      });

      try {
        const response = await page.goto(`${BASE}${spec.path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
        await page.waitForLoadState("load", { timeout: 15000 }).catch(() => {});
        await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
        await page.waitForTimeout(250);

        await Promise.allSettled(jobs);

        const status = response?.status() || 0;
        const timing = await page.evaluate(() => {
          const nav = performance.getEntriesByType("navigation")[0];
          if (!nav) return { loadMs: 0, domContentLoadedMs: 0 };
          return {
            loadMs: Math.round(nav.loadEventEnd || nav.duration || 0),
            domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd || 0),
          };
        });

        const summary = summarize(records);
        const pageErrors = [];
        const pageWarnings = [];

        if (!spec.ok.includes(status)) pageErrors.push(`unexpected status ${status}`);

        const badResponses = records
          .filter((r) => r.status >= 400 && ![401, 403, 404].includes(r.status))
          .map((r) => `${r.status} ${redactUrl(r.url)}`)
          .slice(0, 8);

        if (badResponses.length) pageErrors.push(`bad asset responses: ${badResponses.join(" | ")}`);

        if (status === 200) {
          const budgetResult = budgetErrors(summary, timing, spec.budget);
          pageErrors.push(...budgetResult.errors);
          pageWarnings.push(...budgetResult.warnings);
        }

        if (consoleErrors.length) {
          pageWarnings.push(`console errors observed: ${consoleErrors.slice(0, 3).join(" | ")}`);
        }

        const record = {
          key,
          path: shown,
          status,
          viewport: vpName,
          timing,
          summary,
          budget: spec.budget,
          pageErrors,
          pageWarnings,
          largestResources: topByBytes(records),
          records: records.map((r) => ({ ...r, url: redactUrl(r.url), kb: kb(r.bytes) })),
        };

        fs.writeFileSync(path.join(OUT, `${key}.json`), JSON.stringify(record, null, 2));
        results.push(record);

        if (pageErrors.length && !spec.optional) {
          errors.push(`${key}: ${pageErrors.join("; ")}`);
          console.log(`❌ ${key}`);
        } else {
          if (pageErrors.length) warnings.push(`${key}: optional issue: ${pageErrors.join("; ")}`);
          for (const w of pageWarnings) warnings.push(`${key}: ${w}`);
          console.log(`✅ ${key} total=${summary.totalKB}KB css=${summary.cssKB}KB js=${summary.jsKB}KB img=${summary.imageKB}KB req=${summary.requests}`);
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
  strict: STRICT,
  errors,
  warnings,
  results: results.map((r) => ({
    key: r.key,
    path: r.path,
    status: r.status,
    timing: r.timing,
    summary: r.summary,
    budget: r.budget,
    pageErrors: r.pageErrors,
    pageWarnings: r.pageWarnings,
    largestResources: r.largestResources,
  })),
};

fs.writeFileSync(path.join(OUT, "latest.json"), JSON.stringify(report, null, 2));

const lines = [
  "# FutureFunded Performance Budget Gate",
  "",
  `**Status:** ${report.ok ? "PASS ✅" : "FAIL ❌"}`,
  `**Checked:** ${report.checkedAt}`,
  "",
  "## Summary",
  "",
  `- Pages checked: ${results.length}`,
  `- Errors: ${errors.length}`,
  `- Warnings: ${warnings.length}`,
  `- Strict: ${STRICT}`,
  "",
  "## Errors",
  "",
  ...(errors.length ? errors.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Warnings",
  "",
  ...(warnings.length ? warnings.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Page Budgets",
  "",
];

for (const r of results) {
  lines.push(
    `- **${r.key}** — ${r.path} — total ${r.summary.totalKB}KB / css ${r.summary.cssKB}KB / js ${r.summary.jsKB}KB / img ${r.summary.imageKB}KB / req ${r.summary.requests} / load ${r.timing.loadMs}ms`
  );
}

fs.writeFileSync(path.join(OUT, "latest.md"), `${lines.join("\n")}\n`);
console.log("\n" + fs.readFileSync(path.join(OUT, "latest.md"), "utf8"));
console.log(`Report: ${path.join(OUT, "latest.json")}`);

if (!report.ok) process.exit(1);
