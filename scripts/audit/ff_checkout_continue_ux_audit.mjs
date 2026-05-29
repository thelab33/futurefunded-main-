import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const base = process.env.FF_BASE_URL || "http://127.0.0.1:5000";
const slug = process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";
const url = `${base}/c/${slug}?checkout_direct_audit=${Date.now()}`;

const outDir = path.resolve("audit_outputs/checkout-continue-ux");
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

const checkoutRequests = [];
const checkoutResponses = [];
const consoleMessages = [];
const pageErrors = [];

page.on("console", (msg) => consoleMessages.push({ type: msg.type(), text: msg.text() }));
page.on("pageerror", (err) => pageErrors.push(String(err?.stack || err?.message || err)));

page.on("request", (req) => {
  if (req.url().includes("/checkout/session")) {
    checkoutRequests.push({
      method: req.method(),
      url: req.url(),
      postData: req.postData(),
    });
  }
});

page.on("response", async (res) => {
  if (res.url().includes("/checkout/session")) {
    let bodyPreview = "";
    try {
      bodyPreview = (await res.text()).slice(0, 1200);
    } catch {
      bodyPreview = "";
    }

    checkoutResponses.push({
      status: res.status(),
      url: res.url(),
      bodyPreview,
    });
  }
});

async function screenshot(label) {
  await page.screenshot({
    path: path.join(outDir, `${label}.png`),
    fullPage: true,
  }).catch(() => null);
}

await page.goto(url, { waitUntil: "networkidle" });

const assetProof = await page.evaluate(async () => {
  const directScript = document.querySelector("script[data-ff-checkout-direct-js]");
  const directUrl = directScript?.src || null;

  let directHasMarker = false;
  let directHasXhrV2 = false;

  if (directUrl) {
    const js = await fetch(directUrl).then((res) => res.text()).catch(() => "");
    directHasMarker = js.includes("FF_CHECKOUT_DIRECT_V2_START");
    directHasXhrV2 = js.includes("checkout-direct-v2") && js.includes("XMLHttpRequest");
  }

  return {
    directUrl,
    directHasMarker,
    directHasXhrV2,
    directRuntimeInstalled: window.FutureFundedCheckoutDirect?.version === "checkout-direct-v2",
  };
});

const opened = await page.evaluate(() => {
  const trigger =
    document.querySelector("[data-ff-open-checkout]") ||
    document.querySelector("[data-ff-donate-trigger]");

  if (!trigger) return false;

  trigger.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, cancelable: true }));
  trigger.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  return true;
});

if (!opened) {
  await screenshot("fail-no-donate-trigger");
  throw new Error("Could not dispatch donate trigger.");
}

await page.waitForTimeout(800);

const modalProof = await page.evaluate(() => {
  const modal =
    document.querySelector("[data-ff-embedded-checkout-shell]") ||
    document.querySelector(".ff-embeddedCheckout") ||
    document.querySelector(".ff-checkoutModal");

  const email =
    modal?.querySelector("[data-ff-checkout-donor-email]") ||
    modal?.querySelector("input[type='email']");

  const button =
    modal?.querySelector("[data-ff-start-embedded-checkout]") ||
    modal?.querySelector(".ff-checkoutContinue");

  return {
    modalExists: Boolean(modal),
    modalHidden: modal ? modal.hidden : null,
    modalAriaHidden: modal?.getAttribute("aria-hidden") || null,
    emailExists: Boolean(email),
    buttonExists: Boolean(button),
    buttonText: button?.textContent?.trim() || null,
    buttonOwned: button?.getAttribute("data-ff-checkout-direct-owned") || null,
  };
});

if (!modalProof.modalExists || !modalProof.emailExists || !modalProof.buttonExists) {
  await screenshot("fail-modal-proof");
  throw new Error(`Modal proof failed: ${JSON.stringify(modalProof)}`);
}

await page.evaluate(() => {
  const modal =
    document.querySelector("[data-ff-embedded-checkout-shell]") ||
    document.querySelector(".ff-embeddedCheckout") ||
    document.querySelector(".ff-checkoutModal");

  const email =
    modal?.querySelector("[data-ff-checkout-donor-email]") ||
    modal?.querySelector("input[type='email']");

  if (email) {
    email.value = `receipt+${Date.now()}@example.com`;
    email.dispatchEvent(new Event("input", { bubbles: true }));
    email.dispatchEvent(new Event("change", { bubbles: true }));
  }
});

await page.waitForTimeout(300);

const waitForCheckout = page
  .waitForResponse((res) => res.url().includes("/checkout/session"), { timeout: 8000 })
  .catch(() => null);

const clicked = await page.evaluate(() => {
  const modal =
    document.querySelector("[data-ff-embedded-checkout-shell]") ||
    document.querySelector(".ff-embeddedCheckout") ||
    document.querySelector(".ff-checkoutModal");

  const button =
    modal?.querySelector("[data-ff-start-embedded-checkout]") ||
    modal?.querySelector(".ff-checkoutContinue");

  if (!button) return false;

  button.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, cancelable: true }));
  button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  return true;
});

const checkoutResponse = await waitForCheckout;
await page.waitForTimeout(800);

const joinedPostData = checkoutRequests.map((req) => req.postData || "").join("\n");
const sponsorPollutionPatterns = [
  "sponsor_intake",
  "business_name",
  "contact_email",
  "recognition_name",
  "package_amount",
  "package_label",
  "\"package\"",
];

const sponsorPayloadPollution = sponsorPollutionPatterns.filter((pattern) =>
  joinedPostData.includes(pattern)
);

const successfulCheckoutResponse = checkoutResponses.some(
  (res) => res.status >= 200 && res.status < 300
);

const result = {
  ok:
    assetProof.directHasMarker &&
    assetProof.directHasXhrV2 &&
    assetProof.directRuntimeInstalled &&
    clicked &&
    checkoutRequests.length > 0 &&
    successfulCheckoutResponse &&
    sponsorPayloadPollution.length === 0,
  url,
  assetProof,
  modalProof,
  clicked,
  checkoutRequestCount: checkoutRequests.length,
  sponsorPayloadPollution,
  checkoutRequests,
  checkoutResponses,
  sawCheckoutResponseViaWait: Boolean(checkoutResponse),
  currentUrl: page.url(),
  pageErrors,
  consoleMessages: consoleMessages.slice(-50),
};

fs.writeFileSync(
  path.join(outDir, "latest-checkout-continue-ux.json"),
  JSON.stringify(result, null, 2)
);

console.log(JSON.stringify(result, null, 2));

await screenshot(result.ok ? "pass-checkout-direct" : "fail-checkout-direct");
await browser.close();

if (!result.ok) process.exitCode = 1;
