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
  const response = await page.goto(`${base}/platform/login?login_calm_audit=${Date.now()}`, {
    waitUntil: "networkidle",
  });

  const status = response?.status() || 0;
  record(status >= 200 && status < 400, `Login responds [${viewport.name}]`, `status=${status}`);

  const cssLinked = await page.locator('link[href*="ff-login-calm.css"]').count();
  record(cssLinked > 0, `Login calm CSS linked [${viewport.name}]`, `count=${cssLinked}`);

  const bodyClass = await page.locator("body").getAttribute("class").catch(() => "");
  record((bodyClass || "").includes("ff-loginV4Body"), `Login v4 body scope present [${viewport.name}]`);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, `No horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

  const text = await page.locator("body").innerText().catch(() => "");
  for (const marker of [
    "Run the campaign with confidence",
    "Operator command center",
    "Sign in securely",
    "Protected dashboard",
  ]) {
    record(text.includes(marker), `Login copy marker remains: ${marker} [${viewport.name}]`);
  }

  record(!/{{|{%|%}/.test(text), `No visible template leak [${viewport.name}]`);

  const h1Font = await page.locator("#login-title").evaluate((el) => parseFloat(getComputedStyle(el).fontSize)).catch(() => 0);
  const h1Box = await page.locator("#login-title").boundingBox().catch(() => null);
  const footerBox = await page.locator(".ff-loginV4__footer").boundingBox().catch(() => null);

  if (viewport.name === "desktop") {
    record(h1Font > 72 && h1Font <= 122, `Hero headline pressure reduced [${viewport.name}]`, `font=${Math.round(h1Font)}px`);
    record((h1Box?.height || 0) > 100 && (h1Box?.height || 999) < 335, `Hero headline height controlled [${viewport.name}]`, `height=${Math.round(h1Box?.height || 0)}`);
    record((footerBox?.height || 0) > 0 && (footerBox?.height || 999) < 86, `Footer rail is quiet [${viewport.name}]`, `height=${Math.round(footerBox?.height || 0)}`);
  } else {
    record(h1Font > 44 && h1Font <= 82, `Hero headline mobile scale controlled [${viewport.name}]`, `font=${Math.round(h1Font)}px`);
    record((footerBox?.height || 0) > 0 && (footerBox?.height || 999) < 150, `Footer rail is quiet [${viewport.name}]`, `height=${Math.round(footerBox?.height || 0)}`);
  }

  await page.close();
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
