import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = process.env.FF_AUDIT_BASE_URL || "http://127.0.0.1:5000";
const SLUG = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const URL = `${BASE}/c/${SLUG}`;
const OUT_DIR = "artifacts/frontend-screenshots";
const OUT = path.join(OUT_DIR, "campaign-conversion-contract-audit.json");

const viewports = [
  { name: "mobile", width: 390, height: 1200 },
  { name: "desktop", width: 1440, height: 1100 },
];

const selectors = {
  checkoutTrigger: "[data-ff-open-checkout], [data-ff-donate-trigger], .ff-mobile-rail [data-ff-open-checkout]",
  donationShell: "[data-ff-donation-shell], [data-ff-checkout-shell], [data-ff-donation-modal], [data-ff-checkout-sheet], #checkout, .ff-donatePanel, .ff-donationPanel, .ff-paymentPanel",
  amount: "[data-ff-amount], [data-ff-amount-value], button:has-text('$25'), button:has-text('$50'), button:has-text('$100'), button:has-text('$250')",
  amountInput: "input#custom-amount, input[data-ff-custom-amount], input[data-ff-donation-amount-input]",
  sponsorTrigger: "[data-ff-open-sponsor], [data-ff-sponsor-trigger]",
  sponsorShell: "[data-ff-sponsor-shell], [data-ff-sponsor-sheet], [data-ff-sponsor-section], #sponsors, .ff-sponsorPanel",
  share: "[data-ff-share], [data-ff-share-trigger], [data-ff-qr-trigger], [data-ff-copy-link], [data-ff-copy-share-url]",
};

function assert(ok, label, details = "") {
  return { ok: Boolean(ok), label, details };
}

await fs.mkdir(OUT_DIR, { recursive: true });

const browser = await chromium.launch();
const results = [];

for (const viewport of viewports) {
  const page = await browser.newPage({ viewport });
  await page.goto(URL, { waitUntil: "networkidle" });

  const overflowX = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  results.push({ viewport: viewport.name, ...assert(!overflowX, "no horizontal overflow") });

  const triggerCount = await page.locator(selectors.checkoutTrigger).count();
  results.push({ viewport: viewport.name, ...assert(triggerCount > 0, "checkout trigger exists", `count=${triggerCount}`) });

  if (triggerCount > 0) {
    await page.locator(selectors.checkoutTrigger).first().click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(350);
  }

  const shellCount = await page.locator(selectors.donationShell).count();
  results.push({ viewport: viewport.name, ...assert(shellCount > 0, "donation shell/inline checkout exists", `count=${shellCount}`) });

  const amountCount = await page.locator(selectors.amount).count();
  results.push({ viewport: viewport.name, ...assert(amountCount >= 3, "quick amount controls exist", `count=${amountCount}`) });

  const unlabeledAmountInputs = await page.evaluate((sel) => {
    return Array.from(document.querySelectorAll(sel)).filter((el) => {
      const id = el.getAttribute("id");
      const hasLabel = id && document.querySelector(`label[for="${CSS.escape(id)}"]`);
      return !hasLabel && !el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby");
    }).map((el) => el.outerHTML.slice(0, 180));
  }, selectors.amountInput);

  results.push({
    viewport: viewport.name,
    ...assert(unlabeledAmountInputs.length === 0, "custom amount input has accessible name", unlabeledAmountInputs.join(" | ")),
  });

  const sponsorTriggerCount = await page.locator(selectors.sponsorTrigger).count();
  results.push({ viewport: viewport.name, ...assert(sponsorTriggerCount > 0, "sponsor trigger exists", `count=${sponsorTriggerCount}`) });

  if (sponsorTriggerCount > 0) {
    await page.locator(selectors.sponsorTrigger).first().click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(250);
  }

  const sponsorShellCount = await page.locator(selectors.sponsorShell).count();
  results.push({ viewport: viewport.name, ...assert(sponsorShellCount > 0, "sponsor shell/section exists", `count=${sponsorShellCount}`) });

  const shareCount = await page.locator(selectors.share).count();
  results.push({ viewport: viewport.name, ...assert(shareCount > 0, "share/copy/QR path exists", `count=${shareCount}`) });

  await page.close();
}

await browser.close();

const failed = results.filter((r) => !r.ok);

await fs.writeFile(OUT, JSON.stringify({
  url: URL,
  generatedAt: new Date().toISOString(),
  passed: results.length - failed.length,
  failed: failed.length,
  results,
}, null, 2));

for (const r of results) {
  console.log(`${r.ok ? "PASS" : "CHECK"} [${r.viewport}] ${r.label}${r.details ? ` — ${r.details}` : ""}`);
}

console.log(`\nWrote ${OUT}`);
console.log(`Summary: ${results.length - failed.length}/${results.length} passed`);

if (failed.length) process.exit(1);
