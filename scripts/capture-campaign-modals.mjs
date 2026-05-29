import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const url =
  process.env.CAMPAIGN_URL ||
  process.env.FF_CAMPAIGN_URL ||
  "http://127.0.0.1:5000/c/connect-atx-elite";

const outDir = process.env.FF_MODAL_SCREENSHOT_DIR || "artifacts/frontend-screenshots";

const visibleExpression = (selectors) =>
  selectors.some((selector) =>
    Array.from(document.querySelectorAll(selector)).some((el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();

      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number(style.opacity) !== 0 &&
        rect.width > 0 &&
        rect.height > 0 &&
        el.getAttribute("aria-hidden") !== "true" &&
        !el.hidden
      );
    })
  );

async function clickFirst(page, selectors, label) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();

    if ((await locator.count()) > 0) {
      await locator.scrollIntoViewIfNeeded().catch(() => {});
      await locator.click({ timeout: 8_000 });
      console.log(`✅ Clicked ${label}: ${selector}`);
      return;
    }
  }

  throw new Error(`Could not find clickable ${label}. Tried: ${selectors.join(", ")}`);
}

async function waitVisible(page, selectors, label) {
  await page.waitForFunction(visibleExpression, selectors, { timeout: 10_000 });
  console.log(`✅ ${label} became visible.`);
}

async function newCampaignPage(browser, viewport) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    bypassCSP: true,
  });

  const page = await context.newPage();
  page.setDefaultTimeout(25_000);

  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });

  if (!response || !response.ok()) {
    throw new Error(
      `Could not load campaign URL: ${url}. Status: ${response?.status() ?? "no response"}`
    );
  }

  await page.waitForSelector("#campaign-main");
  await page.waitForSelector("#campaign-hero");
  await page.emulateMedia({ reducedMotion: "reduce" });

  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
      }

      #donation-modal :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]),
      #sponsor-modal :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]),
      #qr-modal :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]),
      [data-ff-donation-modal] :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]),
      [data-ff-sponsor-modal] :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]),
      [data-ff-qr-modal] :is(.ff-modal__panel, .ff-modal-card, .ff-checkout, .ff-dialog, [role="document"]) {
        max-height: none !important;
        overflow: visible !important;
      }
    `,
  });

  return { context, page };
}

async function captureFlow(browser, flow) {
  const { context, page } = await newCampaignPage(browser, flow.viewport);

  if (flow.scrollTo) {
    await page
      .locator(flow.scrollTo)
      .first()
      .scrollIntoViewIfNeeded()
      .catch(() => {});
  }

  await clickFirst(page, flow.triggers, flow.label);
  await waitVisible(page, flow.dialogs, flow.dialogLabel);

  if (flow.fileName.includes("qr")) {
    await page
      .waitForFunction(
        () =>
          Array.from(document.querySelectorAll("[data-ff-qr-image]")).every((img) => img.complete),
        null,
        { timeout: 8_000 }
      )
      .catch(() => {});
  }

  const panel = page.locator(flow.panelSelectors.join(", ")).first();
  const filePath = path.join(outDir, flow.fileName);

  if ((await panel.count()) > 0) {
    await panel.scrollIntoViewIfNeeded().catch(() => {});
    await panel.screenshot({ path: filePath });
  } else {
    await page.screenshot({ path: filePath, fullPage: false });
  }

  await context.close();

  console.log(`✅ Saved ${filePath}`);
}

await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });

try {
  await captureFlow(browser, {
    label: "donation modal trigger",
    dialogLabel: "Donation modal",
    fileName: "campaign-donation-modal.png",
    viewport: { width: 1440, height: 1800 },
    triggers: [
      "#campaign-hero [data-ff-open-checkout]",
      "#donation-card [data-ff-open-checkout]",
      "[data-ff-open-checkout]",
    ],
    dialogs: [
      "#donation-modal",
      "[data-ff-donation-modal]",
      "[data-ff-checkout-modal]",
      '[role="dialog"][aria-labelledby*="donation" i]',
    ],
    panelSelectors: [
      "#donation-modal .ff-modal__panel",
      "#donation-modal .ff-modal-card",
      "#donation-modal .ff-checkout",
      "#donation-modal [role='document']",
      "[data-ff-donation-modal] .ff-modal__panel",
      "[data-ff-checkout-modal] [role='dialog']",
      "#donation-modal",
    ],
  });

  await captureFlow(browser, {
    label: "sponsor modal trigger",
    dialogLabel: "Sponsor modal",
    fileName: "campaign-sponsor-modal.png",
    viewport: { width: 1440, height: 1800 },
    scrollTo: "#sponsor-packages",
    triggers: [
      "#sponsor-packages [data-ff-open-sponsor]",
      "#sponsor-packages [data-ff-sponsor-trigger]",
      "[data-ff-open-sponsor]",
      "[data-ff-sponsor-trigger]",
    ],
    dialogs: [
      "#sponsor-modal",
      "[data-ff-sponsor-modal]",
      '[role="dialog"][aria-labelledby*="sponsor" i]',
      '[role="dialog"][id*="sponsor" i]',
    ],
    panelSelectors: [
      "#sponsor-modal .ff-modal__panel",
      "#sponsor-modal .ff-modal-card",
      "#sponsor-modal .ff-checkout",
      "#sponsor-modal [role='document']",
      "[data-ff-sponsor-modal] .ff-modal__panel",
      "[data-ff-sponsor-modal] [role='dialog']",
      "#sponsor-modal",
    ],
  });

  await captureFlow(browser, {
    label: "QR modal trigger",
    dialogLabel: "QR modal",
    fileName: "campaign-qr-modal.png",
    viewport: { width: 1440, height: 1400 },
    scrollTo: "#share",
    triggers: [
      "[data-ff-qr-trigger]",
      '[data-ff-action="open-qr-modal"]',
      '#share button[aria-controls="qr-modal"]',
    ],
    dialogs: [
      "#qr-modal",
      "[data-ff-qr-modal]",
      "[data-ff-qr-code]",
      "[data-ff-qr]",
      '[role="dialog"][aria-labelledby*="qr" i]',
      '[role="dialog"][id*="qr" i]',
    ],
    panelSelectors: [
      "#qr-modal .ff-qrModal__panel",
      "#qr-modal .ff-modal__panel",
      "#qr-modal [role='document']",
      "[data-ff-qr-modal] .ff-modal__panel",
      "#qr-modal",
    ],
  });

  await captureFlow(browser, {
    label: "mobile rail donation trigger",
    dialogLabel: "Mobile donation modal",
    fileName: "campaign-mobile-donation-modal.png",
    viewport: { width: 390, height: 1400 },
    triggers: [
      ".ff-mobile-rail [data-ff-open-checkout]",
      ".ff-mobile-rail [data-ff-donate-trigger]",
      "[data-ff-mobile-rail] [data-ff-open-checkout]",
      "[data-ff-mobile-conversion-rail] [data-ff-open-checkout]",
    ],
    dialogs: [
      "#donation-modal",
      "[data-ff-donation-modal]",
      "[data-ff-checkout-modal]",
      '[role="dialog"][aria-labelledby*="donation" i]',
    ],
    panelSelectors: [
      "#donation-modal .ff-modal__panel",
      "#donation-modal .ff-modal-card",
      "#donation-modal .ff-checkout",
      "#donation-modal [role='document']",
      "[data-ff-donation-modal] .ff-modal__panel",
      "[data-ff-checkout-modal] [role='dialog']",
      "#donation-modal",
    ],
  });

  console.log("");
  console.log("Open artifacts/frontend-screenshots/campaign-donation-modal.png for review.");
} finally {
  await browser.close();
}
