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
  { name: "mobile", width: 390, height: 900 },
  { name: "desktop", width: 1440, height: 1100 },
]) {
  const page = await browser.newPage({ viewport });

  const response = await page.goto(`${base}/c/${slug}?conversion_trim_audit=${Date.now()}`, {
    waitUntil: "networkidle",
  });

  const status = response?.status() || 0;
  record(status >= 200 && status < 400, `Campaign responds [${viewport.name}]`, `status=${status}`);

  const text = await page.locator("body").innerText().catch(() => "");
  const sectionCount = await page.locator("main section:not([hidden])").count().catch(() => 0);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);

  record(!/Sponsor checkout path/i.test(text), `Sponsor checkout path removed [${viewport.name}]`);
  record(!/Choose a package,\s*confirm recognition,\s*then pay securely/i.test(text), `Sponsor sales form explainer removed [${viewport.name}]`);
  record(!/After someone supports/i.test(text), `After-support operator proof removed [${viewport.name}]`);
  record(!/Receipts,\s*sponsor follow-up,\s*and operator alerts/i.test(text), `Operator-alert proof removed [${viewport.name}]`);
  record(!/Text-to-Donate lane ready for launch/i.test(text), `Pending Text-to-Donate card removed [${viewport.name}]`);
  record(/Fuel the season|Give securely|Complete your donation|Sponsor packages|The essentials before you give/i.test(text), `Core campaign conversion copy remains [${viewport.name}]`);
  record(sectionCount <= 10, `Campaign section count is tighter [${viewport.name}]`, `sections=${sectionCount}`);
  record(!overflow, `No horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

  await page.close();
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
