import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE = process.env.FF_BASE_URL || "https://getfuturefunded.com";

for (const path of ["/platform/", "/c/connect-atx-elite"]) {
  test(`public accessibility gate: ${path}`, async ({ page }) => {
    await page.goto(`${BASE}${path}`, { waitUntil: "domcontentloaded" });

    const results = await new AxeBuilder({ page })
      .disableRules([
        // Keep this list empty unless a known third-party false positive appears.
      ])
      .analyze();

    expect(results.violations).toEqual([]);
  });
}
