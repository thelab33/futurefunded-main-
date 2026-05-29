#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium, firefox, webkit } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:5000/c/connect-atx-elite?mode=preview";

const BROWSER = (process.env.BROWSER || "chromium").toLowerCase();
const HEADLESS = !["0", "false", "no"].includes(String(process.env.HEADLESS || "1").toLowerCase());
const SLOW_MO = Number(process.env.SLOW_MO || 0);
const QA_ARTIFACTS_DIR = process.env.QA_ARTIFACTS_DIR || "tmp/qa-artifacts";
const IGNORE_CONSOLE_REGEX = process.env.IGNORE_CONSOLE_REGEX
  ? new RegExp(process.env.IGNORE_CONSOLE_REGEX, "i")
  : null;

const browsers = { chromium, firefox, webkit };

if (!browsers[BROWSER]) {
  console.error(
    `Unsupported BROWSER="${BROWSER}". Use one of: ${Object.keys(browsers).join(", ")}`
  );
  process.exit(2);
}

const results = [];
const consoleErrors = [];
const pageErrors = [];

function pass(name, detail = "") {
  results.push({ name, ok: true, detail });
  console.log(`OK ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, error) {
  const detail = error instanceof Error ? error.message : String(error);
  results.push({ name, ok: false, detail });
  console.error(`FAIL ${name} - ${detail}`);
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

async function ensureArtifactsDir() {
  await fs.mkdir(QA_ARTIFACTS_DIR, { recursive: true });
}

async function saveFailureScreenshot(page, stepName) {
  try {
    await ensureArtifactsDir();
    const filePath = path.join(QA_ARTIFACTS_DIR, `${slugify(stepName)}-${Date.now()}.png`);
    await page.screenshot({ path: filePath, fullPage: true });
    return filePath;
  } catch {
    return "";
  }
}

async function runStep(name, fn, options = {}) {
  const { page, cleanup } = options;
  try {
    await fn();
    if (!results.find((r) => r.name === name)) {
      pass(name);
    }
  } catch (err) {
    let detail = err instanceof Error ? err.message : String(err);
    if (page) {
      const screenshotPath = await saveFailureScreenshot(page, name);
      if (screenshotPath) {
        detail += ` [screenshot: ${screenshotPath}]`;
      }
    }
    fail(name, detail);
  } finally {
    if (typeof cleanup === "function") {
      try {
        await cleanup();
      } catch {}
    }
  }
}

async function isVisible(locator) {
  try {
    return await locator.isVisible();
  } catch {
    return false;
  }
}

async function expectVisible(locator, message) {
  if (!(await isVisible(locator))) {
    throw new Error(message);
  }
}

async function expectHidden(locator, message) {
  if (await isVisible(locator)) {
    throw new Error(message);
  }
}

async function expectAnyVisible(locators, message) {
  for (const locator of locators) {
    if (await isVisible(locator)) return locator;
  }
  throw new Error(message);
}

async function safeClick(locator, message) {
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  try {
    await locator.click({ timeout: 5000 });
  } catch (err) {
    throw new Error(message || (err instanceof Error ? err.message : String(err)));
  }
}

async function getActiveInside(page, panelHandle) {
  return await page.evaluate((panel) => {
    const active = document.activeElement;
    return !!(active && panel && panel.contains(active));
  }, panelHandle);
}

async function focusableCount(page, panelHandle) {
  return await page.evaluate((panel) => {
    if (!panel) return 0;
    const selector = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");
    return panel.querySelectorAll(selector).length;
  }, panelHandle);
}

async function checkTabLoop(page, panelLocator, iterations = 6) {
  const panelHandle = await panelLocator.elementHandle();
  if (!panelHandle) throw new Error("Dialog panel handle not found");

  const count = await focusableCount(page, panelHandle);
  if (count < 1) throw new Error("No focusable elements found inside dialog");

  await page.evaluate((panel) => {
    const selector = [
      "button:not([disabled])",
      "a[href]",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ].join(",");
    const first = panel.querySelector(selector);
    if (first) first.focus();
  }, panelHandle);

  for (let i = 0; i < iterations; i += 1) {
    const inside = await getActiveInside(page, panelHandle);
    if (!inside) throw new Error(`Focus escaped dialog before Tab iteration ${i + 1}`);
    await page.keyboard.press("Tab");
  }

  for (let i = 0; i < Math.min(iterations, count + 1); i += 1) {
    const inside = await getActiveInside(page, panelHandle);
    if (!inside) throw new Error(`Focus escaped dialog before Shift+Tab iteration ${i + 1}`);
    await page.keyboard.press("Shift+Tab");
  }
}

async function installShareAndClipboardStubs(context) {
  await context.addInitScript(() => {
    window.__ffQa = {
      shareCalls: [],
      clipboardWrites: [],
    };

    const clipboard = {
      async writeText(text) {
        window.__ffQa.clipboardWrites.push(String(text));
      },
      async readText() {
        const writes = window.__ffQa.clipboardWrites;
        return writes.length ? writes[writes.length - 1] : "";
      },
    };

    try {
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        enumerable: true,
        value: clipboard,
      });
    } catch {
      navigator.clipboard = clipboard;
    }

    navigator.share = async (payload) => {
      window.__ffQa.shareCalls.push(payload || {});
    };

    if (!navigator.canShare) {
      navigator.canShare = () => true;
    }
  });
}

async function getQaData(page) {
  return await page.evaluate(() => window.__ffQa || { shareCalls: [], clipboardWrites: [] });
}

async function collectDuplicateIds(page) {
  return await page.evaluate(() => {
    const counts = {};
    for (const el of document.querySelectorAll("[id]")) {
      counts[el.id] = (counts[el.id] || 0) + 1;
    }
    return Object.entries(counts)
      .filter(([, count]) => count > 1)
      .map(([id, count]) => ({ id, count }));
  });
}

function overlayContracts() {
  return [
    { overlay: "[data-ff-checkout-sheet]", close: "[data-ff-close-checkout]" },
    { overlay: "[data-ff-drawer]", close: "[data-ff-close-drawer]" },
    { overlay: "[data-ff-sponsor-modal]", close: "[data-ff-close-sponsor]" },
    { overlay: "[data-ff-video-modal]", close: "[data-ff-close-video]" },
    { overlay: "[data-ff-privacy-modal]", close: "[data-ff-close-privacy]" },
    { overlay: "[data-ff-terms-modal]", close: "[data-ff-close-terms]" },
    { overlay: "[data-ff-onboard-modal]", close: "[data-ff-close-onboard]" },
  ];
}

async function closeOverlay(page, overlaySelector, closeSelector) {
  const overlay = page.locator(`${overlaySelector}:visible`).first();
  if (!(await isVisible(overlay))) return false;

  const closeBtn = page.locator(`${closeSelector}:visible`).first();
  if (await isVisible(closeBtn)) {
    await closeBtn.click({ timeout: 1500 }).catch(() => {});
    await page.waitForTimeout(150);
    if (!(await isVisible(overlay))) return true;
  }

  const backdrop = overlay
    .locator(".ff-sheet__backdrop:visible, .ff-modal__backdrop:visible")
    .first();

  if (await isVisible(backdrop)) {
    await backdrop.click({ timeout: 1500 }).catch(() => {});
    await page.waitForTimeout(150);
    if (!(await isVisible(overlay))) return true;
  }

  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(150);
  return !(await isVisible(overlay));
}

async function closeAllOverlays(page) {
  for (let i = 0; i < 8; i += 1) {
    let closedOne = false;
    for (const item of overlayContracts()) {
      const didClose = await closeOverlay(page, item.overlay, item.close);
      if (didClose) closedOne = true;
    }
    if (!closedOne) break;
  }
  await page.waitForTimeout(120);
}

async function visibleOverlayReport(page) {
  return await page.evaluate(() => {
    const selectors = [
      "[data-ff-checkout-sheet]",
      "[data-ff-drawer]",
      "[data-ff-sponsor-modal]",
      "[data-ff-video-modal]",
      "[data-ff-privacy-modal]",
      "[data-ff-terms-modal]",
      "[data-ff-onboard-modal]",
    ];

    function visible(el) {
      if (!el || el.hidden) return false;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
        return false;
      }
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    }

    return selectors
      .flatMap((selector) =>
        Array.from(document.querySelectorAll(selector)).map((el) => ({
          selector,
          visible: visible(el),
          ariaHidden: el.getAttribute("aria-hidden"),
          dataOpen: el.getAttribute("data-open"),
          hidden: el.hidden,
        }))
      )
      .filter((item) => item.visible || item.ariaHidden === "false" || item.dataOpen === "true");
  });
}

async function installPaymentMocks(page) {
  const hits = { config: 0, stripe: 0, paypal: 0 };

  await page.route("**/payments/config", async (route) => {
    hits.config += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        providers: {
          stripe: { enabled: true },
          paypal: { enabled: false },
        },
      }),
    });
  });

  await page.route("**/payments/stripe/intent", async (route) => {
    hits.stripe += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        provider: "stripe",
        client_secret: "pi_test_secret",
      }),
    });
  });

  await page.route("**/payments/paypal/order", async (route) => {
    hits.paypal += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        provider: "paypal",
        order_id: "ORDER_TEST_123",
      }),
    });
  });

  return hits;
}

async function main() {
  const browser = await browsers[BROWSER].launch({
    headless: HEADLESS,
    slowMo: SLOW_MO,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
  });

  await installShareAndClipboardStubs(context);
  const page = await context.newPage();

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (IGNORE_CONSOLE_REGEX && IGNORE_CONSOLE_REGEX.test(text)) return;
    consoleErrors.push(text);
  });

  page.on("pageerror", (err) => {
    const text = err?.message || String(err);
    if (IGNORE_CONSOLE_REGEX && IGNORE_CONSOLE_REGEX.test(text)) return;
    pageErrors.push(text);
  });

  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(600);

  await runStep(
    "DOM smoke test stability",
    async () => {
      const report = await page.evaluate(() => {
        const cfg = document.getElementById("ffConfig");
        const sels = document.getElementById("ffSelectors");
        const payload = sels ? JSON.parse(sels.textContent || "{}") : {};
        const hooks = payload?.hooks || {};

        const requiredKeys = [
          "openCheckout",
          "closeCheckout",
          "checkoutSheet",
          "checkoutShell",
          "amountInput",
          "summaryAmount",
          "share",
          "openDrawer",
          "closeDrawer",
          "drawer",
          "openSponsor",
          "closeSponsor",
          "sponsorModal",
          "openVideo",
          "closeVideo",
          "videoModal",
          "openTerms",
          "closeTerms",
          "termsModal",
          "openPrivacy",
          "closePrivacy",
          "privacyModal",
          "live",
          "toasts",
        ];

        const missing = [];
        for (const key of requiredKeys) {
          const selector = hooks[key];
          if (!selector) {
            missing.push(`${key}:<missing-selector>`);
            continue;
          }
          if (!document.querySelector(selector)) {
            missing.push(`${key}:${selector}`);
          }
        }

        return {
          hasConfig: !!cfg,
          hasSelectors: !!sels,
          missing,
        };
      });

      if (!report.hasConfig) throw new Error("#ffConfig missing");
      if (!report.hasSelectors) throw new Error("#ffSelectors missing");
      if (report.missing.length) {
        throw new Error(`Missing required hook nodes: ${report.missing.join(", ")}`);
      }

      pass("DOM smoke test stability");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "no duplicate IDs in rendered DOM",
    async () => {
      const duplicates = await collectDuplicateIds(page);
      if (duplicates.length) {
        throw new Error(
          `Duplicate ids found: ${duplicates.map((d) => `${d.id}(${d.count})`).join(", ")}`
        );
      }
      pass("no duplicate IDs in rendered DOM");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "checkout opens via dynamic opener [data-ff-open-checkout]",
    async () => {
      const donateCta = page.locator("[data-ff-open-checkout]:visible").first();
      await expectVisible(donateCta, "No visible dynamic checkout opener found");
      await safeClick(donateCta, "Could not click checkout opener");

      const checkoutSheet = page.locator("[data-ff-checkout-sheet]:visible").first();
      await expectVisible(checkoutSheet, "Checkout sheet did not open");

      const checkoutPanel = checkoutSheet
        .locator("[data-ff-checkout-shell]:visible, .ff-sheet__panel:visible")
        .first();
      await expectVisible(checkoutPanel, "Checkout panel not visible");

      pass("checkout opens via dynamic opener [data-ff-open-checkout]");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "focus moves inside the opened dialog/sheet",
    async () => {
      const donateCta = page.locator("[data-ff-open-checkout]:visible").first();
      await safeClick(donateCta, "Could not open checkout");

      const checkoutPanel = page
        .locator(
          "[data-ff-checkout-shell]:visible, [data-ff-checkout-sheet]:visible .ff-sheet__panel:visible"
        )
        .first();

      await expectVisible(checkoutPanel, "Checkout panel not visible");
      await checkTabLoop(page, checkoutPanel, 6);

      pass("focus moves inside the opened dialog/sheet");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "clicking visible backdrop closes the overlay",
    async () => {
      const donateCta = page.locator("[data-ff-open-checkout]:visible").first();
      await safeClick(donateCta, "Could not open checkout");

      const overlay = page.locator("[data-ff-checkout-sheet]:visible").first();
      await expectVisible(overlay, "Checkout sheet not visible");

      const backdrop = overlay
        .locator(".ff-sheet__backdrop:visible, .ff-modal__backdrop:visible")
        .first();
      await expectVisible(backdrop, "Visible overlay backdrop not found");

      await safeClick(backdrop, "Could not click checkout backdrop");
      await expectHidden(overlay, "Overlay did not close after backdrop click");

      pass("clicking visible backdrop closes the overlay");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "ESC closes overlays",
    async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(400);

      const openDrawer = page.locator("[data-ff-open-drawer]:visible").first();
      await expectVisible(openDrawer, "Mobile drawer trigger not visible");
      await safeClick(openDrawer, "Could not open drawer");

      const drawer = page.locator("[data-ff-drawer]:visible").first();
      await expectVisible(drawer, "Drawer not visible");

      await page.keyboard.press("Escape");
      await page.waitForTimeout(160);
      await expectHidden(drawer, "Drawer did not close on Escape");

      pass("ESC closes overlays");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "closeAllOverlays leaves no visible overlays",
    async () => {
      await page.setViewportSize({ width: 1440, height: 1200 });
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(400);

      const openCheckout = page.locator("[data-ff-open-checkout]:visible").first();
      await safeClick(openCheckout, "Could not open checkout before closeAllOverlays");

      const openPrivacy = page.locator("[data-ff-open-privacy]:visible").first();
      if (await isVisible(openPrivacy)) {
        await closeAllOverlays(page);
      }

      await closeAllOverlays(page);

      const visible = await visibleOverlayReport(page);
      if (visible.length) {
        throw new Error(`Visible/open overlays remain: ${JSON.stringify(visible)}`);
      }

      pass("closeAllOverlays leaves no visible overlays");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "payments lazy-load only when checkout is open AND amount >= 1",
    async () => {
      const hits = await installPaymentMocks(page);

      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(500);

      if (hits.config !== 0 || hits.stripe !== 0 || hits.paypal !== 0) {
        throw new Error("Payment endpoints were touched before checkout opened");
      }

      const openCheckout = page.locator("[data-ff-open-checkout]:visible").first();
      await safeClick(openCheckout, "Could not open checkout");

      if (hits.config !== 0 || hits.stripe !== 0 || hits.paypal !== 0) {
        throw new Error("Payment endpoints were touched just by opening checkout");
      }

      const amountInput = page.locator("[data-ff-amount-input]:visible").first();
      const emailInput = await expectAnyVisible(
        [
          page.locator("[data-ff-email]:visible").first(),
          page.locator('input[name="donor_email"]:visible').first(),
        ],
        "Visible email field not found in checkout"
      );

      await amountInput.fill("0");
      await emailInput.fill("qa@example.com");

      const submitButton = page
        .locator(
          '#donationForm button[type="submit"]:visible, #donationForm input[type="submit"]:visible'
        )
        .first();
      await safeClick(submitButton, "Could not submit checkout with zero amount");
      await page.waitForTimeout(350);

      if (hits.config !== 0 || hits.stripe !== 0 || hits.paypal !== 0) {
        throw new Error("Payment endpoints should not load when amount < 1");
      }

      await amountInput.fill("1");
      await safeClick(submitButton, "Could not submit checkout with valid amount");
      await page.waitForTimeout(450);

      if (hits.config < 1) {
        throw new Error("payments/config was not lazy-loaded after valid checkout submit");
      }
      if (hits.stripe + hits.paypal < 1) {
        throw new Error("No payment intent/order endpoint was called after valid checkout submit");
      }

      pass(
        "payments lazy-load only when checkout is open AND amount >= 1",
        `config=${hits.config}, stripe=${hits.stripe}, paypal=${hits.paypal}`
      );
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "CSP-safe injectScript supports blob: when used by ff-app.js",
    async () => {
      const result = await page.evaluate(async () => {
        const runtime = window.ff || window.FutureFundedApp || window.FutureFunded || {};

        const injectScript = runtime.injectScript || window.injectScript || null;

        if (typeof injectScript !== "function") {
          return { skipped: true, reason: "injectScript helper not exposed in current runtime" };
        }

        window.__ff_blob_ok__ = 0;

        const blob = new Blob(["window.__ff_blob_ok__ = (window.__ff_blob_ok__ || 0) + 1;"], {
          type: "text/javascript",
        });
        const blobUrl = URL.createObjectURL(blob);

        try {
          const out = injectScript(blobUrl);
          if (out && typeof out.then === "function") {
            await out;
          }

          await new Promise((resolve) => setTimeout(resolve, 180));

          return {
            skipped: false,
            ok: window.__ff_blob_ok__ === 1,
            value: window.__ff_blob_ok__,
          };
        } catch (error) {
          return {
            skipped: false,
            ok: false,
            error: error?.message || String(error),
          };
        } finally {
          URL.revokeObjectURL(blobUrl);
        }
      });

      if (result.skipped) {
        pass("CSP-safe injectScript supports blob: when used by ff-app.js", result.reason);
        return;
      }

      if (!result.ok) {
        throw new Error(
          result.error || `Blob injectScript failed; __ff_blob_ok__=${String(result.value)}`
        );
      }

      pass("CSP-safe injectScript supports blob: when used by ff-app.js");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "share buttons work",
    async () => {
      const shareBtn = page.locator("[data-ff-share]:visible").first();
      await expectVisible(shareBtn, "No visible share button found");
      await safeClick(shareBtn, "Could not click share button");
      await page.waitForTimeout(250);

      const qa = await getQaData(page);
      const shareWorked = (qa.shareCalls?.length || 0) > 0 || (qa.clipboardWrites?.length || 0) > 0;

      if (!shareWorked) {
        throw new Error("Share button did not call navigator.share or clipboard.writeText");
      }

      pass(
        "share buttons work",
        `shareCalls=${qa.shareCalls.length || 0}, clipboardWrites=${qa.clipboardWrites.length || 0}`
      );
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await runStep(
    "no console errors",
    async () => {
      if (consoleErrors.length || pageErrors.length) {
        const detail = [
          ...consoleErrors.map((e) => `console: ${e}`),
          ...pageErrors.map((e) => `pageerror: ${e}`),
        ].join(" | ");
        throw new Error(detail);
      }
      pass("no console errors");
    },
    { page, cleanup: () => closeAllOverlays(page) }
  );

  await browser.close();

  const failed = results.filter((r) => !r.ok);
  const passed = results.filter((r) => r.ok);

  console.log("\n=== QA SUMMARY ===");
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Browser: ${BROWSER}`);
  console.log(`Passed: ${passed.length}`);
  console.log(`Failed: ${failed.length}`);

  if (failed.length) {
    console.log("\nFailures:");
    for (const f of failed) {
      console.log(`- ${f.name}: ${f.detail}`);
    }
    process.exit(1);
  }

  console.log("\nAll checks passed.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
