import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

const results = [];

function pass(label, detail = "") {
  results.push({ ok: true, label, detail });
}

function fail(label, detail = "") {
  results.push({ ok: false, label, detail });
}

function hasRawJinja(html) {
  return /\{\{\s*[^}]+\s*\}\}|\{%\s*[^%]+\s*%\}/.test(html);
}

try {
  const rootUrl = `${base}/?root_platform_contract=${Date.now()}`;
  const rootResp = await page.goto(rootUrl, { waitUntil: "networkidle" });
  const rootStatus = rootResp?.status() || 0;
  const rootFinalUrl = page.url();
  const rootText = await page.locator("body").innerText().catch(() => "");
  const rootHtml = await page.content();

  if (rootStatus >= 200 && rootStatus < 400) {
    pass("Root responds", `status=${rootStatus}`);
  } else {
    fail("Root responds", `status=${rootStatus}`);
  }

  const rootLooksPlatform =
    rootFinalUrl.includes("/platform") ||
    /Launch-ready fundraising pages|Fundraising pages|One polished path|One launch system/i.test(rootText);

  if (rootLooksPlatform) {
    pass("Root resolves to platform surface", rootFinalUrl);
  } else {
    fail("Root resolves to platform surface", rootFinalUrl);
  }

  if (!/Connect ATX Elite\s+LIVE|Back the season with care|Organized by Connect ATX Elite/i.test(rootText)) {
    pass("Root no longer presents as campaign-first");
  } else {
    fail("Root still presents as campaign-first");
  }

  if (!hasRawJinja(rootHtml)) {
    pass("Root has no raw Jinja leak");
  } else {
    fail("Root has raw Jinja leak");
  }

  const campaignUrl = `${base}/c/${slug}?jinja_leak_contract=${Date.now()}`;
  const campaignResp = await page.goto(campaignUrl, { waitUntil: "networkidle" });
  const campaignStatus = campaignResp?.status() || 0;
  const campaignHtml = await page.content();
  const campaignText = await page.locator("body").innerText().catch(() => "");

  if (campaignStatus >= 200 && campaignStatus < 400) {
    pass("Campaign demo responds", `status=${campaignStatus}`);
  } else {
    fail("Campaign demo responds", `status=${campaignStatus}`);
  }

  if (/Connect ATX Elite|Fuel the season|Give securely|Secure donation/i.test(campaignText)) {
    pass("Campaign demo remains intact");
  } else {
    fail("Campaign demo remains intact");
  }

  if (!campaignHtml.includes("{{ _safe_campaign_name|e }}") && !hasRawJinja(campaignHtml)) {
    pass("Campaign has no raw Jinja leak");
  } else {
    fail("Campaign has raw Jinja leak");
  }

  const platformUrl = `${base}/platform/?platform_contract=${Date.now()}`;
  const platformResp = await page.goto(platformUrl, { waitUntil: "networkidle" });
  const platformStatus = platformResp?.status() || 0;
  const platformText = await page.locator("body").innerText().catch(() => "");

  if (platformStatus >= 200 && platformStatus < 400) {
    pass("Platform page responds", `status=${platformStatus}`);
  } else {
    fail("Platform page responds", `status=${platformStatus}`);
  }

  if (/Launch-ready fundraising pages|One polished path|Sponsor packages|Show a campaign/i.test(platformText)) {
    pass("Platform positioning copy is present");
  } else {
    fail("Platform positioning copy is present");
  }
} finally {
  await browser.close();
}

for (const result of results) {
  console.log(`${result.ok ? "PASS" : "FAIL"} ${result.label}${result.detail ? ` — ${result.detail}` : ""}`);
}

const failed = results.filter((result) => !result.ok);
console.log(`\nSummary: ${results.length - failed.length}/${results.length} passed`);

if (failed.length) {
  process.exitCode = 1;
}
