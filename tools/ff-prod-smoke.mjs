import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";

const urls = [
  process.env.PLATFORM_URL || "https://getfuturefunded.com/platform/",
  process.env.CAMPAIGN_URL || "https://getfuturefunded.com/c/connect-atx-elite",
];

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1440, height: 1200 },
];

const requiredTextByPage = {
  platform: ["Start a fundraiser"],
  campaign: ["Donate securely", "Become a sponsor", "Give with confidence"],
};

const forbiddenVisibleCopy = [
  { name: "TODO", re: /\bTODO\b/i },
  { name: "FIXME", re: /\bFIXME\b/i },
  { name: "scaffold", re: /\bscaffold/i },
  { name: "placeholder", re: /\bplaceholder\b/i },
  { name: "example.com", re: /example\.com/i },
  { name: "undefined", re: /\bundefined\b/i },
  { name: "null", re: /\bnull\b/i },
  { name: "should", re: /\bshould\b/i },
  { name: "ready for", re: /\bready for\b/i },
];

fs.mkdirSync("reports/smoke", { recursive: true });

function pageKey(url) {
  return url.includes("/c/") ? "campaign" : "platform";
}

function isProd(url) {
  return /^https:\/\/getfuturefunded\.com/i.test(url);
}

const browser = await chromium.launch({ headless: true });
const results = [];

for (const url of urls) {
  for (const viewport of viewports) {
    const key = pageKey(url);
    const context = await browser.newContext({
      viewport,
      ignoreHTTPSErrors: false,
    });

    const page = await context.newPage();
    const consoleErrors = [];
    const pageErrors = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    page.on("pageerror", (err) => {
      pageErrors.push(err.message || String(err));
    });

    let response = null;
    let status = 0;
    let title = "";
    let h1Count = 0;
    let bodyText = "";
    let axeViolations = [];
    let axeError = "";
    let missingText = [];
    let forbiddenHits = [];
    let csp = "";
    let cspHasLocalhost = false;

    try {
      response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 45000,
      });

      await page.waitForLoadState("networkidle", { timeout: 12000 }).catch(() => {});

      status = response?.status() || 0;
      title = await page.title();
      h1Count = await page.locator("h1").count();
      bodyText = await page
        .locator("body")
        .innerText({ timeout: 10000 })
        .catch(() => "");

      const headers = response?.headers?.() || {};
      csp = headers["content-security-policy"] || "";
      cspHasLocalhost = isProd(url) && /(127\.0\.0\.1|localhost)/i.test(csp);

      missingText = (requiredTextByPage[key] || []).filter((text) => !bodyText.includes(text));
      forbiddenHits = forbiddenVisibleCopy
        .filter((item) => item.re.test(bodyText))
        .map((item) => item.name);

      const axe = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      axeViolations = axe.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.length,
        help: v.help,
        description: v.description,
        targets: v.nodes.slice(0, 5).map((node) => ({
          target: node.target,
          html: node.html,
          failureSummary: node.failureSummary,
        })),
      }));

      await page.screenshot({
        path: `reports/smoke/${viewport.name}-${key}.png`,
        fullPage: true,
      });
    } catch (err) {
      axeError = err?.message || String(err);

      await page
        .screenshot({
          path: `reports/smoke/${viewport.name}-${key}-error.png`,
          fullPage: true,
        })
        .catch(() => {});
    }

    const pass =
      status >= 200 &&
      status < 400 &&
      h1Count === 1 &&
      consoleErrors.length === 0 &&
      pageErrors.length === 0 &&
      axeViolations.length === 0 &&
      !axeError &&
      missingText.length === 0 &&
      forbiddenHits.length === 0 &&
      !cspHasLocalhost;

    results.push({
      url,
      viewport: viewport.name,
      status,
      title,
      h1Count,
      consoleErrors,
      pageErrors,
      axeError,
      axeViolations,
      missingText,
      forbiddenHits,
      cspHasLocalhost,
      pass,
    });

    await context.close();
  }
}

await browser.close();

fs.writeFileSync("reports/smoke/results.json", JSON.stringify(results, null, 2));

console.table(
  results.map((r) => ({
    page: r.url.includes("/c/") ? "campaign" : "platform",
    viewport: r.viewport,
    status: r.status,
    h1: r.h1Count,
    consoleErrors: r.consoleErrors.length,
    pageErrors: r.pageErrors.length,
    axe: r.axeViolations.length,
    axeError: r.axeError ? "yes" : "no",
    missing: r.missingText.length,
    copyHits: r.forbiddenHits.length,
    cspLocalhost: r.cspHasLocalhost ? "yes" : "no",
    pass: r.pass,
  }))
);

const failed = results.filter((r) => !r.pass);
if (failed.length) {
  console.error("\n❌ Smoke test failed. See reports/smoke/results.json");
  process.exit(1);
}

console.log("\n✅ Smoke test passed.");
