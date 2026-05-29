import { chromium, expect } from "@playwright/test";
import fs from "node:fs/promises";

const checkoutUrl = process.env.FF_TEST_CHECKOUT_URL || process.env.STRIPE_TEST_CHECKOUT_URL || "";
const stripeSecretKey = process.env.STRIPE_SECRET_KEY || "";
const outDir = "artifacts/conversion-proof";

async function ensureOutDir() {
  await fs.mkdir(outDir, { recursive: true });
}

async function writeJson(name, payload) {
  await ensureOutDir();
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function writeText(name, text) {
  await ensureOutDir();
  await fs.writeFile(`${outDir}/${name}`, text);
}

function redactCheckoutUrl(value = "") {
  return String(value).replace(/cs_test_[^#?]*/g, "cs_test_REDACTED");
}

function extractCheckoutSessionId(url = "") {
  const match = String(url).match(/\/c\/pay\/(cs_(?:test|live)_[^#?]+)/);
  return match ? match[1] : "";
}

function assertConfig() {
  if (!checkoutUrl) {
    console.log("⚠️ Stripe test checkout skipped: FF_TEST_CHECKOUT_URL is not set.");
    process.exit(0);
  }

  if (
    checkoutUrl.includes("YOUR_TEST_SESSION") ||
    checkoutUrl.includes("cs_test_YOUR") ||
    checkoutUrl.endsWith("cs_test_")
  ) {
    console.log("⚠️ Stripe test checkout skipped: placeholder FF_TEST_CHECKOUT_URL was provided.");
    process.exit(0);
  }

  if (!checkoutUrl.includes("checkout.stripe.com") || !checkoutUrl.includes("cs_test")) {
    throw new Error(
      "Refusing to run. FF_TEST_CHECKOUT_URL must be a Stripe test-mode hosted Checkout URL containing cs_test."
    );
  }

  if (!stripeSecretKey.startsWith("sk_test_")) {
    throw new Error(
      "STRIPE_SECRET_KEY must be exported in this same shell. The verifier needs it to poll the test Checkout Session if Stripe does not redirect immediately."
    );
  }
}

async function debugCheckoutPage(page, label) {
  const frameSummaries = [];

  for (const frame of page.frames()) {
    const inputs = await frame
      .locator("input, textarea, select, button")
      .evaluateAll((nodes) =>
        nodes.slice(0, 90).map((node) => ({
          tag: node.tagName.toLowerCase(),
          type: node.getAttribute("type") || "",
          name: node.getAttribute("name") || "",
          id: node.getAttribute("id") || "",
          autocomplete: node.getAttribute("autocomplete") || "",
          placeholder: node.getAttribute("placeholder") || "",
          ariaLabel: node.getAttribute("aria-label") || "",
          checked: node instanceof HTMLInputElement ? node.checked : undefined,
          disabled:
            node instanceof HTMLButtonElement ||
            node instanceof HTMLInputElement ||
            node instanceof HTMLSelectElement ||
            node instanceof HTMLTextAreaElement
              ? node.disabled
              : undefined,
          text: (node.textContent || "").replace(/\s+/g, " ").trim().slice(0, 120),
        }))
      )
      .catch(() => []);

    frameSummaries.push({
      url: frame.url(),
      name: frame.name(),
      inputs,
    });
  }

  const bodyText = await page
    .locator("body")
    .innerText()
    .catch(() => "");

  await page.screenshot({
    path: `${outDir}/${label}.png`,
    fullPage: true,
  });

  await writeText(`${label}.txt`, bodyText);

  await writeJson(label, {
    url: page.url(),
    title: await page.title().catch(() => ""),
    bodyPreview: bodyText.slice(0, 3000),
    frames: frameSummaries,
    checkedAt: new Date().toISOString(),
  });
}

async function fillFirstVisible(pageOrFrame, candidates, value, label) {
  const errors = [];

  for (const selector of candidates) {
    const locator = pageOrFrame.locator(selector).first();

    try {
      await locator.waitFor({ state: "visible", timeout: 2500 });
      await locator.fill(value, { timeout: 7000 });
      console.log(`✅ filled ${label}: ${selector}`);
      return true;
    } catch (error) {
      errors.push(`${selector}: ${error.message}`);
    }
  }

  return false;
}

async function fillAcrossFrames(page, candidates, value, label) {
  if (await fillFirstVisible(page, candidates, value, label)) return true;

  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    if (await fillFirstVisible(frame, candidates, value, label)) return true;
  }

  return false;
}

async function selectAcrossFrames(page, candidates, value, label) {
  for (const frameOrPage of [
    page,
    ...page.frames().filter((frame) => frame !== page.mainFrame()),
  ]) {
    for (const selector of candidates) {
      const locator = frameOrPage.locator(selector).first();

      try {
        await locator.waitFor({ state: "visible", timeout: 2000 });
        await locator.selectOption(value, { timeout: 6000 });
        console.log(`✅ selected ${label}: ${selector}`);
        return true;
      } catch {
        // Try next selector.
      }
    }
  }

  return false;
}

async function acceptStripeAgentDisclosure(page) {
  const result = await page.evaluate(() => {
    const clean = (value) =>
      String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const bodyText = clean(document.body.innerText || "");
    const checkboxes = Array.from(document.querySelectorAll("input[type='checkbox']"));
    const matches = [];

    for (const checkbox of checkboxes) {
      const id = checkbox.id || "";
      const label =
        (id && document.querySelector(`label[for="${CSS.escape(id)}"]`)) ||
        checkbox.closest("label") ||
        checkbox.parentElement;

      const nearby = clean(
        [
          label?.textContent,
          checkbox.closest("div")?.textContent,
          checkbox.closest("section")?.textContent,
          checkbox.parentElement?.textContent,
        ].join(" ")
      );

      if (/AI agent|acting on behalf|someone else/i.test(nearby)) {
        checkbox.scrollIntoView({ block: "center", inline: "center" });
        if (!checkbox.checked) checkbox.click();

        matches.push({
          id,
          name: checkbox.getAttribute("name") || "",
          checked: checkbox.checked,
          nearby: nearby.slice(0, 240),
        });
      }
    }

    return {
      bodyHasDisclosure: /AI agent|acting on behalf|someone else/i.test(bodyText),
      found: matches.length > 0,
      checked: matches.some((item) => item.checked),
      matches,
    };
  });

  if (result.found) {
    console.log(`✅ Stripe AI-agent disclosure handled: checked=${result.checked}`);
  } else if (result.bodyHasDisclosure) {
    console.log("⚠️ Stripe AI-agent disclosure text is present, but no checkbox was found.");
  }

  return result;
}

async function clickPayButton(page, label) {
  const candidates = [
    page.getByRole("button", { name: /^pay$/i }).first(),
    page.getByRole("button", { name: /pay|donate|submit|complete|continue/i }).first(),
    page.locator("button[type='submit']").first(),
    page.locator("button:has-text('Pay')").first(),
  ];

  for (const locator of candidates) {
    try {
      await locator.waitFor({ state: "visible", timeout: 5000 });
      await locator.scrollIntoViewIfNeeded().catch(() => {});
      await expect(locator).toBeEnabled({ timeout: 15_000 });
      await locator.click({ timeout: 10_000 });
      console.log(`✅ clicked ${label}`);
      return true;
    } catch {
      // Try next candidate.
    }
  }

  return false;
}

async function fetchStripeSession(sessionId) {
  const response = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sessionId}`, {
    headers: {
      Authorization: `Bearer ${stripeSecretKey}`,
    },
  });

  const data = await response.json().catch(() => ({}));

  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

async function pollStripeSessionComplete(sessionId) {
  let latest = null;

  for (let attempt = 1; attempt <= 24; attempt += 1) {
    latest = await fetchStripeSession(sessionId);

    const status = latest.data?.status || "";
    const paymentStatus = latest.data?.payment_status || "";

    console.log(
      `Stripe session poll ${attempt}/24: http=${latest.status} status=${status || "n/a"} payment_status=${paymentStatus || "n/a"}`
    );

    if (latest.ok && (status === "complete" || paymentStatus === "paid")) {
      return {
        ...latest,
        complete: true,
        attempt,
      };
    }

    await new Promise((resolve) => setTimeout(resolve, 5000));
  }

  return {
    ...(latest || {}),
    complete: false,
    reason: "Stripe session did not become complete/paid before timeout.",
  };
}

async function run() {
  assertConfig();

  const sessionId = extractCheckoutSessionId(checkoutUrl);
  if (!sessionId) {
    throw new Error("Could not extract cs_test session id from FF_TEST_CHECKOUT_URL.");
  }

  await ensureOutDir();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1100 },
    locale: "en-US",
  });

  try {
    const page = await context.newPage();
    page.setDefaultTimeout(35_000);

    await page.goto(checkoutUrl, { waitUntil: "domcontentloaded", timeout: 90_000 });
    await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});
    await page.waitForTimeout(2500);

    await debugCheckoutPage(page, "stripe-checkout-before-fill");

    const initialText = await page
      .locator("body")
      .innerText()
      .catch(() => "");
    if (/expired|no longer available|already been completed|session expired/i.test(initialText)) {
      throw new Error(
        "Stripe Checkout session is expired/completed. Generate a fresh cs_test URL and rerun."
      );
    }

    await page
      .getByText(/Card/i)
      .first()
      .click({ timeout: 5000 })
      .catch(() => {});

    const emailOk = await fillAcrossFrames(
      page,
      [
        "input[type='email']",
        "input[name='email']",
        "input[autocomplete='email']",
        "input[placeholder*='email' i]",
        "input[aria-label*='email' i]",
      ],
      "qa+stripe-test@getfuturefunded.com",
      "email"
    );

    const cardNumberOk = await fillAcrossFrames(
      page,
      [
        "input[name='cardNumber']",
        "input[name='cardnumber']",
        "input[autocomplete='cc-number']",
        "input[placeholder*='1234']",
        "input[aria-label*='card number' i]",
      ],
      "4242424242424242",
      "card number"
    );

    const expOk = await fillAcrossFrames(
      page,
      [
        "input[name='cardExpiry']",
        "input[name='exp-date']",
        "input[name='expiry']",
        "input[autocomplete='cc-exp']",
        "input[placeholder*='MM']",
        "input[aria-label*='expiration' i]",
        "input[aria-label*='expiry' i]",
      ],
      "1234",
      "expiry"
    );

    const cvcOk = await fillAcrossFrames(
      page,
      [
        "input[name='cardCvc']",
        "input[name='cvc']",
        "input[autocomplete='cc-csc']",
        "input[placeholder*='CVC' i]",
        "input[aria-label*='CVC' i]",
        "input[aria-label*='security' i]",
      ],
      "123",
      "cvc"
    );

    const billingNameOk = await fillAcrossFrames(
      page,
      [
        "input[name='billingName']",
        "input[name='cardholderName']",
        "input[autocomplete='cc-name']",
        "input[placeholder*='Full name' i]",
        "input[aria-label*='cardholder' i]",
        "input[aria-label*='name' i]",
      ],
      "FutureFunded QA",
      "cardholder name"
    );

    await selectAcrossFrames(
      page,
      [
        "select[name='billingCountry']",
        "select[autocomplete='billing country']",
        "select[aria-label*='Country' i]",
      ],
      "US",
      "billing country"
    );

    const postalOk = await fillAcrossFrames(
      page,
      [
        "input[name='billingPostalCode']",
        "input[name='postal']",
        "input[name='postalCode']",
        "input[autocomplete='billing postal-code']",
        "input[autocomplete='postal-code']",
        "input[placeholder*='ZIP' i]",
        "input[aria-label*='ZIP' i]",
        "input[aria-label*='postal' i]",
      ],
      "78754",
      "postal"
    );

    const requiredOk = {
      emailOk,
      cardNumberOk,
      expOk,
      cvcOk,
      billingNameOk,
      postalOk,
    };

    if (!Object.values(requiredOk).every(Boolean)) {
      await debugCheckoutPage(page, "stripe-checkout-field-detection-failed");
      throw new Error(`Could not fill all required Stripe fields: ${JSON.stringify(requiredOk)}`);
    }

    await acceptStripeAgentDisclosure(page);

    const firstClick = await clickPayButton(page, "initial Pay button");
    if (!firstClick) {
      throw new Error("Could not find enabled Stripe Pay button.");
    }

    await page.waitForTimeout(5000);

    const disclosureAfterFirstClick = await acceptStripeAgentDisclosure(page);
    if (disclosureAfterFirstClick.found || disclosureAfterFirstClick.bodyHasDisclosure) {
      await clickPayButton(page, "Pay button after AI disclosure").catch(() => {});
    }

    await page.waitForTimeout(8000);

    const stripeSession = await pollStripeSessionComplete(sessionId);

    await page
      .waitForURL(/success|thank|complete|return|checkout\/complete/i, {
        timeout: 15_000,
      })
      .catch(() => {});

    const finalUrl = page.url();
    const finalBody = await page
      .locator("body")
      .innerText()
      .catch(() => "");

    const finalHost = (() => {
      try {
        return new URL(finalUrl).hostname;
      } catch {
        return "";
      }
    })();

    const stillOnStripeCheckout =
      finalHost === "checkout.stripe.com" || finalUrl.includes("checkout.stripe.com/c/pay/");

    const browserOk =
      !stillOnStripeCheckout &&
      (/success|thank-you|thank_you|payment-success|donation-success/i.test(finalUrl) ||
        /thank you for your donation|payment successful|donation complete|donation received|checkout complete/i.test(
          finalBody
        ));

    const stripeComplete =
      stripeSession?.complete === true ||
      stripeSession?.data?.status === "complete" ||
      stripeSession?.data?.payment_status === "paid";

    const ok = browserOk || stripeComplete;

    await debugCheckoutPage(page, "stripe-checkout-after-submit");

    await writeJson("stripe-test-checkout", {
      ok,
      browserOk,
      skipped: false,
      checkoutUrl: redactCheckoutUrl(checkoutUrl),
      sessionId: sessionId.replace(/cs_test_[^#?]*/g, "cs_test_REDACTED"),
      stripeSession,
      finalUrl,
      checkedAt: new Date().toISOString(),
      bodyPreview: finalBody.slice(0, 1800),
    });

    if (!ok) {
      throw new Error(
        [
          "Stripe test checkout did not reach a recognizable success state.",
          `Final URL: ${finalUrl}`,
          `Stripe session: ${JSON.stringify(stripeSession).slice(0, 1400)}`,
          `Debug artifacts: ${outDir}/stripe-checkout-after-submit.json and .png`,
        ].join("\n")
      );
    }

    console.log("✅ Stripe test checkout completion passed.");
  } finally {
    await context.close();
    await browser.close();
  }
}

run();
