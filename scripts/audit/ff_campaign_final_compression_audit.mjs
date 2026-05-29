import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1050 },
  { name: "mobile", width: 390, height: 900 },
]) {
  const page = await browser.newPage({ viewport });
  const response = await page.goto(`${base}/c/${slug}?campaign_compression_audit=${Date.now()}`, {
    waitUntil: "networkidle",
  });

  const status = response?.status() || 0;
  record(status >= 200 && status < 400, `Campaign responds [${viewport.name}]`, `status=${status}`);

  const runtime = await page.evaluate(() => window.FutureFundedCampaignFinalCompression || null);
  record(Boolean(runtime), `Final compression runtime installed [${viewport.name}]`);

  record(Boolean(runtime?.hiddenMomentum), `Momentum strip hidden [${viewport.name}]`);
  record(Boolean(runtime?.hasAthletesCompression), `Athletes proof compressed [${viewport.name}]`);
  record(Boolean(runtime?.hasStoryCompression), `Story section compressed [${viewport.name}]`);
  record(Boolean(runtime?.sponsorMovedAfterSupport), `Sponsor packages moved earlier [${viewport.name}]`);

  const cssLinked = await page.locator('link[href*="ff-campaign-final-compression.css"]').count();
  const jsLinked = await page.locator('script[src*="ff-campaign-final-compression.js"]').count();
  record(cssLinked > 0, `Compression CSS linked [${viewport.name}]`, `count=${cssLinked}`);
  record(jsLinked > 0, `Compression JS linked [${viewport.name}]`, `count=${jsLinked}`);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, `No horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

  const text = await page.locator("body").innerText().catch(() => "");
  record(!/Momentum is building/i.test(text), `Momentum copy not visible [${viewport.name}]`);
  record(/Donate now|Back the season|What support covers|Sponsor|The essentials before you give/i.test(text), `Core conversion copy remains [${viewport.name}]`);

  const sections = await page.locator("main section:not([hidden])").count().catch(() => 999);
  record(sections <= 8, `Visible section count reduced [${viewport.name}]`, `sections=${sections}`);

  await page.close();
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
