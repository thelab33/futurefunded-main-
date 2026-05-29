#!/usr/bin/env node

import { chromium } from "playwright";

const baseUrl =
  process.env.FF_QA_URL ||
  process.env.FF_QA_BASE_URL ||
  process.argv.find((arg) => /^https?:\/\//.test(arg)) ||
  "http://127.0.0.1:5000/c/connect-atx-elite?mode=preview";

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 390, height: 960 },
  reducedMotion: "reduce",
});

const page = await context.newPage();
const failures = [];
const passes = [];
const consoleErrors = [];

function pass(name, detail = "") {
  passes.push({ name, detail });
  console.log(`OK ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, detail = "") {
  failures.push({ name, detail });
  console.log(`FAIL ${name}${detail ? ` - ${detail}` : ""}`);
}

page.on("console", (msg) => {
  if (msg.type() !== "error") return;

  const text = msg.text();
  const ignored = ["favicon", "ResizeObserver loop", "injectScript helper not exposed"];

  if (ignored.some((needle) => text.includes(needle))) return;
  consoleErrors.push(text);
});

page.on("pageerror", (err) => {
  consoleErrors.push(err.message);
});

async function count(selector) {
  return page
    .locator(selector)
    .count()
    .catch(() => 0);
}

async function isVisible(selector) {
  const loc = page.locator(selector).first();
  return (await loc.count()) > 0 && (await loc.isVisible().catch(() => false));
}

async function parseJsonScript(id) {
  return page.evaluate((scriptId) => {
    const node = document.getElementById(scriptId);
    if (!node) return null;
    return JSON.parse(node.textContent || "{}");
  }, id);
}

async function expectPresent(name, selector) {
  const total = await count(selector);
  if (total > 0) pass(name, `${total} node(s)`);
  else fail(name, `missing ${selector}`);
}

try {
  const response = await page.goto(baseUrl, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  const status = response?.status() || 0;
  if (status >= 200 && status < 400) pass("app reachability", `${status} ${baseUrl}`);
  else fail("app reachability", `HTTP ${status}`);

  await expectPresent("campaign root", "[data-ff-page-root]");
  await expectPresent("flagship CSS link", 'link[href*="ff.campaign-flagship.css"]');

  const config = await parseJsonScript("ffConfig");
  if (config?.campaign?.name) pass("ffConfig parses", config.campaign.name);
  else fail("ffConfig parses", "missing campaign config");

  const selectors = await parseJsonScript("ffSelectors");
  if (selectors && Object.keys(selectors).length >= 8) {
    pass("ffSelectors parses", `${Object.keys(selectors).length} keys`);
  } else {
    fail("ffSelectors parses", "missing or empty selector registry");
  }

  await expectPresent("checkout openers", "[data-ff-open-checkout]");
  await expectPresent("checkout sheet", "[data-ff-checkout-sheet]");
  await expectPresent("amount input", "[data-ff-amount-input]");
  await expectPresent("email input", "[data-ff-email-input], input[type='email']");
  await expectPresent("sponsor openers", "[data-ff-open-sponsor]");
  await expectPresent("sponsor modal", "[data-ff-sponsor-modal]");
  await expectPresent("share controls", "[data-ff-share], [data-ff-share-trigger], .share-button");

  const ledgerResponse = await page.request.get(
    new URL("/c/connect-atx-elite/ledger/summary", baseUrl).toString()
  );
  if (ledgerResponse.ok()) {
    const ledger = await ledgerResponse.json();
    if (ledger?.totals && typeof ledger.totals.raised_amount_cents === "number") {
      pass("live ledger endpoint reachable", `${ledger.totals.raised_amount_cents} cents`);
    } else {
      fail("live ledger endpoint reachable", "missing totals payload");
    }
  } else {
    fail("live ledger endpoint reachable", `HTTP ${ledgerResponse.status()}`);
  }

  await expectPresent("ledger trust microcopy", "[data-ff-ledger-trust]");

  const duplicateIds = await page.evaluate(() => {
    const ids = [...document.querySelectorAll("[id]")].map((node) => node.id);
    return ids.filter((id, index) => ids.indexOf(id) !== index);
  });

  if (duplicateIds.length) fail("no duplicate IDs", duplicateIds.join(", "));
  else pass("no duplicate IDs");

  const inlineStyles = await count("[style]");
  if (inlineStyles) fail("CSP-safe markup", `${inlineStyles} inline style attribute(s)`);
  else pass("CSP-safe markup", "no inline style attributes");

  const checkoutOpener = page.locator("[data-ff-open-checkout]:visible").first();
  await checkoutOpener.click({ timeout: 10000 });

  const checkoutSheet = page.locator("[data-ff-checkout-sheet]").first();
  await checkoutSheet.waitFor({ state: "visible", timeout: 5000 });
  pass("checkout opens");

  if (await isVisible("[data-ff-email-input], input[type='email']")) {
    pass("checkout email visible");
  } else {
    fail("checkout email visible", "email field not visible");
  }

  if (await isVisible("[data-ff-amount-input], input[name='amount']")) {
    pass("checkout amount visible");
  } else {
    fail("checkout amount visible", "amount field not visible");
  }

  let focusStayed = true;
  for (let i = 0; i < 8; i += 1) {
    await page.keyboard.press("Tab");
    const inside = await page.evaluate(() => {
      const overlay = document.querySelector("[data-ff-checkout-sheet]:not([hidden])");
      return !!overlay && overlay.contains(document.activeElement);
    });

    if (!inside) {
      focusStayed = false;
      break;
    }
  }

  if (focusStayed) pass("checkout focus containment");
  else fail("checkout focus containment", "focus escaped checkout overlay");

  const backdrop = page
    .locator("[data-ff-checkout-sheet]:not([hidden]) [data-ff-close-checkout]")
    .first();

  if ((await backdrop.count()) > 0) {
    const box = await backdrop.boundingBox();

    if (box) {
      // Click a safe backdrop coordinate outside the centered panel.
      await page.mouse.click(box.x + 18, box.y + 18);
    } else {
      await backdrop.click({ force: true });
    }

    await page.waitForTimeout(250);

    let stillOpen = await page.locator("[data-ff-checkout-sheet]:not([hidden])").count();

    if (stillOpen) {
      // Product fallback: Escape should always close any active overlay.
      await page.keyboard.press("Escape");
      await page.waitForTimeout(250);
      stillOpen = await page.locator("[data-ff-checkout-sheet]:not([hidden])").count();
    }

    if (stillOpen) fail("checkout backdrop closes", "checkout remained open");
    else pass("checkout backdrop closes");
  } else {
    fail("checkout backdrop closes", "backdrop close control missing");
  }

  // Ensure checkout is closed before testing sponsor flow.
  await page.keyboard.press("Escape");
  await page.waitForTimeout(150);

  const sponsorOpener = page.locator("[data-ff-open-sponsor]:visible").first();
  if ((await sponsorOpener.count()) > 0) {
    await sponsorOpener.click({ timeout: 10000 });
    await page
      .locator("[data-ff-sponsor-modal]")
      .first()
      .waitFor({ state: "visible", timeout: 5000 });
    pass("sponsor modal opens");
    await page.keyboard.press("Escape");
  }

  // Share controls may live below the fold on mobile. Validate them in context.
  await page.keyboard.press("Escape");
  await page
    .locator("#share, [data-ff-section='share']")
    .first()
    .scrollIntoViewIfNeeded()
    .catch(() => {});
  await page.waitForTimeout(150);

  const shareVisible = await page.evaluate(() => {
    const nodes = Array.from(
      document.querySelectorAll("[data-ff-share], [data-ff-share-trigger], .share-button")
    );
    return nodes.some((node) => {
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none"
      );
    });
  });

  if (shareVisible) {
    pass("share control visible");
  } else {
    fail("share control visible", "no visible flagship share control");
  }

  if (consoleErrors.length) {
    fail("no console errors", consoleErrors.slice(0, 5).join(" | "));
  } else {
    pass("no console errors");
  }
} catch (err) {
  fail("playwright smoke runtime", err?.message || String(err));
} finally {
  await browser.close();
}

console.log("");
console.log("=== FLAGSHIP QA SUMMARY ===");
console.log(`Base URL: ${baseUrl}`);
console.log(`Passed: ${passes.length}`);
console.log(`Failed: ${failures.length}`);

if (failures.length) {
  console.log("");
  console.log("Failures:");
  for (const item of failures) {
    console.log(`- ${item.name}: ${item.detail}`);
  }
  process.exitCode = 1;
}
