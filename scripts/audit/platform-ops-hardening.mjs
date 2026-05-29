#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";

const BASE_URL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.FF_OPERATOR_TOKEN || "";
const OUT_DIR = path.resolve("docs/audits/platform-ops");
await fs.mkdir(OUT_DIR, { recursive: true });

const results = [];

function pass(name, detail = "") {
  results.push({ ok: true, name, detail });
  console.log(`✅ ${name}${detail ? ` — ${detail}` : ""}`);
}

function fail(name, detail = "") {
  results.push({ ok: false, name, detail });
  console.log(`❌ ${name}${detail ? ` — ${detail}` : ""}`);
}

function warn(name, detail = "") {
  results.push({ ok: "warn", name, detail });
  console.log(`⚠️  ${name}${detail ? ` — ${detail}` : ""}`);
}

async function fetchText(url) {
  const res = await fetch(url, { redirect: "manual" });
  const text = await res.text();
  return { res, text };
}

function cssLinks(html) {
  return [...html.matchAll(/css\/[^"'<>]+\.css[^"'<>]*/g)].map((m) => m[0]).sort();
}

console.log("\n🚀 FutureFunded platform ops hardening audit");
console.log(`Base URL: ${BASE_URL}\n`);

const onboardingUrl = `${BASE_URL}/platform/onboarding?css_v=ops-single-css-audit`;
const dashboardUrl = TOKEN
  ? `${BASE_URL}/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}&css_v=ops-single-css-audit`
  : `${BASE_URL}/platform/dashboard?css_v=ops-single-css-audit`;

try {
  const { res, text } = await fetchText(onboardingUrl);

  if (res.status === 200) pass("Onboarding returns 200", onboardingUrl);
  else fail("Onboarding returns 200", `status=${res.status}`);

  const links = cssLinks(text);
  if (links.some((x) => x.includes("ff.css"))) pass("Onboarding loads ff.css", links.join(", "));
  else fail("Onboarding loads ff.css", links.join(", "));

  if (!links.some((x) => x.includes("ff.operator-dashboard.css"))) {
    pass("Onboarding does not load deprecated operator CSS");
  } else {
    fail("Onboarding still loads deprecated operator CSS", links.join(", "));
  }

  const requiredHooks = [
    "data-ff-onboard-root",
    "data-ff-onboard-form",
    "data-ff-onboard-score",
    "data-ff-team-photo-upload",
  ];

  const missing = requiredHooks.filter((hook) => !text.includes(hook));
  if (!missing.length) pass("Onboarding hooks are intact");
  else fail("Onboarding hooks missing", missing.join(", "));
} catch (error) {
  fail("Onboarding request failed", error.message);
}

try {
  const { res, text } = await fetchText(dashboardUrl);

  if (TOKEN) {
    if (res.status === 200) pass("Dashboard returns 200 with operator token", dashboardUrl);
    else fail("Dashboard returns 200 with operator token", `status=${res.status}`);
  } else {
    if (res.status === 403 || res.status === 302) {
      warn("Dashboard protected as expected", `status=${res.status}; set FF_OPERATOR_TOKEN or FF_OPERATOR_ACCESS_TOKEN for full audit`);
    } else {
      fail("Dashboard protection unexpected", `status=${res.status}`);
    }
  }

  if (res.status === 200) {
    const links = cssLinks(text);

    if (links.some((x) => x.includes("ff.css"))) pass("Dashboard loads ff.css", links.join(", "));
    else fail("Dashboard loads ff.css", links.join(", "));

    if (!links.some((x) => x.includes("ff.operator-dashboard.css"))) {
      pass("Dashboard does not load deprecated operator CSS");
    } else {
      fail("Dashboard still loads deprecated operator CSS", links.join(", "));
    }

    const requiredHooks = [
      "data-ff-operator-root",
      "data-ff-ledger-url",
      "data-ff-donations-table",
      "data-ff-sponsors-list",
      "data-ff-offline-donation-form",
      "data-ff-refresh-ledger",
    ];

    const missing = requiredHooks.filter((hook) => !text.includes(hook));
    if (!missing.length) pass("Dashboard hooks are intact");
    else fail("Dashboard hooks missing", missing.join(", "));
  }
} catch (error) {
  fail("Dashboard request failed", error.message);
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  chromium = null;
}

if (!chromium) {
  warn("Screenshot audit skipped", "Playwright unavailable");
} else {
  const browser = await chromium.launch();

  for (const viewport of [
    { name: "desktop", width: 1440, height: 1200 },
    { name: "mobile", width: 390, height: 1100 },
  ]) {
    const page = await browser.newPage({ viewport });

    try {
      await page.goto(onboardingUrl, { waitUntil: "networkidle", timeout: 30000 });
      await page.screenshot({
        path: path.join(OUT_DIR, `onboarding-${viewport.name}.png`),
        fullPage: true,
      });

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow <= 2) pass(`Onboarding ${viewport.name} has no horizontal overflow`, `overflow=${overflow}px`);
      else fail(`Onboarding ${viewport.name} horizontal overflow`, `overflow=${overflow}px`);
    } catch (error) {
      fail(`Onboarding ${viewport.name} screenshot failed`, error.message);
    }

    if (TOKEN) {
      try {
        await page.goto(dashboardUrl, { waitUntil: "networkidle", timeout: 30000 });
        await page.screenshot({
          path: path.join(OUT_DIR, `dashboard-${viewport.name}.png`),
          fullPage: true,
        });

        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (overflow <= 2) pass(`Dashboard ${viewport.name} has no horizontal overflow`, `overflow=${overflow}px`);
        else fail(`Dashboard ${viewport.name} horizontal overflow`, `overflow=${overflow}px`);
      } catch (error) {
        fail(`Dashboard ${viewport.name} screenshot failed`, error.message);
      }
    }

    await page.close();
  }

  await browser.close();
  pass("Platform ops screenshots saved", OUT_DIR);
}

await fs.writeFile(
  path.join(OUT_DIR, "platform-ops-hardening-results.json"),
  JSON.stringify({ baseUrl: BASE_URL, results }, null, 2)
);

const failed = results.filter((r) => r.ok === false);
const warnings = results.filter((r) => r.ok === "warn");

console.log("\n==============================");
console.log("FutureFunded platform ops result");
console.log("==============================");
console.log(`Passed:   ${results.filter((r) => r.ok === true).length}`);
console.log(`Warnings: ${warnings.length}`);
console.log(`Failed:   ${failed.length}`);
console.log(`Output:   ${OUT_DIR}`);

if (failed.length) process.exit(1);

console.log("\n🎉 Platform ops hardening passed.");
