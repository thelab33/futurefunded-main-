import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = (process.env.FF_BASE_URL || process.argv[2] || "http://127.0.0.1:5000").replace(
  /\/$/,
  ""
);
const homepageUrl = process.env.HOMEPAGE_URL || `${baseUrl}/platform/`;
const campaignUrl = process.env.CAMPAIGN_URL || `${baseUrl}/c/connect-atx-elite`;
const outDir = "artifacts/release-proof";

async function writeJson(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function installAnalyticsCollector(page) {
  await page.addInitScript(() => {
    const key = "__ffAnalyticsEventsPersistent";

    const readPersistent = () => {
      try {
        return JSON.parse(window.localStorage.getItem(key) || "[]");
      } catch {
        return [];
      }
    };

    const writePersistent = (events) => {
      try {
        window.localStorage.setItem(key, JSON.stringify(events));
      } catch {
        // Ignore storage failures; in-memory capture still works.
      }
    };

    window.__ffAnalyticsEvents = readPersistent();

    const record = (source, payload) => {
      const event = {
        source,
        payload,
        at: Date.now(),
        path: window.location.pathname,
      };

      window.__ffAnalyticsEvents.push(event);

      const persistent = readPersistent();
      persistent.push(event);
      writePersistent(persistent);
    };

    window.dataLayer = window.dataLayer || [];
    const originalPush = window.dataLayer.push.bind(window.dataLayer);
    window.dataLayer.push = (...args) => {
      record("dataLayer.push", args);
      return originalPush(...args);
    };

    window.gtag = (...args) => record("gtag", args);
    window.plausible = (...args) => record("plausible", args);

    window.posthog = window.posthog || {};
    window.posthog.capture = (...args) => record("posthog.capture", args);

    const originalBeacon = navigator.sendBeacon?.bind(navigator);
    navigator.sendBeacon = (url, data) => {
      record("sendBeacon", { url: String(url), data: String(data || "") });
      return originalBeacon ? originalBeacon(url, data) : true;
    };

    const originalFetch = window.fetch.bind(window);
    window.fetch = (...args) => {
      const url = String(args[0]?.url || args[0] || "");
      if (/analytics|collect|events|plausible|posthog|gtag|google-analytics/i.test(url)) {
        record("fetch", { url });
      }
      return originalFetch(...args);
    };
  });
}

async function getEvents(page) {
  return page.evaluate(() => {
    try {
      const persistent = JSON.parse(
        window.localStorage.getItem("__ffAnalyticsEventsPersistent") || "[]"
      );

      if (persistent.length) return persistent;
    } catch {
      // Fall back below.
    }

    return window.__ffAnalyticsEvents || [];
  });
}

async function resetEvents(page) {
  await page.evaluate(() => {
    window.__ffAnalyticsEvents = [];

    try {
      window.localStorage.removeItem("__ffAnalyticsEventsPersistent");
    } catch {
      // Ignore storage failures.
    }
  });
}

async function safeClick(page, selectors, label) {
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    if ((await loc.count()) > 0 && (await loc.isVisible().catch(() => false))) {
      await loc.scrollIntoViewIfNeeded().catch(() => {});
      await loc.click({ timeout: 5000 }).catch(async () => {
        await loc.dispatchEvent("click");
      });
      console.log(`✅ clicked ${label}: ${selector}`);
      return true;
    }
  }

  console.log(`⚠️ no visible target for ${label}`);
  return false;
}

async function runPage(browser, kind, url) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    bypassCSP: true,
  });

  const page = await context.newPage();
  await installAnalyticsCollector(page);

  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45_000 });
  if (!response || !response.ok()) {
    throw new Error(`${kind} failed to load: ${response?.status()}`);
  }

  await page.waitForLoadState("networkidle").catch(() => {});
  await resetEvents(page);

  if (kind === "homepage") {
    await safeClick(
      page,
      ["[data-ff-home-primary-cta]", "[data-ff-home-launch-cta]"],
      "homepage launch CTA"
    );
    await safeClick(
      page,
      ["[data-ff-home-demo-cta]", "[data-ff-home-campaign-preview-cta]"],
      "homepage demo CTA"
    );
  } else {
    await safeClick(
      page,
      [
        "#campaign-hero [data-ff-open-checkout]",
        "[data-ff-open-checkout]",
        "[data-ff-checkout-trigger]",
      ],
      "campaign donate CTA"
    );
    await safeClick(
      page,
      ["[data-ff-open-sponsor]", "[data-ff-sponsor-trigger]", "[data-ff-sponsor-cta]"],
      "campaign sponsor CTA"
    );
    await safeClick(
      page,
      ["[data-ff-qr-trigger]", "[data-ff-share-trigger]"],
      "campaign share CTA"
    );
  }

  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForTimeout(500);

  const events = await getEvents(page);
  await context.close();

  return { kind, url, eventCount: events.length, events };
}

const browser = await chromium.launch({ headless: true });

try {
  const homepage = await runPage(browser, "homepage", homepageUrl);
  const campaign = await runPage(browser, "campaign", campaignUrl);

  const payload = {
    ok: true,
    baseUrl,
    checkedAt: new Date().toISOString(),
    homepage,
    campaign,
    note: "This verifies analytics instrumentation surfaces can receive launch-critical CTA events. If no analytics provider is installed, eventCount may be zero and should be treated as instrumentation pending.",
  };

  const failures = [];

  if (homepage.eventCount < 1) {
    failures.push("Homepage produced zero analytics events.");
  }

  if (campaign.eventCount < 1) {
    failures.push("Campaign produced zero analytics events.");
  }

  payload.ok = failures.length === 0;
  payload.failures = failures;

  await writeJson("analytics-events", payload);

  if (failures.length) {
    throw new Error(`Analytics event verification failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Analytics events verified.");
} finally {
  await browser.close();
}
