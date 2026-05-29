import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = (
  process.env.FF_BASE_URL ||
  process.argv[2] ||
  "https://getfuturefunded.com"
).replace(/\/$/, "");
const homepageUrl = process.env.HOMEPAGE_URL || `${baseUrl}/platform/`;
const campaignUrl = process.env.CAMPAIGN_URL || `${baseUrl}/c/connect-atx-elite`;
const outDir = "artifacts/conversion-proof";

const requiredEvents = [
  "ff_checkout_started",
  "ff_donation_amount_selected",
  "ff_sponsor_interest_click",
  "ff_share_click",
  "ff_share_copy_click",
  "ff_mobile_conversion_click",
];

async function writeJson(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function installHardCollector(page) {
  await page.addInitScript(() => {
    window.__ffQaErrors = [];
    window.__ffQaEvents = [];

    const capture = (source, payload) => {
      window.__ffQaEvents.push({
        source,
        payload,
        at: Date.now(),
        path: window.location.pathname,
      });
    };

    window.addEventListener("ff:analytics", (event) => {
      capture("ff:analytics", event.detail);
    });

    window.addEventListener("error", (event) => {
      window.__ffQaErrors.push({
        type: "error",
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
      });
    });

    window.addEventListener("unhandledrejection", (event) => {
      window.__ffQaErrors.push({
        type: "unhandledrejection",
        message: String(event.reason?.message || event.reason || ""),
      });
    });

    const key = "__ffAnalyticsEventsPersistent";
    try {
      window.localStorage.removeItem(key);
      window.__ffAnalyticsEvents = [];
    } catch {
      // no-op
    }
  });
}

function allowedConsoleNoise(text) {
  return ["favicon", ".well-known/appspecific/com.chrome.devtools.json", "chrome-extension"].some(
    (fragment) => text.includes(fragment)
  );
}

async function safeClick(page, selectors, label) {
  const attempts = [];

  for (const selector of selectors) {
    const loc = page.locator(selector);
    const total = await loc.count().catch(() => 0);

    for (let i = 0; i < total; i += 1) {
      const item = loc.nth(i);
      const visible = await item.isVisible().catch(() => false);

      if (!visible) continue;

      try {
        await item.scrollIntoViewIfNeeded({ timeout: 3000 }).catch(() => {});
        await item.click({ timeout: 5000 });
        console.log(`✅ ${label}: ${selector}${total > 1 ? ` [${i}]` : ""}`);
        return { ok: true, selector, index: i };
      } catch (error) {
        attempts.push(`${selector}${total > 1 ? ` [${i}]` : ""}: ${error.message}`);
      }
    }
  }

  throw new Error(`Could not click ${label}.\n${attempts.join("\n")}`);
}

async function assertAnalyticsBridgeReady(page, label) {
  const status = await page.evaluate(() => ({
    hasFfTrack: typeof window.ffTrack === "function",
    hasPersistentStore: Boolean(window.localStorage),
    scriptLoaded: Boolean(
      Array.from(document.scripts).find((script) =>
        String(script.src || "").includes("ff-analytics.js")
      )
    ),
    currentPath: location.pathname,
  }));

  if (!status.hasFfTrack) {
    throw new Error(
      `${label}: ff-analytics bridge is not active. ` +
        `scriptLoaded=${status.scriptLoaded}; path=${status.currentPath}. ` +
        `Deploy the latest ff-analytics.js and clear CDN/browser cache before running public conversion QA.`
    );
  }

  return status;
}

async function getQaState(page) {
  return page.evaluate(() => {
    let persistent = [];

    try {
      persistent = JSON.parse(localStorage.getItem("__ffAnalyticsEventsPersistent") || "[]");
    } catch {
      persistent = [];
    }

    return {
      events: [
        ...(window.__ffQaEvents || []),
        ...(window.__ffAnalyticsEvents || []),
        ...persistent,
      ],
      errors: window.__ffQaErrors || [],
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      url: location.href,
    };
  });
}

function eventNames(events) {
  return new Set(
    events
      .map(
        (entry) =>
          entry?.payload?.event ||
          entry?.payload?.payload?.event ||
          entry?.payload?.payload?.eventName
      )
      .filter(Boolean)
  );
}

async function auditSmallScreens(browser) {
  const sizes = [
    { width: 320, height: 980 },
    { width: 360, height: 980 },
    { width: 390, height: 1100 },
  ];

  const audits = [];

  for (const viewport of sizes) {
    const context = await browser.newContext({ viewport, bypassCSP: true });
    const page = await context.newPage();

    await page.goto(campaignUrl, { waitUntil: "domcontentloaded", timeout: 45_000 });
    await page.waitForLoadState("networkidle").catch(() => {});

    const audit = await page.evaluate(() => {
      const offenders = Array.from(document.body.querySelectorAll("*"))
        .map((el) => {
          const rect = el.getBoundingClientRect();
          return {
            tag: el.tagName.toLowerCase(),
            id: el.id,
            className: String(el.className || ""),
            width: rect.width,
            right: rect.right,
            text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80),
          };
        })
        .filter((item) => item.right > window.innerWidth + 2 && item.width > 0)
        .slice(0, 10);

      return {
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        offenders,
      };
    });

    audits.push({ viewport, ...audit });
    await context.close();
  }

  return audits;
}

async function run() {
  const consoleErrors = [];

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    bypassCSP: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  await context.route("**/*", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = request.url();

    const isPaymentMutation =
      !["GET", "HEAD", "OPTIONS"].includes(method) &&
      /(checkout|payment|payments|donation|donate|stripe|paypal|session|intent)/i.test(url);

    if (isPaymentMutation) {
      return route.fulfill({
        status: 418,
        contentType: "application/json",
        body: JSON.stringify({
          blockedBy: "FutureFunded conversion QA",
          safe: true,
        }),
      });
    }

    return route.continue();
  });

  const page = await context.newPage();

  page.on("console", (msg) => {
    if (msg.type() === "error" && !allowedConsoleNoise(msg.text())) {
      consoleErrors.push(msg.text());
    }
  });

  await installHardCollector(page);

  await page.goto(`${homepageUrl}?qa_v=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForLoadState("networkidle").catch(() => {});
  const homepageBridge = await assertAnalyticsBridgeReady(page, "homepage");

  await safeClick(
    page,
    [
      "[data-ff-home-demo-cta]",
      "[data-ff-home-campaign-preview-cta]",
      "a[href*='connect-atx-elite']",
    ],
    "homepage campaign/demo CTA click"
  );

  await page.goto(`${campaignUrl}?qa_v=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await page.waitForLoadState("networkidle").catch(() => {});
  const campaignBridge = await assertAnalyticsBridgeReady(page, "campaign");

  for (const amount of ["25", "50", "100"]) {
    await safeClick(page, [`[data-ff-donation-amount="${amount}"]`], `amount selection ${amount}`);
  }

  const customAmount = page
    .locator("[data-ff-custom-amount], #custom-amount, input[name='custom_amount']")
    .first();
  if ((await customAmount.count()) > 0 && (await customAmount.isVisible().catch(() => false))) {
    await customAmount.fill("123");
    console.log("✅ custom amount interaction");
  }

  await safeClick(
    page,
    [
      "#campaign-hero [data-ff-open-checkout]",
      "[data-ff-open-checkout]",
      "[data-ff-checkout-trigger]",
      "[data-ff-donate-cta]",
    ],
    "donation CTA / checkout start"
  );

  await safeClick(
    page,
    [
      "[data-ff-open-sponsor]",
      "[data-ff-sponsor-trigger]",
      "[data-ff-sponsor-cta]",
      "[data-ff-sponsor-package]",
    ],
    "sponsor interest click"
  );

  await safeClick(page, ["[data-ff-qr-trigger]", "[data-ff-share-trigger]"], "share click");

  await safeClick(
    page,
    ["[data-ff-copy-share-url]", "[data-ff-copy-link]", "[data-ff-copy-trigger]"],
    "copy-link usage"
  );

  const mobile = await browser.newContext({
    viewport: { width: 390, height: 1000 },
    bypassCSP: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  const mobilePage = await mobile.newPage();
  await installHardCollector(mobilePage);
  await mobilePage.goto(`${campaignUrl}?qa_v=${Date.now()}`, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });
  await mobilePage.waitForLoadState("networkidle").catch(() => {});
  const mobileBridge = await assertAnalyticsBridgeReady(mobilePage, "mobile campaign");

  await safeClick(
    mobilePage,
    [".ff-mobileDonateBar a", "[data-ff-mobile-rail] a", "[data-ff-mobile-conversion-rail] a"],
    "mobile conversion behavior"
  );

  const desktopState = await getQaState(page);
  const mobileState = await getQaState(mobilePage);
  const smallScreens = await auditSmallScreens(browser);

  const allEvents = [...desktopState.events, ...mobileState.events];
  const names = eventNames(allEvents);

  const missingEvents = requiredEvents.filter((name) => !names.has(name));

  const smallScreenFailures = smallScreens.filter((item) => item.scrollWidth > item.innerWidth + 2);

  const failures = [
    ...missingEvents.map((name) => `Missing event: ${name}`),
    ...consoleErrors.map((message) => `Console error: ${message}`),
    ...desktopState.errors.map((error) => `Page error: ${error.message}`),
    ...mobileState.errors.map((error) => `Mobile page error: ${error.message}`),
    ...smallScreenFailures.map((item) => `Small-screen overflow at ${item.viewport.width}px`),
  ];

  const summary = {
    ok: failures.length === 0,
    baseUrl,
    homepageUrl,
    campaignUrl,
    checkedAt: new Date().toISOString(),
    requiredEvents,
    observedEvents: Array.from(names).sort(),
    eventCount: allEvents.length,
    consoleErrors,
    desktopState,
    mobileState,
    smallScreens,
    bridgeStatus: {
      homepage: homepageBridge,
      campaign: campaignBridge,
      mobileCampaign: mobileBridge,
    },
    failures,
  };

  await writeJson("conversion-behavior", summary);

  await context.close();
  await mobile.close();
  await browser.close();

  if (failures.length) {
    throw new Error(`Conversion behavior QA failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Conversion behavior QA passed.");
  console.log(`Events observed: ${Array.from(names).sort().join(", ")}`);
}

run();
