#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "audit_outputs", "accessibility");
fs.mkdirSync(OUT, { recursive: true });

const BASE = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";
const HEADLESS = process.env.PW_HEADLESS !== "0";

const pages = [
  { key: "platform", path: "/platform/", ok: [200], requireH1: true },
  { key: "campaign", path: "/c/connect-atx-elite", ok: [200], requireH1: true },
  { key: "login", path: "/platform/login", ok: [200], requireH1: true },
  { key: "dashboard-locked", path: "/platform/dashboard", ok: [200, 302, 401, 403], requireH1: false },
  { key: "onboarding", path: "/platform/onboarding", ok: [200, 302, 401, 403, 404], requireH1: false, optional: true },
];

if (TOKEN) {
  pages.push({
    key: "dashboard-token",
    path: `/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}`,
    shown: "/platform/dashboard?operator_token=<redacted>",
    ok: [200],
    requireH1: true,
    optional: true,
  });
}

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

function uniq(items) {
  return [...new Set(items.filter(Boolean))];
}

async function inspectA11y(page, spec) {
  return page.evaluate((spec) => {
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
    };

    const text = (el) => (el?.textContent || "").replace(/\s+/g, " ").trim();
    const nameOf = (el) =>
      (
        el.getAttribute("aria-label") ||
        el.getAttribute("title") ||
        text(el) ||
        el.getAttribute("alt") ||
        ""
      ).trim();

    const byId = (id) => (id ? document.getElementById(id) : null);

    const inputName = (el) => {
      const id = el.getAttribute("id");
      const ariaLabel = el.getAttribute("aria-label");
      const labelledby = el.getAttribute("aria-labelledby");
      const labelById = labelledby
        ? labelledby.split(/\s+/).map((x) => text(byId(x))).join(" ").trim()
        : "";
      const explicit = id ? text(document.querySelector(`label[for="${CSS.escape(id)}"]`)) : "";
      const implicit = text(el.closest("label"));
      const placeholder = el.getAttribute("placeholder") || "";
      return (ariaLabel || labelById || explicit || implicit || placeholder || "").trim();
    };

    const badButtons = [...document.querySelectorAll("button, [role='button']")]
      .filter(visible)
      .filter((el) => !nameOf(el))
      .map((el) => el.outerHTML.slice(0, 260));

    const badLinks = [...document.querySelectorAll("a[href]")]
      .filter(visible)
      .filter((el) => !nameOf(el))
      .map((el) => el.outerHTML.slice(0, 260));

    const badInputs = [...document.querySelectorAll("input, select, textarea")]
      .filter(visible)
      .filter((el) => {
        const type = (el.getAttribute("type") || "").toLowerCase();
        return !["hidden", "submit", "button", "reset"].includes(type);
      })
      .filter((el) => !inputName(el))
      .map((el) => el.outerHTML.slice(0, 260));

    const badImages = [...document.images]
      .filter(visible)
      .filter((img) => !img.hasAttribute("alt"))
      .map((img) => img.outerHTML.slice(0, 260));

    const badAriaControls = [...document.querySelectorAll("[aria-controls]")]
      .filter(visible)
      .filter((el) => !document.getElementById(el.getAttribute("aria-controls")))
      .map((el) => el.outerHTML.slice(0, 260));

    const badDialogs = [...document.querySelectorAll("[role='dialog'], [aria-modal='true']")]
      .filter((el) => !el.hidden && el.getAttribute("aria-hidden") !== "true")
      .filter((el) => {
        const hasName =
          el.getAttribute("aria-label") ||
          el.getAttribute("aria-labelledby") ||
          el.querySelector("h1,h2,h3");
        return !hasName;
      })
      .map((el) => el.outerHTML.slice(0, 260));

    const focusables = [...document.querySelectorAll(
      "a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex='-1'])"
    )].filter(visible);

    return {
      title: document.title || "",
      lang: document.documentElement.lang || "",
      hasViewport: Boolean(document.querySelector("meta[name='viewport']")),
      h1Count: document.querySelectorAll("h1").length,
      visibleHeadingCount: [...document.querySelectorAll("h1,h2,h3")].filter(visible).length,
      focusableCount: focusables.length,
      badButtons,
      badLinks,
      badInputs,
      badImages,
      badAriaControls,
      badDialogs,
      bodyTextLength: (document.body?.innerText || "").trim().length,
    };
  }, spec);
}

const browser = await chromium.launch({ headless: HEADLESS });
const errors = [];
const warnings = [];
const results = [];

try {
  for (const [vpName, viewport] of viewports) {
    const context = await browser.newContext({ viewport, ignoreHTTPSErrors: true });
    const page = await context.newPage();

    for (const spec of pages) {
      const key = `${spec.key}-${vpName}`;
      const shown = spec.shown || spec.path;
      const pageErrors = [];
      const pageWarnings = [];

      try {
        const res = await page.goto(`${BASE}${spec.path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
        await page.waitForLoadState("load", { timeout: 12000 }).catch(() => {});
        await page.waitForTimeout(350);

        const status = res?.status() || 0;
        const diag = await inspectA11y(page, spec);

        if (!spec.ok.includes(status)) pageErrors.push(`unexpected status ${status}`);

        if (status === 200) {
          if (!diag.title.trim()) pageErrors.push("missing document title");
          if (!diag.lang.trim()) pageErrors.push("missing html lang");
          if (!diag.hasViewport) pageErrors.push("missing viewport meta");
          if (spec.requireH1 && diag.h1Count < 1) pageErrors.push("missing h1");
          if (diag.visibleHeadingCount < 1) pageErrors.push("no visible headings");
          if (diag.focusableCount < 1) pageErrors.push("no visible focusable controls");

          if (diag.badButtons.length) pageErrors.push(`${diag.badButtons.length} unnamed buttons`);
          if (diag.badLinks.length) pageErrors.push(`${diag.badLinks.length} unnamed links`);
          if (diag.badInputs.length) pageErrors.push(`${diag.badInputs.length} unlabeled inputs`);
          if (diag.badImages.length) pageErrors.push(`${diag.badImages.length} images missing alt attribute`);
          if (diag.badAriaControls.length) pageErrors.push(`${diag.badAriaControls.length} aria-controls targets missing`);
          if (diag.badDialogs.length) pageErrors.push(`${diag.badDialogs.length} unnamed visible dialogs`);

          if (diag.bodyTextLength < 80) pageWarnings.push("very sparse body text");
        }

        const record = { key, path: shown, status, pageErrors, pageWarnings, ...diag };
        fs.writeFileSync(path.join(OUT, `${key}.json`), JSON.stringify(record, null, 2));
        results.push(record);

        if (pageErrors.length && !spec.optional) {
          errors.push(`${key}: ${pageErrors.join("; ")}`);
          console.log(`❌ ${key}`);
        } else {
          if (pageErrors.length) warnings.push(`${key}: optional issue: ${pageErrors.join("; ")}`);
          for (const w of pageWarnings) warnings.push(`${key}: ${w}`);
          console.log(`✅ ${key}`);
        }
      } catch (err) {
        const msg = `${key}: ${err?.message || err}`;
        if (spec.optional) warnings.push(msg);
        else errors.push(msg);
        console.log(`❌ ${msg}`);
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
  errors: uniq(errors),
  warnings: uniq(warnings),
  results,
};

fs.writeFileSync(path.join(OUT, "latest.json"), JSON.stringify(report, null, 2));

const md = [
  "# FutureFunded Accessibility Gate",
  "",
  `**Status:** ${report.ok ? "PASS ✅" : "FAIL ❌"}`,
  `**Checked:** ${report.checkedAt}`,
  "",
  "## Summary",
  "",
  `- Pages checked: ${results.length}`,
  `- Errors: ${report.errors.length}`,
  `- Warnings: ${report.warnings.length}`,
  "",
  "## Errors",
  "",
  ...(report.errors.length ? report.errors.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Warnings",
  "",
  ...(report.warnings.length ? report.warnings.map((x) => `- ${x}`) : ["- None"]),
  "",
  "## Pages",
  "",
  ...results.map((r) => `- **${r.key}** — ${r.path} — status ${r.status}`),
  "",
].join("\n");

fs.writeFileSync(path.join(OUT, "latest.md"), md);
console.log("\n" + md);
console.log(`Report: ${path.join(OUT, "latest.json")}`);

if (!report.ok) process.exit(1);
