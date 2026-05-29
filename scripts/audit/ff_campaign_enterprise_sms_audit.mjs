import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });

try {
  const response = await page.goto(`${base}/c/${slug}?enterprise_sms_audit=${Date.now()}`, { waitUntil: "networkidle" });
  record((response?.status() || 0) >= 200 && (response?.status() || 0) < 400, "Campaign responds", `status=${response?.status()}`);

  const enterpriseReady = await page.evaluate(() => Boolean(window.FutureFundedEnterpriseCampaign));
  record(enterpriseReady, "Enterprise campaign runtime installed");

  const cssLinked = await page.locator('link[href*="ff-campaign-enterprise.css"]').count();
  record(cssLinked > 0, "Enterprise CSS linked", `count=${cssLinked}`);

  const launchCssLinked = await page.locator('link[href*="ff-launch-completion.css"]').count();
  record(launchCssLinked > 0, "Launch CSS linked outside ff.css", `count=${launchCssLinked}`);

  const pendingTextVisible = await page.getByText(/Text-to-Donate lane ready for launch/i).count().catch(() => 0);
  record(pendingTextVisible === 0, "No public pending Text-to-Donate card", `count=${pendingTextVisible}`);

  const hiddenCount = await page.locator("[data-ff-enterprise-hidden='true']").count();
  record(hiddenCount >= 1, "Enterprise trim hid duplicate/internal sections", `count=${hiddenCount}`);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, "No horizontal overflow", `overflow=${overflow}`);

  const webhook = await fetch(`${base}/sms/twilio/incoming`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      From: "+15551234567",
      To: "+15557654321",
      Body: process.env.FF_TEXT_TO_DONATE_KEYWORD || "ATXELITE"
    })
  });

  const webhookText = await webhook.text();
  record(webhook.status === 200 || webhook.status === 403, "Native SMS webhook reachable", `status=${webhook.status}`);
  record(/<Response>|<Message>|FutureFunded|Connect ATX Elite/i.test(webhookText), "Native SMS webhook returns TwiML-ish response");
} finally {
  await browser.close();
}

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
