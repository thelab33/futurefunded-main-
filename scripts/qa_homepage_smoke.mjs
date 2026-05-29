#!/usr/bin/env node

import { chromium } from "playwright";

const baseUrl =
  process.env.FF_HOME_QA_URL ||
  process.argv.find((arg) => /^https?:\/\//.test(arg)) ||
  "http://127.0.0.1:5000/platform/";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 960 } });

const failures = [];
const passes = [];
const consoleErrors = [];

function pass(name, detail = "") {
  passes.push({ name, detail });
  console.log(`OK ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, detail = "") {
  failures.push({ name, detail });
  console.log(`FAIL ${name}${detail ? ` - ${detail}` : ""}`);
}

page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});

page.on("pageerror", (err) => {
  consoleErrors.push(err.message);
});

async function expectVisible(name, selector) {
  const loc = page.locator(selector).first();
  if ((await loc.count()) > 0 && (await loc.isVisible().catch(() => false))) {
    pass(name);
  } else {
    fail(name, `missing visible ${selector}`);
  }
}

try {
  const response = await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  const status = response?.status() || 0;

  if (status >= 200 && status < 400) pass("homepage reachable", `${status} ${baseUrl}`);
  else fail("homepage reachable", `HTTP ${status}`);

  await expectVisible("homepage root", "[data-ff-home-root]");
  await expectVisible("hero CTA", "[data-ff-home-launch-cta]");
  await expectVisible("campaign demo CTA", "[data-ff-home-demo-cta]");
  await expectVisible("platform console", "[data-ff-home-console]");
  await expectVisible("campaign preview", "[data-ff-home-campaign-preview]");

  const cssLinked = await page.locator('link[href*="ff.homepage-flagship.css"]').count();
  if (cssLinked > 0) pass("homepage flagship CSS linked");
  else fail("homepage flagship CSS linked", "missing ff.homepage-flagship.css");

  const href = await page.locator("[data-ff-home-demo-cta]").first().getAttribute("href");
  if (href?.includes("/c/connect-atx-elite")) pass("demo CTA routes to campaign", href);
  else fail("demo CTA routes to campaign", `bad href=${href}`);

  const body = (await page.locator("body").innerText()).toLowerCase();
  for (const phrase of [
    "secure checkout",
    "webhook",
    "ledger",
    "sponsor",
    "mobile-first",
    "institutionally credible",
  ]) {
    if (body.includes(phrase)) pass(`homepage mentions ${phrase}`);
    else fail(`homepage mentions ${phrase}`, "missing product proof copy");
  }

  const inlineStyles = await page.locator("[style]").count();
  if (inlineStyles === 0) pass("homepage CSP-safe markup", "no inline style attributes");
  else fail("homepage CSP-safe markup", `${inlineStyles} inline style attributes`);

  if (consoleErrors.length) fail("no console errors", consoleErrors.slice(0, 5).join(" | "));
  else pass("no console errors");
} catch (error) {
  fail("homepage smoke runtime", error?.message || String(error));
} finally {
  await browser.close();
}

console.log("");
console.log("=== HOMEPAGE QA SUMMARY ===");
console.log(`Passed: ${passes.length}`);
console.log(`Failed: ${failures.length}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const item of failures) console.log(`- ${item.name}: ${item.detail}`);
  process.exitCode = 1;
}
