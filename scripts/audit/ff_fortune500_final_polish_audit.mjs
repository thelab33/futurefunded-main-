import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";

const pages = [
  ["/platform/", "Platform homepage", false],
  ["/c/connect-atx-elite", "Campaign page", false],
  ["/platform/onboarding", "Launch workspace", false],
  ["/platform/dashboard", "Dashboard locked", true],
  ["/platform/login", "Operator login", false],
];

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

for (const [path, label, allowForbidden] of pages) {
  for (const viewport of [
    { name: "desktop", width: 1440, height: 1050 },
    { name: "mobile", width: 390, height: 900 },
  ]) {
    const page = await browser.newPage({ viewport });
    const response = await page.goto(`${base}${path}?f500_audit=${Date.now()}`, { waitUntil: "networkidle" });
    const status = response?.status() || 0;
    const okStatus = allowForbidden ? status >= 200 && status < 500 : status >= 200 && status < 400;

    record(okStatus, `${label} responds [${viewport.name}]`, `status=${status}`);

    const cssLinked = await page.locator('link[href*="ff-fortune500-final.css"]').count().catch(() => 0);
    record(cssLinked > 0 || (allowForbidden && status === 403), `${label} loads final polish CSS [${viewport.name}]`, `count=${cssLinked}`);

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1).catch(() => false);
    record(!overflow, `${label} has no horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

    const text = await page.locator("body").innerText().catch(() => "");
    record(!/{{|{%|%}/.test(text), `${label} has no visible template leak [${viewport.name}]`);

    await page.close();
  }
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
