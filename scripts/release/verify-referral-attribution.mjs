import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = (
  process.env.FF_BASE_URL ||
  process.argv[2] ||
  "https://getfuturefunded.com"
).replace(/\/$/, "");
const campaignPath = "/c/connect-atx-elite";
const outDir = "artifacts/conversion-proof";

const scenarios = [
  {
    name: "facebook",
    referer: "https://www.facebook.com/groups/local-hoops",
    url: `${baseUrl}${campaignPath}?utm_source=facebook&utm_medium=social&utm_campaign=prelaunch_share`,
  },
  {
    name: "instagram",
    referer: "https://www.instagram.com/",
    url: `${baseUrl}${campaignPath}?utm_source=instagram&utm_medium=social&utm_campaign=prelaunch_share`,
  },
  {
    name: "email",
    referer: "https://mail.google.com/",
    url: `${baseUrl}${campaignPath}?utm_source=email&utm_medium=email&utm_campaign=sponsor_outreach`,
  },
  {
    name: "qr",
    referer: "",
    url: `${baseUrl}${campaignPath}?ff_source=qr&ff_ref=gym_flyer&utm_campaign=prelaunch_qr`,
  },
  {
    name: "sponsor",
    referer: "https://example-sponsor.test/",
    url: `${baseUrl}${campaignPath}?utm_source=sponsor&utm_medium=partner&utm_campaign=sponsor_packet`,
  },
];

async function writeJson(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function collectScenario(browser, scenario) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    bypassCSP: true,
    extraHTTPHeaders: scenario.referer ? { Referer: scenario.referer } : {},
  });

  const page = await context.newPage();

  await page.goto(scenario.url, { waitUntil: "domcontentloaded", timeout: 45_000 });
  await page.waitForLoadState("networkidle").catch(() => {});

  const clickTarget = page
    .locator(
      "#campaign-hero [data-ff-open-checkout], [data-ff-open-checkout], [data-ff-share-trigger]"
    )
    .first();
  if ((await clickTarget.count()) > 0) {
    await clickTarget.click({ timeout: 5000 }).catch(() => {});
  }

  await page.waitForTimeout(350);

  const payload = await page.evaluate(() => {
    let persistent = [];

    try {
      persistent = JSON.parse(localStorage.getItem("__ffAnalyticsEventsPersistent") || "[]");
    } catch {
      persistent = [];
    }

    return {
      referrer: document.referrer,
      href: location.href,
      events: [...(window.__ffAnalyticsEvents || []), ...persistent],
    };
  });

  await context.close();

  return {
    scenario,
    ...payload,
  };
}

const browser = await chromium.launch({ headless: true });

try {
  const results = [];

  for (const scenario of scenarios) {
    const result = await collectScenario(browser, scenario);
    results.push(result);
    console.log(`✅ attribution scenario: ${scenario.name}`);
  }

  const topSources = {};

  for (const result of results) {
    for (const event of result.events) {
      const payload = event.payload || {};
      const source =
        payload.utm_source ||
        payload.ff_source ||
        new URL(result.href).searchParams.get("utm_source") ||
        new URL(result.href).searchParams.get("ff_source") ||
        "direct";

      topSources[source] = (topSources[source] || 0) + 1;
    }
  }

  const failures = [];

  for (const result of results) {
    const params = new URL(result.href).searchParams;
    const expectedSource = params.get("utm_source") || params.get("ff_source") || "";

    const hasSource = result.events.some((event) => {
      const payload = event.payload || {};
      return payload.utm_source === expectedSource || payload.ff_source === expectedSource;
    });

    if (!hasSource) {
      failures.push(`Missing attribution source for ${result.scenario.name}`);
    }
  }

  await writeJson("referral-attribution", {
    ok: failures.length === 0,
    baseUrl,
    checkedAt: new Date().toISOString(),
    topSources,
    results,
    failures,
  });

  if (failures.length) {
    throw new Error(`Referral attribution QA failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Referral attribution QA passed.");
  console.log("Top pre-live test sources:", topSources);
} finally {
  await browser.close();
}
