import { expect, Page, test } from "@playwright/test";

const BASE_URL = (process.env.FF_BASE_URL || "https://getfuturefunded.com").replace(/\/$/, "");
const HOME_URL = `${BASE_URL}/platform/`;
const CAMPAIGN_URL = `${BASE_URL}/c/connect-atx-elite`;

const BAD_COPY = /\b(?:None|undefined|null|NaN|Lorem|TODO)\b|Choose None/i;

async function expectNoBadCopy(page: Page) {
  const copySurface = await page.evaluate(() => {
    const clone = document.body.cloneNode(true) as HTMLElement;

    clone.querySelectorAll("script, style, noscript, template").forEach((node) => node.remove());

    const visibleBodyText = clone.innerText || clone.textContent || "";

    const metaText = [
      document.title,
      ...Array.from(
        document.querySelectorAll(
          "meta[name='description'], meta[property='og:title'], meta[property='og:description']"
        )
      ).map((node) => node.getAttribute("content") || ""),
    ].join("\n");

    return `${visibleBodyText}\n${metaText}`;
  });

  expect(copySurface).not.toMatch(BAD_COPY);
}

async function collectConsoleBreakers(page: Page) {
  const errors: string[] = [];

  page.on("pageerror", (error) => {
    errors.push(error.message);
  });

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;

    const text = msg.text();
    const allowedNoise = [
      "favicon",
      "chrome-extension",
      ".well-known/appspecific/com.chrome.devtools.json",
      "Executing inline script violates the following Content Security Policy",
      "Applying inline style violates the following Content Security Policy",
    ];

    if (!allowedNoise.some((fragment) => text.includes(fragment))) {
      errors.push(text);
    }
  });

  return errors;
}

async function expectNoHorizontalOverflow(page: Page) {
  const htmlScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  expect(htmlScrollWidth).toBeLessThanOrEqual(viewportWidth + 2);
}

test.describe("FutureFunded public templates UX gates", () => {
  test("homepage template passes desktop UX gate", async ({ page }) => {
    const errors = await collectConsoleBreakers(page);

    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.goto(HOME_URL, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    await expect(page).toHaveTitle(/FutureFunded/i);
    await expect(page.locator('html[data-ff-template="getfuturefunded-home-2026"]')).toHaveCount(1);
    await expect(page.locator("[data-ff-home-root]")).toHaveCount(1);
    await expect(
      page.locator("[data-ff-header][data-ff-home-header], [data-ff-home-header]")
    ).toHaveCount(1);

    await expect(
      page.getByRole("heading", { name: /Fundraising pages that make your team look ready/i })
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: /Start fundraiser|Start a fundraiser/i }).first()
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /View campaign demo|See live demo/i }).first()
    ).toBeVisible();

    await expect(page.getByText(/Youth teams/i).first()).toBeVisible();
    await expect(
      page.getByText(/Sponsor inventory|Sponsor monetization layer/i).first()
    ).toBeVisible();
    await expect(page.getByText(/Community fundraising should feel secure/i).first()).toBeVisible();

    await expectNoBadCopy(page);
    expect(errors, `Console/page errors:\n${errors.join("\n")}`).toEqual([]);
  });

  test("homepage template passes mobile UX gate", async ({ page }) => {
    const errors = await collectConsoleBreakers(page);

    await page.setViewportSize({ width: 390, height: 1200 });
    await page.goto(HOME_URL, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    await expect(page.locator("[data-ff-home-root]")).toHaveCount(1);
    await expect(
      page.getByRole("heading", { name: /Fundraising pages that make your team look ready/i })
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Start fundraiser|Start a fundraiser/i }).first()
    ).toBeVisible();

    await expectNoHorizontalOverflow(page);
    await expectNoBadCopy(page);
    expect(errors, `Console/page errors:\n${errors.join("\n")}`).toEqual([]);
  });

  test("campaign template passes desktop UX gate", async ({ page }) => {
    const errors = await collectConsoleBreakers(page);

    await page.setViewportSize({ width: 1440, height: 1200 });
    await page.goto(CAMPAIGN_URL, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    await expect(page.locator("[data-ff-campaign-page]")).toHaveCount(1);
    await expect(page.locator("#campaign-hero")).toBeVisible();
    await expect(page.locator("[data-ff-campaign-main]")).toHaveCount(1);

    await expect(page.getByRole("heading", { name: /Fuel the season/i }).first()).toBeVisible();
    await expect(page.getByText(/Support the season with care/i).first()).toBeVisible();
    await expect(page.getByText(/Fundraising progress/i).first()).toBeVisible();
    await expect(page.getByText(/What support covers/i).first()).toBeVisible();
    await expect(page.getByText(/Sponsors and recognition/i).first()).toBeVisible();

    await expect(page.locator('[data-ff-media-bound="true"] img').first()).toBeVisible();
    expect(await page.locator('[data-ff-media-bound="true"] img').count()).toBeGreaterThan(1);

    await expectNoBadCopy(page);
    expect(errors, `Console/page errors:\n${errors.join("\n")}`).toEqual([]);
  });

  test("campaign template passes mobile UX gate", async ({ page }) => {
    const errors = await collectConsoleBreakers(page);

    await page.setViewportSize({ width: 390, height: 1400 });
    await page.goto(CAMPAIGN_URL, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    await expect(page.locator("#campaign-hero")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Fuel the season/i }).first()).toBeVisible();
    await expect(
      page
        .getByRole("button", { name: /Donate/i })
        .or(page.getByRole("link", { name: /Donate/i }))
        .first()
    ).toBeVisible();
    await expect(page.locator('[data-ff-media-bound="true"] img').first()).toBeVisible();

    await expectNoHorizontalOverflow(page);
    await expectNoBadCopy(page);
    expect(errors, `Console/page errors:\n${errors.join("\n")}`).toEqual([]);
  });

  test("campaign sponsor and FAQ interactions do not break", async ({ page }) => {
    const errors = await collectConsoleBreakers(page);

    await page.setViewportSize({ width: 1280, height: 1000 });
    await page.goto(CAMPAIGN_URL, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle").catch(() => {});

    const sponsorCta = page
      .getByRole("link", { name: /Sponsor|Become a sponsor|Choose/i })
      .or(page.getByRole("button", { name: /Sponsor|Become a sponsor|Choose/i }))
      .first();

    await expect(sponsorCta).toBeVisible();

    const faqSummary = page.locator("details summary").first();
    if ((await faqSummary.count()) > 0) {
      await faqSummary.click();
      await expect(faqSummary).toBeVisible();
    }

    await expectNoBadCopy(page);
    expect(errors, `Console/page errors:\n${errors.join("\n")}`).toEqual([]);
  });
});
