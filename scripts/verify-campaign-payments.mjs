import { chromium } from "playwright";
import fs from "node:fs/promises";

const url =
  process.env.CAMPAIGN_URL ||
  process.env.FF_CAMPAIGN_URL ||
  "http://127.0.0.1:5000/c/connect-atx-elite";

const outDir = "artifacts/frontend-screenshots";

const mutationPattern =
  /(checkout|payment|payments|donation|donate|stripe|paypal|sponsor|session|intent)/i;

const externalProviderPattern = /(stripe\.com|paypal\.com|paypalobjects\.com)/i;

async function writeAudit(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`🧪 Wrote ${outDir}/${name}.json`);
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

async function count(page, selector) {
  return page
    .locator(selector)
    .count()
    .catch(() => 0);
}

async function run() {
  const paymentMutationAttempts = [];
  const providerExternalRequests = [];

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: 1,
    bypassCSP: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  await context.route("**/*", async (route) => {
    const request = route.request();
    const method = request.method();
    const requestUrl = request.url();

    if (externalProviderPattern.test(requestUrl)) {
      providerExternalRequests.push({
        method,
        url: requestUrl,
        resourceType: request.resourceType(),
      });
    }

    const isMutation = !["GET", "HEAD", "OPTIONS"].includes(method);

    if (isMutation && mutationPattern.test(requestUrl)) {
      paymentMutationAttempts.push({
        method,
        url: requestUrl,
        resourceType: request.resourceType(),
        postData: request.postData() || "",
      });

      return route.fulfill({
        status: 418,
        contentType: "application/json",
        body: JSON.stringify({
          blockedBy: "FutureFunded payment readiness QA",
          safe: true,
        }),
      });
    }

    return route.continue();
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

  await clickFirst(
    page,
    [
      "#campaign-hero [data-ff-open-checkout]",
      "#donation-card [data-ff-open-checkout]",
      "[data-ff-open-checkout]",
      "[data-ff-payment-trigger]",
      "[data-ff-donate-trigger]",
      "[data-ff-checkout-trigger]",
    ],
    "donation checkout trigger"
  );

  const donationShellCount = await count(
    page,
    "#donation-modal, [data-ff-donation-modal], [data-ff-checkout-modal], [data-ff-embedded-checkout-shell], [data-ff-embedded-checkout-panel], .ff-checkoutModal, #give, [data-ff-donation-card]"
  );

  if (donationShellCount < 1) {
    throw new Error("Missing donation modal or inline donation shell.");
  }

  const amountCount = await count(
    page,
    "[data-ff-amount-button], [data-ff-donation-amount], [data-ff-checkout-amount], [data-ff-checkout-custom-input], [data-ff-custom-amount], [data-ff-amount-input], #ff-donation-amount, #donation-amount, input[name='amount'], input[type='number']"
  );

  if (amountCount < 1) {
    throw new Error("Missing donation amount controls.");
  }

  const submitCount = await count(
    page,
    "[data-ff-start-embedded-checkout], [data-ff-checkout-continue], [data-ff-payment-submit], [data-ff-action='continue-to-payment'], button[type='submit'], [data-ff-open-checkout]"
  );

  if (submitCount < 1) {
    throw new Error("Missing payment CTA/submit controls.");
  }

  const providerHooks = await count(
    page,
    "[data-ff-payment-provider], [data-ff-provider-option], [data-ff-render-paypal], [data-ff-paypal-mount], [data-ff-provider-status], [data-ff-payment-ready]"
  );

  console.log(`✅ Donation shells: ${donationShellCount}`);
  console.log(`✅ Amount controls: ${amountCount}`);
  console.log(`✅ Submit/CTA controls: ${submitCount}`);
  console.log(`✅ Provider hooks found: ${providerHooks}`);

  if (paymentMutationAttempts.length > 0) {
    await writeAudit("campaign-payment-provider-readiness", {
      ok: false,
      reason: "Payment mutation request was attempted during QA.",
      paymentMutationAttempts,
      providerExternalRequests,
    });

    throw new Error(
      `Blocked ${paymentMutationAttempts.length} payment mutation request(s). QA must not submit payments.`
    );
  }

  await writeAudit("campaign-payment-provider-readiness", {
    ok: true,
    mode: "safe-readiness-smoke",
    donationShellCount,
    amountCount,
    submitCount,
    providerHooks,
    paymentMutationAttempts,
    providerExternalRequests,
    notes: [
      "QA opened/targeted the donation path without submitting payments.",
      "Network route blocked payment-like mutation requests as a safety net.",
      "Provider hooks are counted when present, not required for inline demo mode.",
    ],
  });

  await page.screenshot({
    path: `${outDir}/campaign-payment-provider-readiness.png`,
    fullPage: false,
  });

  await context.close();
  await browser.close();

  console.log("");
  console.log("✅ Campaign payment provider readiness QA passed.");
}

run();
