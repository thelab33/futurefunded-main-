import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";

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

  const response = await page.goto(`${base}/platform/?homepage_exec_audit=${Date.now()}`, {
    waitUntil: "networkidle",
  });

  const status = response?.status() || 0;
  record(status >= 200 && status < 400, `Homepage responds [${viewport.name}]`, `status=${status}`);

  const runtime = await page.evaluate(() => window.FutureFundedHomepageExecutive || null);
  record(Boolean(runtime), `Homepage executive runtime installed [${viewport.name}]`);

  record(Boolean(runtime?.commandRail), `Command strip compressed into executive rail [${viewport.name}]`);
  record(Boolean(runtime?.systemBento), `System bento tagged [${viewport.name}]`);
  record(Boolean(runtime?.demoPanel), `Demo panel tagged [${viewport.name}]`);
  record(Boolean(runtime?.sponsorPanel), `Sponsor panel tagged [${viewport.name}]`);
  record(Boolean(runtime?.faqPanel), `FAQ panel tagged [${viewport.name}]`);

  const cssLinked = await page.locator('link[href*="ff-homepage-executive.css"]').count();
  const jsLinked = await page.locator('script[src*="ff-homepage-executive.js"]').count();
  record(cssLinked > 0, `Homepage executive CSS linked [${viewport.name}]`, `count=${cssLinked}`);
  record(jsLinked > 0, `Homepage executive JS linked [${viewport.name}]`, `count=${jsLinked}`);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, `No horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

  const bodyText = await page.locator("body").innerText().catch(() => "");
  const htmlText = await page.content().catch(() => "");
  const searchable = `${bodyText}\n${htmlText}`.toLowerCase();

  for (const marker of [
    "Fundraising pages",
    "Campaign readiness",
    "One polished path",
    "One launch system",
    "Sponsor packages",
    "Show a campaign",
  ]) {
    record(searchable.includes(marker.toLowerCase()), `Homepage copy marker remains: ${marker} [${viewport.name}]`);
  }

  const commandHeight = await page.locator('[data-ff-home-exec="command-rail"]').first().boundingBox()
    .then((box) => box?.height || 0)
    .catch(() => 0);

  if (viewport.name === "desktop") {
    record(commandHeight > 0 && commandHeight < 320, `Command rail is compact [${viewport.name}]`, `height=${Math.round(commandHeight)}`);
  } else {
    record(commandHeight > 0 && commandHeight < 520, `Command rail is compact [${viewport.name}]`, `height=${Math.round(commandHeight)}`);
  }

  await page.close();
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
