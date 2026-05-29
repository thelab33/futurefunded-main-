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
  const response = await page.goto(
    `${base}/platform/onboarding?onboarding_exec_audit=${Date.now()}`,
    { waitUntil: "networkidle" }
  );

  const status = response?.status() || 0;
  record(status >= 200 && status < 400, `Onboarding responds [${viewport.name}]`, `status=${status}`);

  const cssLinked = await page.locator('link[href*="ff-onboarding-executive.css"]').count();
  record(cssLinked > 0, `Onboarding executive CSS linked [${viewport.name}]`, `count=${cssLinked}`);

  const bodyClass = await page.locator("body").getAttribute("class").catch(() => "");
  record((bodyClass || "").includes("ff-onboardModernBody"), `Onboarding body scope present [${viewport.name}]`);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, `Onboarding has no horizontal overflow [${viewport.name}]`, `overflow=${overflow}`);

  const text = await page.locator("body").innerText().catch(() => "");
  for (const marker of [
    "Build the campaign before it goes public",
    "Everything needed to go live",
    "Text-to-Donate setup",
    "Sponsor packages, ready for review",
    "Ready when the launch pieces align",
  ]) {
    record(text.toLowerCase().includes(marker.toLowerCase()), `Onboarding copy marker remains: ${marker} [${viewport.name}]`);
  }

  const fields = await page.locator("input, select, textarea").count();
  record(fields >= 16, `Onboarding keeps setup fields [${viewport.name}]`, `count=${fields}`);

  const textFields = await page.locator("input[name='text_to_donate_provider'], input[name='text_to_donate_keyword'], input[name='text_to_donate_number']").count();
  record(textFields >= 3, `Onboarding keeps Text-to-Donate fields [${viewport.name}]`, `count=${textFields}`);

  const hero = await page.locator(".ff-onboardModernHero").boundingBox().catch(() => null);
  record(Boolean(hero), `Onboarding hero present [${viewport.name}]`);
  record((hero?.height || 0) > 0 && (hero?.height || 9999) < (viewport.name === "desktop" ? 720 : 1220), `Onboarding hero height controlled [${viewport.name}]`, `height=${Math.round(hero?.height || 0)}`);

  const sectionCount = await page.locator("main section").count();
  record(sectionCount >= 6, `Onboarding sections remain complete [${viewport.name}]`, `count=${sectionCount}`);

  await page.close();
}

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
