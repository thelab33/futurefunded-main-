#!/usr/bin/env node
/**
 * FutureFunded Campaign v1 Authority + Money Loop Smoke
 *
 * Campaign pages MUST NOT load the cinematic platform layer.
 *
 * Usage:
 *   node scripts/verify/ff_campaign_v1_authority_money_loop.mjs http://127.0.0.1:5000 connect-atx-elite
 */

const base = (process.argv[2] || process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const results = [];

function record(ok, label, detail = "") {
  results.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

async function readText(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  return { res, text };
}

async function readJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let json = {};
  try {
    json = JSON.parse(text);
  } catch (_) {}
  return { res, text, json };
}

console.log("\nFutureFunded Campaign v1 authority + money-loop smoke");
console.log(`Base: ${base}`);
console.log(`Campaign: ${slug}\n`);

const campaignUrl = `${base}/c/${encodeURIComponent(slug)}?smoke=campaign-v1-authority`;
const campaign = await readText(campaignUrl);

record(campaign.res.ok, "Campaign page responds", `status=${campaign.res.status}`);
record(campaign.text.includes("ff.css"), "Core ff.css asset is linked");
record(campaign.text.includes("campaign.css"), "Campaign CSS authority is linked");
record(campaign.text.includes("data-ff-checkout-css-contract"), "Checkout CSS contract is owned by campaign.css");
record(!campaign.text.includes("ff.checkout.css") && !campaign.text.includes("ff-checkout-csp.css"), "Legacy checkout CSS files are not linked");
record(campaign.text.includes("ff-campaign.js"), "Campaign JS asset is linked");
record(!campaign.text.includes("ff.cinematic.css"), "Campaign does not load cinematic CSS");
record(!campaign.text.includes("ff-cinematic.js"), "Campaign does not load cinematic JS");
record(campaign.text.includes("ffCampaignConfig"), "Campaign config JSON is present");
record(/data-ff-open-checkout|data-ff-donate-trigger|checkout\/session/.test(campaign.text), "Donate/checkout contract is present");
record(/data-ff-open-sponsor|data-ff-sponsor-trigger|data-ff-sponsor-form/.test(campaign.text), "Sponsor contract is present");
record(/data-ff-share-trigger|data-ff-qr-trigger|ff-shareDrawer/.test(campaign.text), "Share/QR contract is present");

const checkoutPayload = {
  flow: "donation",
  kind: "donation",
  type: "donation",
  payment_flow: "donation",
  checkout_mode: "donation",
  amount: 25,
  amount_cents: 2500,
  amountCents: 2500,
  donor_email: "smoke+campaign-authority@getfuturefunded.com",
  customer_email: "smoke+campaign-authority@getfuturefunded.com",
  email: "smoke+campaign-authority@getfuturefunded.com",
  frequency: "once",
  source: "checkout-direct-authority-v3-smoke"
};

const checkout = await readJson(`${base}/c/${encodeURIComponent(slug)}/checkout/session`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json"
  },
  body: JSON.stringify(checkoutPayload)
});

const sessionId = checkout.json?.id || checkout.json?.session_id || "";
const checkoutUrl = checkout.json?.url || "";

record(
  checkout.res.ok && Boolean(sessionId || checkoutUrl),
  "Checkout session can be created",
  `status=${checkout.res.status}${sessionId ? ` id=${sessionId}` : ""}`
);

if (sessionId) {
  const statusCandidates = [
    `${base}/c/${encodeURIComponent(slug)}/checkout/session-status?session_id=${encodeURIComponent(sessionId)}`,
    `${base}/c/${encodeURIComponent(slug)}/session-status?session_id=${encodeURIComponent(sessionId)}`,
    `${base}/c/stripe/session-status?session_id=${encodeURIComponent(sessionId)}`
  ];

  let found = false;
  for (const url of statusCandidates) {
    const status = await readJson(url);
    if (status.res.ok) {
      found = true;
      const state =
        status.json?.payment_status ||
        status.json?.checkout_status ||
        status.json?.status ||
        status.json?.paid;
      record(true, "Session-status endpoint responds", `state=${JSON.stringify(state)}`);
      break;
    }
  }

  if (!found) {
    record(false, "Session-status endpoint responds", "No candidate endpoint returned 2xx");
  }
} else {
  record(false, "Session-status endpoint responds", "Skipped because checkout did not return a session id");
}

const ledger = await readJson(`${base}/c/${encodeURIComponent(slug)}/ledger/summary`);
record(ledger.res.ok, "Ledger summary endpoint responds", `status=${ledger.res.status}`);

const failed = results.filter((r) => !r.ok);
console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);

if (failed.length) {
  console.log("\nItems to fix before live:");
  for (const item of failed) {
    console.log(`- ${item.label}${item.detail ? `: ${item.detail}` : ""}`);
  }
  process.exit(1);
}
