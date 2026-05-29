#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const out = path.join(root, "audit_outputs/page-beauty");
fs.mkdirSync(out, { recursive: true });

const base = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";
const headless = process.env.PW_HEADLESS !== "0";

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

const pages = [
  { key: "platform", path: "/platform/", ok: [200], must: ["FutureFunded"], cta: ["start", "view", "fundraiser", "campaign"] },
  { key: "campaign", path: "/c/connect-atx-elite", ok: [200], must: ["Connect ATX", "Sponsor"], cta: ["give", "donate", "sponsor", "share"], selectors: ["[data-ff-open-checkout], [data-ff-donate-trigger]", "[data-ff-open-sponsor], [data-ff-sponsor-trigger]", "[data-ff-share], [data-ff-share-trigger]"] },
  { key: "login", path: "/platform/login", ok: [200], must: ["Access", "Sign"], cta: ["sign"], selectors: ["input[type='email'], input[name='email']", "input[type='password'], input[name='password']"] },
  { key: "dashboard-locked", path: "/platform/dashboard", ok: [200,302,401,403], must: ["dashboard", "access", "operator", "login", "forbidden"], cta: [] },
  { key: "onboarding", path: "/platform/onboarding", ok: [200,302,401,403,404], must: ["FutureFunded", "campaign", "Launch", "onboarding"], cta: ["start", "continue", "launch"], optional: true },
];

if (token) {
  pages.push({
    key: "dashboard-token",
    path: `/platform/dashboard?operator_token=${encodeURIComponent(token)}`,
    shown: "/platform/dashboard?operator_token=<redacted>",
    ok: [200],
    must: ["dashboard", "operator", "ledger", "sponsor"],
    cta: ["export", "refresh", "donation", "sponsor"],
    optional: true,
  });
}

const badCopy = [/lorem ipsum/i, /todo:/i, /fixme/i, /\{\{.*\}\}/, /\{%.*%\}/, /undefined/i];


async function hydrateImages(page) {
  await page.evaluate(() => {
    for (const img of document.images) {
      img.loading = "eager";
      img.decoding = "sync";
    }
  });

  const count = await page.locator("img").count();
  for (let i = 0; i < count; i += 1) {
    await page.locator("img").nth(i).scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(60);
  }

  await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(300);
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function diag(page, selectors = []) {
  return page.evaluate((selectors) => {
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
    };

    const html = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(html.scrollWidth, body?.scrollWidth || 0);
    const viewportWidth = window.innerWidth;

    const headings = [...document.querySelectorAll("h1,h2,h3")]
      .filter(visible)
      .map((x) => x.textContent.trim().replace(/\s+/g, " ").slice(0, 140));

    const actions = [...document.querySelectorAll("a,button")]
      .filter(visible)
      .map((x) => {
        const r = x.getBoundingClientRect();
        return {
          text: x.textContent.trim().replace(/\s+/g, " ").slice(0, 80),
          width: Math.round(r.width),
          height: Math.round(r.height),
        };
      });

    const brokenImages = [...document.images]
      .filter(visible)
      .filter((img) => !img.complete || img.naturalWidth <= 0)
      .length;

    return {
      title: document.title,
      bodyText: document.body?.innerText || "",
      headings,
      actions,
      scrollWidth,
      viewportWidth,
      overflow: scrollWidth > viewportWidth + 2,
      brokenImages,
      selectorCounts: Object.fromEntries(selectors.map((s) => [s, document.querySelectorAll(s).length])),
      smallTargets: actions.filter((a) => a.width < 40 || a.height < 36).length,
    };
  }, selectors);
}

const browser = await chromium.launch({ headless });
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
      const shot = path.join(out, `${key}.png`);
      const json = path.join(out, `${key}.json`);
      const pageErrors = [];

      try {
        const res = await page.goto(`${base}${spec.path}`, { waitUntil: "domcontentloaded", timeout: 30000 });
        await page.waitForLoadState("load", { timeout: 12000 }).catch(() => {});
        await page.waitForTimeout(350);

        await hydrateImages(page);

        const status = res?.status() || 0;
        const html = await page.content();
        const d = await diag(page, spec.selectors || []);

        await page.screenshot({ path: shot, fullPage: true, animations: "disabled" });

        if (!spec.ok.includes(status)) pageErrors.push(`status ${status}`);
        if (d.overflow) pageErrors.push(`horizontal overflow ${d.scrollWidth}/${d.viewportWidth}`);

        if (status === 200) {
          const hay = `${html} ${d.bodyText}`.toLowerCase();
          if (spec.must?.length && !spec.must.some((x) => hay.includes(x.toLowerCase()))) pageErrors.push(`missing text: ${spec.must.join("/")}`);
          if (spec.cta?.length && !spec.cta.some((x) => d.actions.map(a => a.text).join(" ").toLowerCase().includes(x))) pageErrors.push(`missing CTA: ${spec.cta.join("/")}`);
          if (!d.headings.length) pageErrors.push("no visible headings");
          if (d.brokenImages) pageErrors.push(`${d.brokenImages} broken images`);
          for (const [sel, count] of Object.entries(d.selectorCounts)) if (!count) pageErrors.push(`missing selector ${sel}`);
          const bad = badCopy.filter((rx) => rx.test(html) || rx.test(d.bodyText)).map(String);
          if (bad.length) pageErrors.push(`bad/template copy ${bad.join(", ")}`);
          if (vpName === "mobile" && d.smallTargets) warnings.push(`${key}: ${d.smallTargets} small tap targets`);
        }

        const record = { key, path: shown, status, screenshot: shot, diagnostics: json, pageErrors, ...d };
        fs.writeFileSync(json, JSON.stringify(record, null, 2));
        results.push(record);

        if (pageErrors.length && !spec.optional) {
          errors.push(`${key}: ${pageErrors.join("; ")}`);
          console.log(`❌ ${key}`);
        } else {
          if (pageErrors.length) warnings.push(`${key}: optional issue: ${pageErrors.join("; ")}`);
          console.log(`✅ ${key}`);
        }
      } catch (e) {
        const msg = `${key}: ${e?.message || e}`;
        if (spec.optional) warnings.push(msg); else errors.push(msg);
        console.log(`❌ ${msg}`);
      }
    }

    await context.close();
  }
} finally {
  await browser.close();
}

const report = { ok: errors.length === 0, checkedAt: new Date().toISOString(), baseUrl: base, errors, warnings, results };
fs.writeFileSync(path.join(out, "latest.json"), JSON.stringify(report, null, 2));

const md = [
  "# FutureFunded Page Beauty Gate",
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
  "## Screenshots",
  "",
  ...results.map((r) => `- **${r.key}** — ${r.path} — \`${r.screenshot}\``),
  "",
].join("\n");

fs.writeFileSync(path.join(out, "latest.md"), md);
console.log("\n" + md);
console.log(`Report: ${path.join(out, "latest.json")}`);

if (!report.ok) process.exit(1);
