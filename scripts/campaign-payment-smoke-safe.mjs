#!/usr/bin/env node
import fs from "node:fs"
import path from "node:path"

const BASE_URL = process.env.FF_BASE_URL || "http://127.0.0.1:5000"
const ROOT_URL = BASE_URL.replace(/\/$/, "")
const CAMPAIGN_URL = `${ROOT_URL}/c/connect-atx-elite`
const OUT_DIR = path.resolve("audit_outputs/campaign-payment-smoke")
const LATEST_JSON = path.join(OUT_DIR, "latest.json")
const LATEST_MD = path.join(OUT_DIR, "latest.md")

fs.mkdirSync(OUT_DIR, { recursive: true })

function has(html, needle) {
  return html.includes(needle)
}

function count(html, needle) {
  return html.split(needle).length - 1
}

function pass(name, ok, detail = "") {
  return { name, ok: Boolean(ok), detail }
}

async function fetchText(url) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15000)

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "FutureFundedContractProof/1.0"
      }
    })

    const text = await response.text()
    return { status: response.status, ok: response.ok, text }
  } finally {
    clearTimeout(timer)
  }
}

const startedAt = new Date().toISOString()
let response
let checks = []

try {
  response = await fetchText(CAMPAIGN_URL)
  const html = response.text

  checks = [
    pass("campaign route returns 200", response.status === 200, `HTTP ${response.status}`),
    pass("route body is clean", !/Internal Server Error|Traceback|TemplateSyntaxError/i.test(html)),
    pass("campaign extends campaign base marker", has(html, "campaign-index-on-campaign-base-v1")),
    pass("campaign modal state contract v3 rendered", has(html, "FutureFunded campaign modal state contract v3")),

    pass("campaign CSS rendered", has(html, "campaign.css")),
    pass("ff-campaign.js rendered", has(html, "ff-campaign.js")),
    pass("embedded checkout JS rendered", has(html, "ff-embedded-checkout.js")),
    pass("checkout direct JS rendered", has(html, "ff-checkout-direct.js")),
    pass("donation payload firewall rendered", has(html, "ff-donation-payload-firewall.js")),

    pass("ffCampaignConfig present", has(html, "ffCampaignConfig")),
    pass("ffSponsorContract present", has(html, "ffSponsorContract")),
    pass("checkout session URL present", has(html, "/checkout/session")),
    pass("payments config URL present", has(html, "/payments/config")),
    pass("paypal create URL present", has(html, "/paypal/orders")),

    pass("checkout modal present", has(html, 'id="checkout"') && has(html, "data-ff-checkout-modal")),
    pass("checkout initial state present", has(html, 'aria-hidden="true"') && has(html, "data-ff-checkout-state")),
    pass("checkout open triggers present", has(html, "data-ff-open-checkout") && has(html, "data-ff-donate-trigger") && has(html, "data-ff-payment-trigger")),
    pass("checkout open-state contract present", has(html, 'aria-hidden", "false"') || has(html, 'aria-hidden", "false"'.replaceAll('"', "'")) || has(html, "data-ff-checkout-state") && has(html, "ff-is-open")),

    pass("sponsor modal present", has(html, 'id="sponsor-modal"') && has(html, "data-ff-sponsor-modal")),
    pass("sponsor triggers present", has(html, "data-ff-open-sponsor") && has(html, "data-ff-sponsor-trigger")),
    pass("sponsor state contract present", has(html, "data-ff-sponsor-state")),

    pass("share modal present", has(html, 'id="qr-modal"') && has(html, "data-ff-qr-modal")),
    pass("share triggers present", has(html, "data-ff-share-trigger") || has(html, "data-ff-qr-trigger")),
    pass("share state contract present", has(html, "data-ff-share-state")),

    pass("donation amount controls present", count(html, "data-ff-donation-amount") >= 4, `${count(html, "data-ff-donation-amount")} controls`),
    pass("custom amount input present", has(html, "data-ff-checkout-custom-input")),
    pass("receipt email field present", has(html, "data-ff-checkout-donor-email")),
    pass("checkout continue button present", has(html, "data-ff-start-embedded-checkout"))
  ]
} catch (error) {
  checks = [
    pass("campaign route fetch", false, error?.stack || error?.message || String(error))
  ]
}

const ok = checks.every((check) => check.ok)

const report = {
  url: CAMPAIGN_URL,
  checkedAt: startedAt,
  ok,
  mode: "rendered-contract-no-browser",
  checks
}

fs.writeFileSync(LATEST_JSON, JSON.stringify(report, null, 2))

fs.writeFileSync(
  LATEST_MD,
  [
    "# FutureFunded Campaign Money Contract Proof",
    "",
    `Status: ${ok ? "PASS ✅" : "FAIL ❌"}`,
    `Mode: rendered-contract-no-browser`,
    `URL: ${CAMPAIGN_URL}`,
    `Checked: ${startedAt}`,
    "",
    "| Check | Result | Detail |",
    "|---|---:|---|",
    ...checks.map((check) => `| ${check.name} | ${check.ok ? "PASS" : "FAIL"} | ${String(check.detail || "-").replaceAll("\n", " ")} |`),
    ""
  ].join("\n")
)

console.log("")
console.log(`FutureFunded campaign money contract proof: ${ok ? "PASS" : "FAIL"}`)
console.log(`Results: ${LATEST_JSON}`)

if (!ok) {
  for (const check of checks.filter((item) => !item.ok)) {
    console.error(`❌ ${check.name}: ${check.detail || ""}`)
  }
}

process.exit(ok ? 0 : 1)
