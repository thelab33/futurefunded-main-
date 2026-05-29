import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || "https://getfuturefunded.com";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 900 } });

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? ` — ${detail}` : ""}`);
}

async function goto(path, label, allowForbidden = false) {
  const response = await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
  const status = response?.status() || 0;
  const ok = allowForbidden ? (status >= 200 && status < 500) : (status >= 200 && status < 400);
  record(ok, `${label} responds`, `status=${status}`);
}

async function noOverflow(label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  record(!overflow, `${label} has no horizontal overflow`, `overflow=${overflow}`);
}

await goto("/platform/?p0_text_audit=1", "Platform");
const platformText = await page.locator("body").innerText().catch(() => "");
record(!/Text-to-Donate lane ready for launch/i.test(platformText), "Platform has no public pending Text-to-Donate placeholder");
await noOverflow("Platform");

await goto("/c/connect-atx-elite?p0_text_audit=1", "Campaign");
const campaignText = await page.locator("body").innerText().catch(() => "");
record(!/Text-to-Donate lane ready for launch/i.test(campaignText), "Campaign has no public pending Text-to-Donate placeholder");
record(!/Sponsor checkout path/i.test(campaignText), "Campaign does not show long sponsor checkout path");
await noOverflow("Campaign");

await goto("/platform/onboarding?p0_text_audit=1", "Onboarding");
record((await page.locator("[data-ff-onboarding-text-to-donate='p0-launch-completion']").count()) > 0, "Onboarding keeps Text-to-Donate setup");
record((await page.locator("input[name='text_to_donate_provider']").count()) > 0, "Onboarding provider field");
record((await page.locator("input[name='text_to_donate_keyword']").count()) > 0, "Onboarding keyword field");
record((await page.locator("input[name='text_to_donate_number']").count()) > 0, "Onboarding number field");
await noOverflow("Onboarding");

await goto("/platform/dashboard?p0_text_audit=1", "Dashboard", true);
const dashboardAssistant = await page.locator("[data-ff-dashboard-launch-assistant='p0-launch-completion']").count().catch(() => 0);
const lockedCopy = await page.locator("body").innerText().then((txt) => /login|sign in|protected|operator|access/i.test(txt)).catch(() => false);
record(dashboardAssistant > 0 || lockedCopy, "Dashboard launch assistant or protected state present", `assistant=${dashboardAssistant}, locked=${lockedCopy}`);

await browser.close();

const failed = checks.filter((check) => !check.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);

if (failed.length) process.exitCode = 1;
