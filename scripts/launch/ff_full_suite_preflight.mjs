import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseUrl = (process.env.FF_BASE_URL || process.argv[2] || "http://127.0.0.1:5000").replace(
  /\/$/,
  ""
);

const homepageUrl = process.env.HOMEPAGE_URL || `${baseUrl}/platform/`;
const campaignUrl = process.env.CAMPAIGN_URL || `${baseUrl}/c/connect-atx-elite`;

const outDir = "artifacts/full-suite";

async function writeJson(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, `${JSON.stringify(payload, null, 2)}\n`);
}

async function inspectPage(page, url, kind) {
  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });

  if (!response || !response.ok()) {
    throw new Error(`${kind} did not load. Status: ${response?.status() ?? "no response"}`);
  }

  await page.waitForLoadState("networkidle").catch(() => {});

  return page.evaluate((kind) => {
    const exists = (selector) => Boolean(document.querySelector(selector));
    const count = (selector) => document.querySelectorAll(selector).length;

    const visibleCount = (selector) =>
      Array.from(document.querySelectorAll(selector)).filter((el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          Number(style.opacity) !== 0 &&
          rect.width > 0 &&
          rect.height > 0 &&
          el.getAttribute("aria-hidden") !== "true" &&
          !el.hidden
        );
      }).length;

    const duplicateIds = Object.entries(
      Array.from(document.querySelectorAll("[id]")).reduce((acc, el) => {
        acc[el.id] = (acc[el.id] || 0) + 1;
        return acc;
      }, {})
    )
      .filter(([, total]) => total > 1)
      .map(([id, total]) => ({ id, total }));

    const badCopy = document.body.innerText.match(/\b(None|undefined|null|NaN|Lorem|TODO)\b/g);

    if (kind === "homepage") {
      return {
        kind,
        title: document.title,
        badCopy: badCopy || [],
        duplicateIds,
        hasRoot: exists("[data-ff-home-root]"),
        hasHeader: exists("[data-ff-home-header]"),
        hasHeaderBridge: exists("[data-ff-header][data-ff-home-header]"),
        hasBanner: exists("header[role='banner']"),
        hasMain: exists("#home-main"),
        hasSkipLink: exists("a[href='#home-main']"),
        hasHero: exists("[data-ff-home-section='hero']"),
        hasProduct: exists("[data-ff-home-section='product']"),
        hasCampaigns: exists("[data-ff-home-section='campaigns']"),
        hasSponsors: exists("[data-ff-home-section='sponsors']"),
        hasOperators: exists("[data-ff-home-section='operators']"),
        hasFinalCta: exists("[data-ff-home-section='final-cta']"),
        navLinkCount: count(".ff-homeNav__links a"),
        ctaCount: count(
          "[data-ff-home-primary-cta], [data-ff-home-launch-cta], [data-ff-home-demo-cta], .ff-homeFinal__actions a"
        ),
        h1Count: count("h1"),
      };
    }

    return {
      kind,
      title: document.title,
      badCopy: badCopy || [],
      duplicateIds,
      hasMain: exists("#campaign-main"),
      hasHero: exists("#campaign-hero"),
      hasHeader: exists("[data-ff-header='campaign']"),
      hasBanner: exists("header[role='banner']"),
      checkoutTriggerCount: count(
        "[data-ff-open-checkout], [data-ff-checkout-trigger], [data-ff-donate-trigger], [data-ff-payment-trigger], [data-ff-donate-cta]"
      ),
      legacyCheckoutTriggerCount: count("[data-ff-open-checkout]"),
      sponsorTriggerCount: count(
        "[data-ff-open-sponsor], [data-ff-sponsor-trigger], [data-ff-sponsor-cta]"
      ),
      qrTriggerCount: count(
        "[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-copy-share-url]"
      ),
      mobileRailCount: count(
        ".ff-mobile-rail, .ff-mobileDonateBar, [data-ff-mobile-rail], [data-ff-mobile-conversion-rail]"
      ),
      mediaImageCount: visibleCount('[data-ff-media-bound="true"] img'),
      h1Count: count("h1"),
    };
  }, kind);
}

function assertHomepage(audit) {
  const failures = [];

  if (!audit.title) failures.push("Homepage missing title.");
  if (audit.badCopy.length) failures.push(`Homepage bad copy tokens: ${audit.badCopy.join(", ")}`);
  if (audit.duplicateIds.length)
    failures.push(`Homepage duplicate IDs: ${audit.duplicateIds.map((x) => x.id).join(", ")}`);
  if (!audit.hasRoot) failures.push("Homepage missing [data-ff-home-root].");
  if (!audit.hasHeader) failures.push("Homepage missing [data-ff-home-header].");
  if (!audit.hasHeaderBridge)
    failures.push("Homepage missing [data-ff-header][data-ff-home-header].");
  if (!audit.hasBanner) failures.push("Homepage missing header role=banner.");
  if (!audit.hasMain) failures.push("Homepage missing #home-main.");
  if (!audit.hasSkipLink) failures.push("Homepage missing skip link.");
  if (!audit.hasHero) failures.push("Homepage missing hero section.");
  if (!audit.hasProduct) failures.push("Homepage missing product section.");
  if (!audit.hasCampaigns) failures.push("Homepage missing campaigns section.");
  if (!audit.hasSponsors) failures.push("Homepage missing sponsors section.");
  if (!audit.hasOperators) failures.push("Homepage missing operators section.");
  if (!audit.hasFinalCta) failures.push("Homepage missing final CTA section.");
  if (audit.navLinkCount < 4) failures.push(`Homepage nav links too low: ${audit.navLinkCount}.`);
  if (audit.ctaCount < 3) failures.push(`Homepage CTA count too low: ${audit.ctaCount}.`);
  if (audit.h1Count !== 1) failures.push(`Homepage expected 1 h1, found ${audit.h1Count}.`);

  return failures;
}

function assertCampaign(audit) {
  const failures = [];

  if (!audit.title) failures.push("Campaign missing title.");
  if (audit.badCopy.length) failures.push(`Campaign bad copy tokens: ${audit.badCopy.join(", ")}`);
  if (audit.duplicateIds.length)
    failures.push(`Campaign duplicate IDs: ${audit.duplicateIds.map((x) => x.id).join(", ")}`);
  if (!audit.hasMain) failures.push("Campaign missing #campaign-main.");
  if (!audit.hasHero) failures.push("Campaign missing #campaign-hero.");
  if (!audit.hasHeader) failures.push("Campaign missing [data-ff-header='campaign'].");
  if (!audit.hasBanner) failures.push("Campaign missing header role=banner.");
  if (audit.checkoutTriggerCount < 1) failures.push("Campaign missing checkout triggers.");
  if (audit.legacyCheckoutTriggerCount < 1)
    failures.push("Campaign missing legacy [data-ff-open-checkout] trigger.");
  if (audit.sponsorTriggerCount < 1) failures.push("Campaign missing sponsor triggers.");
  if (audit.qrTriggerCount < 1) failures.push("Campaign missing QR/share triggers.");
  if (audit.mobileRailCount < 1) failures.push("Campaign missing mobile rail.");
  if (audit.mediaImageCount < 2)
    failures.push(`Campaign media image count too low: ${audit.mediaImageCount}.`);
  if (audit.h1Count < 1) failures.push("Campaign missing h1.");

  return failures;
}

const browser = await chromium.launch({ headless: true });

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1200 },
    bypassCSP: true,
  });

  const homepage = await inspectPage(page, homepageUrl, "homepage");
  const campaign = await inspectPage(page, campaignUrl, "campaign");

  const failures = [...assertHomepage(homepage), ...assertCampaign(campaign)];

  await writeJson("preflight-homepage", homepage);
  await writeJson("preflight-campaign", campaign);
  await writeJson("preflight-summary", {
    ok: failures.length === 0,
    baseUrl,
    homepageUrl,
    campaignUrl,
    failures,
    checkedAt: new Date().toISOString(),
  });

  if (failures.length) {
    throw new Error(`Full-suite preflight failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Full-suite preflight passed.");
} finally {
  await browser.close();
}
