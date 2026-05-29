#!/usr/bin/env node
import { chromium } from "playwright";

const base = (process.argv[2] || process.env.FF_VISUAL_BASE || "http://127.0.0.1:5000").replace(/\/$/, "");
const slug = process.argv[3] || process.env.FF_CAMPAIGN_SLUG || "connect-atx-elite";

const viewports = [
  ["desktop", { width: 1440, height: 1500 }],
  ["mobile", { width: 390, height: 1400 }],
];

function check(label, passed, soft = false) {
  return { label, passed: Boolean(passed), soft };
}

async function readStylesheets(page) {
  return await page.evaluate(async () => {
    const links = Array.from(document.querySelectorAll('link[rel~="stylesheet"]'))
      .map((link) => link.href)
      .filter(Boolean);

    const sheets = [];

    for (const href of links) {
      try {
        const res = await fetch(href, { credentials: "same-origin", cache: "no-store" });
        const text = await res.text();
        sheets.push({ href, text });
      } catch {
        sheets.push({ href, text: "" });
      }
    }

    return sheets;
  });
}

async function auditViewport(browser, viewportName, viewport) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(12000);

  const url = `${base}/c/${slug}?audit_paint=${Date.now()}`;
  const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });

  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
      }
    `,
  }).catch(() => {});

  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      try { await document.fonts.ready; } catch {}
    }
    window.scrollTo(0, 0);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });

  const stylesheets = await readStylesheets(page);

  const stylesheetHrefs = stylesheets.map((sheet) => sheet.href);
  const allCss = stylesheets.map((sheet) => sheet.text).join("\n");

  const hasFfCss = stylesheetHrefs.some((href) => /\/ff\.css(\?|$)/.test(href));
  const hasCampaignCss = stylesheetHrefs.some((href) => /\/campaign\.css(\?|$)/.test(href));

  const checkoutOwnedByCampaignCss =
    hasCampaignCss &&
    (
      allCss.includes("FF_CHECKOUT_PRODUCTION_SURFACE_V1") ||
      allCss.includes(".ff-checkoutPanel") ||
      allCss.includes(".ff-donationCheckout") ||
      allCss.includes("[data-ff-checkout]")
    );

  const legacyCheckoutCssLinked = stylesheetHrefs.some((href) =>
    /checkout|ff-checkout|embedded-checkout/i.test(href)
  );

  const hasCheckoutCss = legacyCheckoutCssLinked || checkoutOwnedByCampaignCss;

  const metrics = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;

    const header =
      document.querySelector(".ff-campaignHeader") ||
      document.querySelector("[data-ff-header]") ||
      document.querySelector("header");

    const hero =
      document.querySelector(".ff-campaignHero") ||
      document.querySelector("[data-ff-campaign-hero]") ||
      document.querySelector("main section");

    const sections = Array.from(document.querySelectorAll(".ff-campaignSection, section"))
      .filter((section) => {
        const rect = section.getBoundingClientRect();
        return rect.width > 20 && rect.height > 20;
      });

    const checkoutTrigger = document.querySelector(
      "[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]"
    );

    const campaignJs = Array.from(document.scripts)
      .some((script) => /ff-campaign|campaign/i.test(script.src || ""));

    const cinematicCss = Array.from(document.querySelectorAll('link[rel~="stylesheet"]'))
      .some((link) => /cinematic/i.test(link.href || ""));

    const cinematicJs = Array.from(document.scripts)
      .some((script) => /cinematic/i.test(script.src || ""));

    let headerToHeroGap = null;
    if (header && hero) {
      const headerRect = header.getBoundingClientRect();
      const heroRect = hero.getBoundingClientRect();
      headerToHeroGap = Math.round(heroRect.top - headerRect.bottom);
    }

    const overflowX = root.scrollWidth > root.clientWidth + 3;

    return {
      statusText: body?.innerText?.slice(0, 160) || "",
      scrollHeight: root.scrollHeight,
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      overflowX,
      headerToHeroGap,
      sectionCount: sections.length,
      checkoutTrigger: Boolean(checkoutTrigger),
      campaignJs,
      cinematicCss,
      cinematicJs,
    };
  });

  const checks = [
    check("Campaign responds", response?.status() === 200),
    check("Campaign loads ff.css", hasFfCss),
    check("Campaign loads campaign JS", metrics.campaignJs),
    check("Campaign loads checkout CSS", hasCheckoutCss),
    check("Campaign does not load cinematic CSS", !metrics.cinematicCss),
    check("Campaign does not load cinematic JS", !metrics.cinematicJs),
    check("Checkout trigger contract present", metrics.checkoutTrigger),
    check("Campaign has no horizontal overflow", !metrics.overflowX),
    check("Campaign sections detected", metrics.sectionCount >= 8),
    check("Campaign sections are paint-ready", metrics.scrollHeight > viewport.height && metrics.sectionCount >= 8),
  ];

  await page.close();

  return {
    viewportName,
    status: response?.status() ?? null,
    checks,
    metrics: {
      scrollHeight: metrics.scrollHeight,
      headerToHeroGap: metrics.headerToHeroGap,
      sectionCount: metrics.sectionCount,
    },
  };
}

const browser = await chromium.launch({
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
});

const results = [];

try {
  for (const [viewportName, viewport] of viewports) {
    results.push(await auditViewport(browser, viewportName, viewport));
  }
} finally {
  await browser.close();
}

let passed = 0;
let total = 0;

for (const result of results) {
  console.log(`\nCampaign paint rhythm audit [${result.viewportName}]`);

  for (const item of result.checks) {
    total += 1;
    if (item.passed) passed += 1;
    console.log(`${item.passed ? "PASS" : item.soft ? "CHECK" : "FAIL"} ${item.label}${item.label === "Campaign responds" ? ` — status=${result.status}` : ""}${item.label === "Campaign sections detected" ? ` — count=${result.metrics.sectionCount}` : ""}`);
  }

  console.log(`metrics ${JSON.stringify(result.metrics)}`);
}

console.log(`\nSummary: ${passed}/${total} passed`);

if (passed !== total) {
  process.exitCode = 1;
}
