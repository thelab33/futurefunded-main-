#!/usr/bin/env node
/**
 * FutureFunded Hybrid Stripe Money Loop Test
 *
 * Verifies:
 *   Checkout Session created
 *   Stripe Checkout opens
 *   Test payment completes by automation OR manual fallback
 *   Return URL contains session context
 *   FutureFunded session-status resolves paid/complete
 *   Ledger summary responds
 *   Dashboard renders when FF_OPERATOR_ACCESS_TOKEN is set
 *
 * Usage:
 *   FF_HEADLESS=0 FF_OPERATOR_ACCESS_TOKEN="$FF_OPERATOR_ACCESS_TOKEN" \
 *   node scripts/verify/ff_real_stripe_money_loop_hybrid.mjs http://127.0.0.1:5000 connect-atx-elite
 */

const { chromium } = await import("playwright");

const base = (process.argv[2] || process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const operatorToken = process.env.FF_OPERATOR_ACCESS_TOKEN || "";
const headless = process.env.FF_HEADLESS === "0" ? false : true;
const amount = Number(process.env.FF_TEST_AMOUNT || "25");
const testEmail = process.env.FF_TEST_EMAIL || `futurefunded-test-${Date.now()}@example.com`;
const testName = process.env.FF_TEST_NAME || "FutureFunded Test Donor";

const results = [];

function record(ok, label, detail = "") {
  results.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

async function readJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let json = {};
  try { json = JSON.parse(text); } catch (_) {}
  return { res, text, json };
}

async function createCheckoutSession() {
  const payload = {
    amount,
    amount_cents: Math.round(amount * 100),
    frequency: "once",
    donor_name: testName,
    donor_email: testEmail,
    source: "ff-real-stripe-money-loop-hybrid",
  };

  const out = await readJson(`${base}/c/${encodeURIComponent(slug)}/checkout/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });

  const sessionId = out.json?.id || out.json?.session_id || "";
  const checkoutUrl = out.json?.url || out.json?.checkout_url || "";

  record(out.res.ok && Boolean(sessionId || checkoutUrl), "Checkout session created", `status=${out.res.status}${sessionId ? ` id=${sessionId}` : ""}`);

  if (!checkoutUrl) {
    console.log("\nCheckout response body:");
    console.log(out.text.slice(0, 1800));
    process.exit(1);
  }

  return { sessionId, checkoutUrl };
}

async function visibleLocator(page, selectors, timeout = 9000) {
  const started = Date.now();

  while (Date.now() - started < timeout) {
    for (const frame of page.frames()) {
      for (const selector of selectors) {
        try {
          const loc = frame.locator(selector).first();
          if ((await loc.count()) > 0 && (await loc.isVisible({ timeout: 250 }))) {
            return loc;
          }
        } catch (_) {}
      }
    }
    await page.waitForTimeout(350);
  }

  return null;
}

async function maybeFill(page, selectors, value, label, timeout = 9000) {
  const loc = await visibleLocator(page, selectors, timeout);
  if (!loc) {
    console.log(`INFO ${label} field not visible; continuing`);
    return false;
  }

  await loc.fill("").catch(() => {});
  await loc.fill(value);
  record(true, `Filled ${label}`);
  return true;
}

async function maybeClick(page, selectors, label, timeout = 9000) {
  const loc = await visibleLocator(page, selectors, timeout);
  if (!loc) {
    console.log(`INFO ${label} button not visible`);
    return false;
  }

  await loc.click();
  record(true, `Clicked ${label}`);
  return true;
}

async function dumpStripeDebug(page, name) {
  try {
    await page.screenshot({ path: `audit_outputs/${name}.png`, fullPage: true });
  } catch (_) {}

  const debug = [];
  for (const frame of page.frames()) {
    try {
      const inputs = await frame.locator("input, button, select").evaluateAll((els) =>
        els.slice(0, 50).map((el) => ({
          tag: el.tagName,
          type: el.getAttribute("type"),
          name: el.getAttribute("name"),
          id: el.getAttribute("id"),
          autocomplete: el.getAttribute("autocomplete"),
          placeholder: el.getAttribute("placeholder"),
          aria: el.getAttribute("aria-label"),
          text: el.textContent?.trim()?.slice(0, 80) || "",
        }))
      );
      debug.push({ url: frame.url(), inputs });
    } catch (_) {}
  }

  await import("node:fs/promises").then((fs) =>
    fs.writeFile(`audit_outputs/${name}.json`, JSON.stringify(debug, null, 2))
  ).catch(() => {});
}

async function completeStripeCheckout(checkoutUrl) {
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({ viewport: { width: 430, height: 900 } });
  const page = await context.newPage();

  await page.goto(checkoutUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);

  record(true, "Stripe Checkout opened", page.url());

  console.log("\nTest card fallback if manual entry is needed:");
  console.log("  Card: 4242 4242 4242 4242");
  console.log("  Exp: 12/34");
  console.log("  CVC: 123");
  console.log("  ZIP: 78754\n");

  await maybeFill(page, [
    'input[name="email"]',
    'input#email',
    'input[type="email"]',
    'input[autocomplete="email"]',
    'input[aria-label*="email" i]',
  ], testEmail, "email", 5000);

  const cardFilled = await maybeFill(page, [
    'input[name="cardNumber"]',
    'input[autocomplete="cc-number"]',
    'input[aria-label*="card number" i]',
    'input[placeholder*="1234"]',
    'input[placeholder*="Card number" i]',
  ], "4242424242424242", "card number", 9000);

  if (cardFilled) {
    await maybeFill(page, [
      'input[name="cardExpiry"]',
      'input[autocomplete="cc-exp"]',
      'input[aria-label*="expiration" i]',
      'input[aria-label*="expiry" i]',
      'input[placeholder*="MM"]',
    ], "1234", "card expiry", 7000);

    await maybeFill(page, [
      'input[name="cardCvc"]',
      'input[autocomplete="cc-csc"]',
      'input[aria-label*="security code" i]',
      'input[aria-label*="CVC" i]',
      'input[aria-label*="CVV" i]',
      'input[placeholder*="CVC"]',
      'input[placeholder*="CVV"]',
    ], "123", "CVC", 7000);

    await maybeFill(page, [
      'input[name="billingName"]',
      'input[autocomplete="cc-name"]',
      'input[name="name"]',
      'input[aria-label*="name" i]',
    ], testName, "billing name", 4000);

    await maybeFill(page, [
      'input[name="billingPostalCode"]',
      'input[autocomplete="postal-code"]',
      'input[aria-label*="ZIP" i]',
      'input[aria-label*="postal" i]',
      'input[placeholder*="ZIP"]',
      'input[placeholder*="Postal"]',
    ], "78754", "postal code", 4000);

    await maybeClick(page, [
      'button[type="submit"]',
      'button:has-text("Pay")',
      'button:has-text("Donate")',
      'button:has-text("Contribute")',
    ], "payment submit", 9000);
  } else {
    await dumpStripeDebug(page, "stripe-checkout-selector-debug");
    console.log("CHECK Stripe fields were not automatable. Complete the open browser window manually.");
  }

  console.log("Waiting for Stripe to return to FutureFunded...");
  try {
    await page.waitForURL((url) => {
      const href = url.toString();
      return href.startsWith(base) || href.includes("session_id=");
    }, { timeout: 240000 });
  } catch (_) {
    await dumpStripeDebug(page, "stripe-checkout-return-timeout");
  }

  const finalUrl = page.url();
  record(finalUrl.startsWith(base) || finalUrl.includes("session_id="), "Returned from Stripe Checkout", finalUrl);

  await browser.close();
  return finalUrl;
}

async function verifySessionStatus(sessionIdFromCreate, finalUrl) {
  let sessionId = sessionIdFromCreate;

  try {
    const u = new URL(finalUrl);
    sessionId =
      u.searchParams.get("session_id") ||
      u.searchParams.get("checkout_session_id") ||
      u.searchParams.get("stripe_session_id") ||
      sessionId;
  } catch (_) {}

  if (!sessionId) {
    record(false, "Session id available after checkout");
    return { paid: false, sessionId: "" };
  }

  const endpoints = [
    `${base}/c/${encodeURIComponent(slug)}/checkout/session-status?session_id=${encodeURIComponent(sessionId)}`,
    `${base}/c/${encodeURIComponent(slug)}/session-status?session_id=${encodeURIComponent(sessionId)}`,
    `${base}/c/stripe/session-status?session_id=${encodeURIComponent(sessionId)}`,
  ];

  for (let attempt = 1; attempt <= 14; attempt++) {
    for (const endpoint of endpoints) {
      const out = await readJson(endpoint);
      if (!out.res.ok) continue;

      const state = {
        paid: out.json?.paid,
        payment_status: out.json?.payment_status,
        checkout_status: out.json?.checkout_status,
        status: out.json?.status,
      };

      const paid =
        out.json?.paid === true ||
        out.json?.payment_status === "paid" ||
        out.json?.checkout_status === "complete" ||
        out.json?.status === "complete";

      if (paid) {
        record(true, "Session-status confirms paid", `attempt=${attempt} ${JSON.stringify(state)}`);
        return { paid: true, sessionId, payload: out.json };
      }

      console.log(`WAIT session-status not paid yet attempt=${attempt} ${JSON.stringify(state)}`);
    }

    await new Promise((resolve) => setTimeout(resolve, 3000));
  }

  record(false, "Session-status confirms paid", `session_id=${sessionId}`);
  return { paid: false, sessionId };
}

async function verifyLedger() {
  const out = await readJson(`${base}/c/${encodeURIComponent(slug)}/ledger/summary`);
  record(out.res.ok, "Ledger summary responds", `status=${out.res.status}`);

  if (out.res.ok) {
    console.log("Ledger summary sample:");
    console.log(JSON.stringify(out.json, null, 2).slice(0, 1200));
  }
}

async function verifyDashboard() {
  if (!operatorToken) {
    console.log("INFO FF_OPERATOR_ACCESS_TOKEN not set; dashboard authenticated check skipped.");
    return;
  }

  const candidates = [
    `${base}/platform/dashboard?operator_token=${encodeURIComponent(operatorToken)}`,
    `${base}/platform/dashboard?token=${encodeURIComponent(operatorToken)}`,
  ];

  for (const url of candidates) {
    const res = await fetch(url, { headers: { Accept: "text/html" } });
    if (res.ok) {
      const html = await res.text();
      record(/dashboard|command center|ledger|supporters|raised/i.test(html), "Dashboard authenticated page renders", `status=${res.status}`);
      return;
    }
  }

  record(false, "Dashboard authenticated page renders", "No token query variant returned 2xx");
}

console.log("\nFutureFunded HYBRID Stripe money-loop test");
console.log(`Base: ${base}`);
console.log(`Campaign: ${slug}`);
console.log(`Headless: ${headless}`);
console.log(`Email: ${testEmail}`);
console.log(`Amount: $${amount}\n`);

const { sessionId, checkoutUrl } = await createCheckoutSession();
const finalUrl = await completeStripeCheckout(checkoutUrl);
const status = await verifySessionStatus(sessionId, finalUrl);
await verifyLedger();
await verifyDashboard();

const failed = results.filter((r) => !r.ok);

console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);

if (!status.paid) {
  console.log("\nMoney-loop blocker:");
  console.log("- Checkout opened, but FutureFunded did not confirm a paid/complete session.");
  console.log("- Next fix is backend session-status reconciliation or Stripe webhook/ledger write-through.");
}

if (failed.length) {
  console.log("\nFailed/CHECK items:");
  for (const item of failed) console.log(`- ${item.label}${item.detail ? `: ${item.detail}` : ""}`);
  process.exit(1);
}
