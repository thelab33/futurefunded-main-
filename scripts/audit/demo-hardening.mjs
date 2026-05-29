#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";

const BASE_URL = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const CAMPAIGN_PATH = process.env.FF_CAMPAIGN_PATH || "/c/connect-atx-elite";
const PLATFORM_PATH = process.env.FF_PLATFORM_PATH || "/platform/";
const SESSION_ID = process.env.FF_SESSION_ID || "";

const OUT_DIR = path.resolve("docs/audits/demo-hardening");
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

async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  try {
    return { res, json: JSON.parse(text), text };
  } catch {
    return { res, json: null, text };
  }
}

function includesAll(text, needles) {
  return needles.filter((needle) => !text.includes(needle));
}

console.log("\n🚀 FutureFunded demo hardening audit");
console.log(`Base URL: ${BASE_URL}\n`);

const campaignUrl = `${BASE_URL}${CAMPAIGN_PATH}?css_v=demo-hardening`;
const platformUrl = `${BASE_URL}${PLATFORM_PATH}?css_v=demo-hardening`;
const paymentReturnUrl = `${BASE_URL}${CAMPAIGN_PATH}?payment=success&session_id=cs_test_demo_hardening&css_v=demo-hardening`;

try {
  const { res, text } = await fetchText(campaignUrl);
  if (res.status === 200) pass("Campaign page returns 200", campaignUrl);
  else fail("Campaign page returns 200", `status=${res.status}`);

  const missing = includesAll(text, [
    "css/ff.css",
    "css/ff.checkout.css",
    "js/ff-campaign.js",
    "js/ff-embedded-checkout.js",
    "data-ff-embedded-checkout-shell",
    "data-ff-open-checkout",
    "data-ff-donate-cta",
    "data-ff-mobile-conversion-rail",
    "data-ff-sponsor-contract",
  ]);

  if (!missing.length) pass("Campaign template contract is intact");
  else fail("Campaign template contract is missing hooks", missing.join(", "));
} catch (err) {
  fail("Campaign page request failed", err.message);
}

try {
  const { res, text } = await fetchText(platformUrl);
  if (res.status === 200) pass("Homepage/platform page returns 200", platformUrl);
  else fail("Homepage/platform page returns 200", `status=${res.status}`);

  const missing = includesAll(text, [
    "css/ff.css",
    "data-ff-page=\"platform-home\"",
    "data-ff-home-root",
    "data-ff-home-primary-cta",
    "data-ff-home-demo-cta",
  ]);

  if (!missing.length) pass("Homepage template contract is intact");
  else fail("Homepage template contract is missing hooks", missing.join(", "));

  if (!text.includes("css/ff.checkout.css")) pass("Homepage does not load checkout CSS");
  else warn("Homepage loads checkout CSS", "expected only ff.css on platform home");
} catch (err) {
  fail("Homepage request failed", err.message);
}

try {
  const { res, text } = await fetchText(paymentReturnUrl);
  if (res.status === 200 && text.includes("ff-paymentReturn")) {
    pass("Payment success banner renders");
  } else {
    fail("Payment success banner renders", `status=${res.status}`);
  }
} catch (err) {
  fail("Payment return request failed", err.message);
}

try {
  const ledgerUrl = `${BASE_URL}${CAMPAIGN_PATH}/ledger/summary`;
  const { res, json } = await fetchJson(ledgerUrl);

  if (res.status === 200 && json?.totals) {
    pass(
      "Ledger summary responds",
      `raised=${json.totals.raised_amount_cents} cents, donations=${json.totals.donation_count}`
    );
  } else {
    fail("Ledger summary responds", `status=${res.status}`);
  }
} catch (err) {
  fail("Ledger summary request failed", err.message);
}

if (SESSION_ID) {
  try {
    const statusUrl = `${BASE_URL}${CAMPAIGN_PATH}/checkout/session-status?session_id=${encodeURIComponent(SESSION_ID)}`;
    const { res, json } = await fetchJson(statusUrl);

    if (res.status === 200 && json?.ok && json?.verified) {
      pass("Stripe session status verifies", `${json.amount_display || ""} ${json.payment_status || ""}`.trim());
    } else {
      fail("Stripe session status verifies", `status=${res.status}`);
    }
  } catch (err) {
    fail("Stripe session status request failed", err.message);
  }
} else {
  warn("Stripe session status skipped", "set FF_SESSION_ID=cs_test_... to verify a known session");
}

let playwrightAvailable = true;
let chromium;

try {
  ({ chromium } = await import("playwright"));
} catch {
  playwrightAvailable = false;
}

if (!playwrightAvailable) {
  warn("Browser/mobile audit skipped", "Playwright is not available in this environment");
} else {
  const browser = await chromium.launch();
  const viewports = [
    { name: "desktop", width: 1440, height: 1200 },
    { name: "mobile", width: 390, height: 1100 },
  ];

  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });

    for (const target of [
      { name: "campaign", url: campaignUrl, hero: ".ff-campaignHero" },
      { name: "homepage", url: platformUrl, hero: ".ff-platformBlueprintHero" },
    ]) {
      try {
        await page.goto(target.url, { waitUntil: "networkidle", timeout: 30000 });
        await page.screenshot({
          path: path.join(OUT_DIR, `${target.name}-${viewport.name}.png`),
          fullPage: true,
        });

        const headerBox = await page.locator("[data-ff-header]").first().boundingBox();
        const heroBox = await page.locator(target.hero).first().boundingBox();

        if (headerBox && heroBox) {
          const gap = Math.round(heroBox.y - (headerBox.y + headerBox.height));
          if (gap <= 22) pass(`${target.name} ${viewport.name} nav-to-hero rhythm`, `gap=${gap}px`);
          else warn(`${target.name} ${viewport.name} nav-to-hero rhythm`, `gap=${gap}px`);
        } else {
          fail(`${target.name} ${viewport.name} nav-to-hero rhythm`, "missing header or hero box");
        }
      } catch (err) {
        fail(`${target.name} ${viewport.name} screenshot/rhythm audit failed`, err.message);
      }
    }

    await page.close();
  }

  const page = await browser.newPage({ viewport: { width: 390, height: 1000 } });

  try {
    await page.goto(campaignUrl, { waitUntil: "networkidle", timeout: 30000 });

    const donate = page.locator("[data-ff-open-checkout]").first();
    await donate.click({ timeout: 10000 });

    const shell = page.locator("[data-ff-embedded-checkout-shell]").first();
    await page.waitForTimeout(900);

    const isVisible = await shell.evaluate((node) => {
      const styles = window.getComputedStyle(node);
      return !node.hidden && node.getAttribute("aria-hidden") !== "true" && styles.display !== "none";
    });

    if (isVisible) pass("Mobile donate CTA opens embedded checkout shell");
    else fail("Mobile donate CTA opens embedded checkout shell", "shell remained hidden");

    await page.screenshot({
      path: path.join(OUT_DIR, "campaign-mobile-checkout-modal.png"),
      fullPage: true,
    });
  } catch (err) {
    fail("Mobile checkout modal audit failed", err.message);
  }

  await page.close();
  await browser.close();

  pass("Screenshots saved", OUT_DIR);
}

const failed = results.filter((r) => r.ok === false);
const warnings = results.filter((r) => r.ok === "warn");

await fs.writeFile(
  path.join(OUT_DIR, "demo-hardening-results.json"),
  JSON.stringify({ baseUrl: BASE_URL, results }, null, 2)
);

console.log("\n==============================");
console.log("FutureFunded demo hardening result");
console.log("==============================");
console.log(`Passed:   ${results.filter((r) => r.ok === true).length}`);
console.log(`Warnings: ${warnings.length}`);
console.log(`Failed:   ${failed.length}`);
console.log(`Output:   ${OUT_DIR}`);

if (failed.length) {
  console.log("\nFailed checks:");
  for (const item of failed) console.log(`- ${item.name}: ${item.detail}`);
  process.exit(1);
}

console.log("\n🎉 Demo hardening checks passed enough to proceed.");
