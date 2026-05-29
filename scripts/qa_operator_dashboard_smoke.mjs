#!/usr/bin/env node

import { chromium } from "playwright";

const rawBaseUrl =
  process.env.FF_OPERATOR_QA_URL ||
  process.argv.find((arg) => /^https?:\/\//.test(arg)) ||
  "http://127.0.0.1:5000/platform/dashboard";

const operatorToken =
  process.env.FF_QA_OPERATOR_TOKEN || process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const loginEmail = process.env.FF_QA_OPERATOR_EMAIL || "";
const loginPassword = process.env.FF_QA_OPERATOR_PASSWORD || "";

function withOperatorToken(rawUrl) {
  if (!operatorToken) return rawUrl;

  const url = new URL(rawUrl);
  if (!url.searchParams.has("operator_token")) {
    url.searchParams.set("operator_token", operatorToken);
  }
  return url.toString();
}

const baseUrl = withOperatorToken(rawBaseUrl);
const origin = new URL(baseUrl).origin;
const operatorHeaders = operatorToken ? { "X-FF-Operator-Token": operatorToken } : {};

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

async function loginIfNeeded() {
  if (operatorToken) return;

  if (!loginEmail || !loginPassword) {
    fail(
      "operator login credentials",
      "FF_QA_OPERATOR_EMAIL/PASSWORD not set and no operator token provided"
    );
    return;
  }

  const loginUrl = `${origin}/platform/login`;
  const response = await page.goto(loginUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  const status = response?.status() || 0;

  if (status >= 200 && status < 400) pass("operator login page reachable", `${status} ${loginUrl}`);
  else {
    fail("operator login page reachable", `HTTP ${status}`);
    return;
  }

  await page.locator("[data-ff-login-email]").fill(loginEmail);
  await page.locator("[data-ff-login-password]").fill(loginPassword);

  await Promise.all([
    page.waitForURL(/\/platform\/dashboard/, { timeout: 30000 }),
    page.locator("[data-ff-login-submit]").click(),
  ]);

  pass("operator browser login");
}

try {
  await loginIfNeeded();

  const response = await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  const status = response?.status() || 0;

  if (status >= 200 && status < 400) pass("operator dashboard reachable", `${status} ${baseUrl}`);
  else fail("operator dashboard reachable", `HTTP ${status}`);

  await expectVisible("operator root", "[data-ff-operator-root]");
  await expectVisible("raised metric", "[data-ff-op-raised]");
  await expectVisible("donations table", "[data-ff-donations-table]");
  await expectVisible("sponsors list", "[data-ff-sponsors-list]");
  await expectVisible("offline donation form", "[data-ff-offline-donation-form]");
  await expectVisible("events list", "[data-ff-events-list]");
  await expectVisible("export csv link", "[data-ff-export-csv]");

  const cssLinked = await page.locator('link[href*="ff.operator-dashboard.css"]').count();
  if (cssLinked > 0) pass("operator CSS linked");
  else fail("operator CSS linked", "missing ff.operator-dashboard.css");

  const summary = await page.request.get(`${origin}/c/connect-atx-elite/ledger/summary`);
  if (summary.ok()) pass("operator ledger summary reachable");
  else fail("operator ledger summary reachable", `HTTP ${summary.status()}`);

  const events = await page.request.get(`${origin}/c/connect-atx-elite/ledger/events`, {
    headers: operatorHeaders,
  });
  if (events.ok()) pass("operator ledger events reachable");
  else fail("operator ledger events reachable", `HTTP ${events.status()}`);

  const csv = await page.request.get(`${origin}/c/connect-atx-elite/ledger/export.csv`, {
    headers: operatorHeaders,
  });
  if (csv.ok()) {
    const text = await csv.text();
    if (text.includes("record_type") && text.includes("amount_cents")) {
      pass("operator CSV export returns header");
    } else {
      fail("operator CSV export returns header", "missing expected columns");
    }
  } else {
    fail("operator CSV export reachable", `HTTP ${csv.status()}`);
  }

  const inlineStyles = await page.locator("[style]").count();
  if (inlineStyles === 0) pass("operator CSP-safe markup", "no inline style attributes");
  else fail("operator CSP-safe markup", `${inlineStyles} inline style attributes`);

  if (consoleErrors.length) fail("no console errors", consoleErrors.slice(0, 5).join(" | "));
  else pass("no console errors");
} catch (error) {
  fail("operator dashboard smoke runtime", error?.message || String(error));
} finally {
  await browser.close();
}

console.log("");
console.log("=== OPERATOR DASHBOARD QA SUMMARY ===");
console.log(`Passed: ${passes.length}`);
console.log(`Failed: ${failures.length}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const item of failures) console.log(`- ${item.name}: ${item.detail}`);
  process.exitCode = 1;
}
