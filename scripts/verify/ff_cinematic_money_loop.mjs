#!/usr/bin/env node
/**
 * FutureFunded Cinematic + Money Loop Smoke
 * Usage:
 *   node scripts/verify/ff_cinematic_money_loop.mjs http://127.0.0.1:5000 connect-atx-elite
 */

const base = (process.argv[2] || process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const results = [];

function record(ok, label, detail = "") {
  results.push({ ok, label, detail });
  const tag = ok ? "PASS" : "CHECK";
  console.log(`${tag} ${label}${detail ? ` — ${detail}` : ""}`);
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

async function main() {
  console.log(`\nFutureFunded cinematic + money loop smoke`);
  console.log(`Base: ${base}`);
  console.log(`Campaign: ${slug}\n`);

  const campaignUrl = `${base}/c/${encodeURIComponent(slug)}?smoke=cinematic-money-loop`;

  const campaign = await readText(campaignUrl);
  record(campaign.res.ok, "Campaign page responds", `status=${campaign.res.status}`);

  record(
    campaign.text.includes("ff.cinematic.css") || campaign.text.includes("data-ff-cinematic-asset=\"css\""),
    "Cinematic CSS asset is linked"
  );

  record(
    campaign.text.includes("ff-cinematic.js") || campaign.text.includes("data-ff-cinematic-asset=\"js\""),
    "Cinematic JS asset is linked"
  );

  record(
    /data-ff-open-checkout|data-ff-donate-trigger|checkout\/session/.test(campaign.text),
    "Donate/checkout contract is present"
  );

  const checkoutPayload = {
    amount: 25,
    amount_cents: 2500,
    frequency: "once",
    source: "ff-cinematic-money-loop-smoke"
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
    "Donate button backend can create Stripe checkout session",
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
        record(true, "Return/session-status endpoint responds", `status=${status.res.status}`);
        const paidLike =
          status.json?.paid === true ||
          status.json?.payment_status ||
          status.json?.checkout_status ||
          status.json?.status;
        record(Boolean(paidLike), "Session-status payload includes payment state", JSON.stringify(paidLike));
        break;
      }
    }

    if (!found) {
      record(false, "Return/session-status endpoint responds", "No candidate endpoint returned 2xx");
    }
  } else {
    record(false, "Return/session-status endpoint responds", "Skipped because checkout did not return a session id");
  }

  const ledger = await readJson(`${base}/c/${encodeURIComponent(slug)}/ledger/summary`);
  record(ledger.res.ok, "Ledger/dashboard summary endpoint responds", `status=${ledger.res.status}`);

  const failed = results.filter((r) => !r.ok);
  console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);

  if (failed.length) {
    console.log("\nItems to fix before the live money loop:");
    for (const item of failed) {
      console.log(`- ${item.label}${item.detail ? `: ${item.detail}` : ""}`);
    }
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error("\nSmoke failed hard:", error);
  process.exit(1);
});
