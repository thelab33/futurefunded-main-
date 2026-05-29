import { test, expect } from "@playwright/test";

const BASE = process.env.FF_BASE_URL || "https://getfuturefunded.com";

function isCriticalRuntimeError(text: string): boolean {
  return /ReferenceError|TypeError|SyntaxError|Unhandled|is not defined|Cannot read/i.test(text);
}

test.describe("FutureFunded public UX gates", () => {
  test("platform and campaign load with unified live metrics", async ({ page }) => {
    const criticalErrors: string[] = [];

    page.on("pageerror", (err) => {
      criticalErrors.push(err.message);
    });

    page.on("console", (msg) => {
      const text = msg.text();
      if (msg.type() === "error" && isCriticalRuntimeError(text)) {
        criticalErrors.push(text);
      }
    });

    const platformResponse = await page.goto(`${BASE}/platform/`, {
      waitUntil: "domcontentloaded",
    });

    expect(platformResponse?.ok()).toBeTruthy();

    const platformBody = page.locator("body");

    await expect(platformBody).toContainText("FutureFunded");
    await expect(platformBody).toContainText(/Fundraising pages donors trust/i);
    await expect(platformBody).toContainText("Connect ATX Elite");

    await expect(platformBody).toContainText("$11,859");
    await expect(platformBody).toContainText("$20,000");
    await expect(platformBody).toContainText("59% funded");

    await expect(platformBody).not.toContainText("$5,620");
    await expect(platformBody).not.toContainText("$7,800 goal");
    await expect(platformBody).not.toContainText("72% funded");

    const campaignResponse = await page.goto(`${BASE}/c/connect-atx-elite`, {
      waitUntil: "domcontentloaded",
    });

    expect(campaignResponse?.ok()).toBeTruthy();

    const campaignBody = page.locator("body");

    await expect(campaignBody).toContainText("Fund the season. Build the future.");
    await expect(campaignBody).toContainText("$11,859");
    await expect(campaignBody).toContainText("$20,000");
    await expect(campaignBody).toContainText("59% funded");
    await expect(campaignBody).toContainText(/Donate securely|Give securely/i);

    expect(criticalErrors, criticalErrors.join("\n")).toEqual([]);
  });

  test("campaign donation modal opens", async ({ page }) => {
    await page.goto(`${BASE}/c/connect-atx-elite`, {
      waitUntil: "domcontentloaded",
    });

    await page.locator("[data-ff-open-checkout]").first().click();

    await expect(page.getByRole("heading", { name: /complete your gift/i })).toBeVisible();

    await expect(
      page.locator("[data-ff-amount-input], input[name*='amount']").first()
    ).toBeVisible();

    await expect(page.locator("[data-ff-email-input], input[type='email']").first()).toBeVisible();

    await expect(
      page.getByRole("button", { name: /continue|checkout|give|donate/i }).first()
    ).toBeVisible();

    await page.keyboard.press("Escape");
  });

  test("campaign sponsor path is visible", async ({ page }) => {
    await page.goto(`${BASE}/c/connect-atx-elite`, {
      waitUntil: "domcontentloaded",
    });

    const body = page.locator("body");

    await expect(body).toContainText(/Community Partner/i);
    await expect(body).toContainText(/Featured Sponsor/i);
    await expect(body).toContainText(/Season Sponsor/i);
    await expect(body).toContainText(/Sponsor Connect ATX Elite|Become a sponsor|Sponsor/i);
  });

  test("mobile has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    for (const path of ["/platform/", "/c/connect-atx-elite"]) {
      await page.goto(`${BASE}${path}`, {
        waitUntil: "domcontentloaded",
      });

      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth - window.innerWidth;
      });

      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
});
