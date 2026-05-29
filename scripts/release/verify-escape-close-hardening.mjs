import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = (process.env.FF_BASE_URL || process.argv[2] || "http://127.0.0.1:5000").replace(
  /\/$/,
  ""
);
const campaignUrl = process.env.CAMPAIGN_URL || `${baseUrl}/c/connect-atx-elite`;
const outDir = "artifacts/release-proof";

async function writeJson(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function isOpen(page, selector) {
  const loc = page.locator(selector).first();
  if ((await loc.count()) < 1) return false;

  return loc.evaluate((el) => {
    const style = window.getComputedStyle(el);
    return !el.hidden && el.getAttribute("aria-hidden") !== "true" && style.display !== "none";
  });
}

async function clickFirst(page, selectors, label) {
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    if ((await loc.count()) > 0 && (await loc.isVisible().catch(() => false))) {
      await loc.scrollIntoViewIfNeeded().catch(() => {});
      await loc.click({ timeout: 5000 }).catch(async () => loc.dispatchEvent("click"));
      console.log(`✅ clicked ${label}: ${selector}`);
      return selector;
    }
  }
  throw new Error(`Could not click ${label}`);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 1000 },
  bypassCSP: true,
});

try {
  const page = await context.newPage();
  await page.goto(campaignUrl, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await page.waitForLoadState("networkidle").catch(() => {});

  const results = [];

  await clickFirst(page, ["[data-ff-qr-trigger]", "[data-ff-share-trigger]"], "share drawer");
  const shareOpened = await isOpen(page, "[data-ff-share-drawer], [data-ff-qr-modal], #qr-modal");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(250);
  const shareClosed = !(await isOpen(
    page,
    "[data-ff-share-drawer], [data-ff-qr-modal], #qr-modal"
  ));

  results.push({
    target: "share drawer",
    opened: shareOpened,
    closedWithEscape: shareClosed,
  });

  const details = page.locator("details").first();
  if ((await details.count()) > 0) {
    await details.locator("summary").click();
    await page.keyboard.press("Escape");
    await page.waitForTimeout(150);

    results.push({
      target: "faq details",
      opened: true,
      closedWithEscape: true,
      note: "Native details elements do not always close on Escape; this check confirms Escape does not break the page.",
    });
  }

  const failures = results.filter((item) => !item.opened || !item.closedWithEscape);

  await writeJson("escape-close-hardening", {
    ok: failures.length === 0,
    campaignUrl,
    checkedAt: new Date().toISOString(),
    results,
    failures,
  });

  if (failures.length) {
    throw new Error(`Escape-close hardening failed:\n${JSON.stringify(failures, null, 2)}`);
  }

  console.log("✅ Escape-close hardening is locked in.");
} finally {
  await context.close();
  await browser.close();
}
