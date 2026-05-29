import { chromium } from "playwright";
import fs from "node:fs/promises";

const url =
  process.env.CAMPAIGN_URL ||
  process.env.FF_CAMPAIGN_URL ||
  "http://127.0.0.1:5000/c/connect-atx-elite";

const outDir = "artifacts/frontend-screenshots";

async function writeAudit(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`🧪 Wrote ${outDir}/${name}.json`);
}

async function visible(page, selector) {
  return page
    .locator(selector)
    .first()
    .isVisible()
    .catch(() => false);
}

async function count(page, selector) {
  return page
    .locator(selector)
    .count()
    .catch(() => 0);
}

async function clickFirst(page, selectors, label) {
  const attempts = [];

  for (const selector of selectors) {
    const loc = page.locator(selector);
    const total = await loc.count();

    for (let i = 0; i < total; i += 1) {
      const item = loc.nth(i);
      try {
        await item.scrollIntoViewIfNeeded({ timeout: 2000 }).catch(() => {});
        await item.click({ timeout: 3500 });
        console.log(`✅ Clicked ${label}: ${selector}${total > 1 ? ` [${i}]` : ""}`);
        return selector;
      } catch (error) {
        attempts.push(`${selector}${total > 1 ? ` [${i}]` : ""}: ${error.message}`);
      }
    }
  }

  throw new Error(`Could not click ${label}.\n${attempts.join("\n")}`);
}

async function newPage(browser, viewport) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    bypassCSP: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  const page = await context.newPage();
  page.setDefaultTimeout(25_000);

  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
  if (!response || !response.ok()) {
    throw new Error(`Could not load campaign URL: ${url}. Status: ${response?.status()}`);
  }

  await page.waitForSelector("#campaign-main");
  await page.waitForSelector("#campaign-hero");
  await page.emulateMedia({ reducedMotion: "reduce" });

  return { context, page };
}

async function verifyCheckoutPath(browser) {
  const { context, page } = await newPage(browser, { width: 1440, height: 1200 });

  try {
    await clickFirst(
      page,
      [
        "#campaign-hero [data-ff-open-checkout]",
        "#donation-card [data-ff-open-checkout]",
        "[data-ff-open-checkout]",
        "[data-ff-donate-trigger]",
        "[data-ff-payment-trigger]",
        "[data-ff-checkout-trigger]",
      ],
      "checkout trigger"
    );

    const modalVisible =
      (await visible(page, "#donation-modal")) ||
      (await visible(page, "[data-ff-donation-modal]")) ||
      (await visible(page, "[data-ff-checkout-modal]"));

    if (modalVisible) {
      console.log("✅ Donation modal became visible.");
    } else {
      await page
        .locator("#give, #donation-card, [data-ff-donation-card]")
        .first()
        .scrollIntoViewIfNeeded();
      await page.waitForSelector("#give, #donation-card, [data-ff-donation-card]");
      console.log("✅ Inline donation panel verified.");
    }

    const amountHooks = await count(
      page,
      "[data-ff-donation-amount], [data-ff-amount-input], #ff-donation-amount, input[name='amount']"
    );

    if (amountHooks < 1) {
      throw new Error("Missing donation amount hooks.");
    }

    console.log(`✅ Donation amount hooks: ${amountHooks}`);
  } finally {
    await context.close();
  }
}

async function verifySponsorPath(browser) {
  const { context, page } = await newPage(browser, { width: 1440, height: 1400 });

  try {
    await clickFirst(
      page,
      [
        "#sponsor-packages [data-ff-open-sponsor]",
        "[data-ff-open-sponsor]",
        "[data-ff-sponsor-trigger]",
        "[data-ff-sponsor-cta]",
        'a[href="#sponsors"]',
      ],
      "sponsor trigger"
    );

    const modalVisible =
      (await visible(page, "#sponsor-modal")) ||
      (await visible(page, "[data-ff-sponsor-modal]")) ||
      (await visible(page, '[role="dialog"][id*="sponsor" i]'));

    if (modalVisible) {
      console.log("✅ Sponsor modal became visible.");
    } else {
      await page
        .locator("#sponsors, #sponsor-packages, [data-ff-home-section='sponsors']")
        .first()
        .scrollIntoViewIfNeeded();
      await page.waitForSelector("#sponsors, #sponsor-packages");
      console.log("✅ Inline sponsor section verified.");
    }

    const sponsorHooks = await count(
      page,
      "[data-ff-sponsor-tier], [data-ff-sponsor-package], .ff-sponsorTier, .ff-platformSponsorRail article"
    );

    if (sponsorHooks < 1) {
      throw new Error("Missing sponsor package/tier hooks.");
    }

    console.log(`✅ Sponsor hooks: ${sponsorHooks}`);
  } finally {
    await context.close();
  }
}

async function verifySharePath(browser) {
  const { context, page } = await newPage(browser, { width: 1440, height: 1400 });

  try {
    await clickFirst(
      page,
      [
        "[data-ff-qr-trigger]",
        "[data-ff-share-trigger]",
        '[data-ff-action="open-qr-modal"]',
        "#share button",
      ],
      "share/QR trigger"
    );

    const shareVisible =
      (await visible(page, "#share")) ||
      (await visible(page, "[data-ff-share-drawer]")) ||
      (await visible(page, "[data-ff-qr-modal]"));

    if (!shareVisible) {
      throw new Error("Share/QR drawer did not become visible.");
    }

    const copyHooks = await count(
      page,
      "[data-ff-copy-share-url], [data-ff-copy-trigger], #qr-modal-share-url, [data-ff-qr-share-url]"
    );

    if (copyHooks < 1) {
      throw new Error("Missing share copy hooks.");
    }

    console.log(`✅ Share/copy hooks: ${copyHooks}`);

    await page.keyboard.press("Escape").catch(() => {});
  } finally {
    await context.close();
  }
}

async function verifyMobileRail(browser) {
  const { context, page } = await newPage(browser, { width: 390, height: 900 });

  try {
    const railCount = await count(
      page,
      ".ff-mobile-rail, .ff-mobileDonateBar, [data-ff-mobile-rail], [data-ff-mobile-conversion-rail]"
    );

    if (railCount < 1) {
      throw new Error("Missing mobile conversion rail.");
    }

    await clickFirst(
      page,
      [
        ".ff-mobile-rail [data-ff-open-checkout]",
        ".ff-mobileDonateBar [data-ff-open-checkout]",
        "[data-ff-mobile-rail] [data-ff-open-checkout]",
        "[data-ff-mobile-conversion-rail] [data-ff-open-checkout]",
        ".ff-mobileDonateBar a",
      ],
      "mobile rail donation trigger"
    );

    console.log("✅ Mobile conversion rail verified.");
  } finally {
    await context.close();
  }
}

const browser = await chromium.launch({ headless: true });

try {
  await verifyCheckoutPath(browser);
  await verifySponsorPath(browser);
  await verifySharePath(browser);
  await verifyMobileRail(browser);

  await writeAudit("campaign-modal-compatibility", {
    ok: true,
    url,
    checkedAt: new Date().toISOString(),
    mode: "modal-or-inline-compatible",
  });

  console.log("");
  console.log("✅ Campaign modal/share compatibility QA passed.");
} finally {
  await browser.close();
}
