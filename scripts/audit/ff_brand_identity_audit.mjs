#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.argv[2] || "http://127.0.0.1:5000";
const token = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const pages = [
  { name: "Homepage", url: "/platform/", platformBrand: true },
  { name: "Onboarding", url: "/platform/onboarding", platformBrand: true },
  { name: "Operator login", url: "/platform/login", platformBrand: true },
  { name: "Dashboard locked", url: "/platform/dashboard", platformBrand: true, allow403: true },
  ...(token ? [{ name: "Dashboard private", url: `/platform/dashboard?token=${encodeURIComponent(token)}`, platformBrand: true }] : []),
  { name: "Campaign", url: "/c/connect-atx-elite", campaignBrand: true },
];

const checks = [];

function record(ok, label, detail = "") {
  checks.push({ ok, label, detail });
  console.log(`${ok ? "PASS" : "CHECK"} ${label}${detail ? ` — ${detail}` : ""}`);
}

const browser = await chromium.launch({ headless: true });

for (const viewport of [
  { name: "desktop", width: 1440, height: 1200 },
  { name: "mobile", width: 390, height: 1200 },
]) {
  console.log(`\nFutureFunded brand identity audit [${viewport.name}]`);

  for (const item of pages) {
    const page = await browser.newPage({ viewport });
    const response = await page.goto(`${base.replace(/\/$/, "")}${item.url}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    }).catch(() => null);

    const status = response?.status?.() ?? 0;
    const html = await page.content();

    record(
      item.allow403 ? status === 403 || status === 200 : status === 200,
      `${item.name} responds`,
      `status=${status}`
    );

    record(html.includes("FutureFunded") || html.includes("Connect ATX Elite"), `${item.name} has brand text`);

    if (item.platformBrand) {
      record(!html.includes("ff.cinematic.css"), `${item.name} does not load cinematic CSS`);
      record(!html.includes("ff-cinematic.js"), `${item.name} does not load cinematic JS`);
    }

    const metrics = await page.evaluate(() => {
      const root = document.documentElement;
      const brandSelectors = [
        ".ff-platformHomeBrand",
        ".ff-homeBrand",
        ".ff-platformHeaderBrand",
        ".ff-onboardModernBrand",
        ".ff-dashboardModern__brand",
        ".ff-dashboardLockedBrand",
        ".ff-loginStandalone__brand",
        ".ff-loginBrand",
        ".ff-siteHeader__brand",
        ".ff-platformBrand",
        ".ff-footerBrand",
        "[aria-label*='FutureFunded']",
      ];

      const markSelectors = [
        ".ff-platformHomeBrand__mark",
        ".ff-homeBrand__mark",
        ".ff-platformHeaderBrand__mark",
        ".ff-onboardModernBrand__mark",
        ".ff-dashboardModern__brandMark",
        ".ff-dashboardLockedBrand__mark",
        ".ff-loginStandalone__brandMark", ".ff-loginV4__brandMark",
        ".ff-loginBrand__mark",
        ".ff-siteHeader__brandMark",
        ".ff-platformBrand__mark",
        ".ff-footerBrand__mark",
      ];

      const brand = brandSelectors.map((s) => document.querySelector(s)).find(Boolean);
      const mark = markSelectors.map((s) => document.querySelector(s)).find(Boolean);
      const brandRect = brand?.getBoundingClientRect();
      const markRect = mark?.getBoundingClientRect();
      const markStyle = mark ? getComputedStyle(mark) : null;

      return {
        overflowX: root.scrollWidth > root.clientWidth + 2,
        brandText: brand?.textContent?.replace(/\s+/g, " ").trim() || "",
        markText: mark?.textContent?.replace(/\s+/g, " ").trim() || "",
        brandVisible: Boolean(brandRect && brandRect.width > 40 && brandRect.height > 20),
        markVisible: Boolean(markRect && markRect.width >= 30 && markRect.height >= 30),
        markRadius: markStyle?.borderRadius || "",
        markBg: markStyle?.backgroundImage || markStyle?.backgroundColor || "",
      };
    });

    record(!metrics.overflowX, `${item.name} has no horizontal overflow`);

    if (item.platformBrand) {
      record(metrics.brandVisible, `${item.name} platform brand is visible`, metrics.brandText);
      record(/FutureFunded/i.test(metrics.brandText), `${item.name} brand title says FutureFunded`, metrics.brandText);
      record(metrics.markVisible, `${item.name} brand mark is visible`, metrics.markText || "visual mark");
      record(metrics.markText === "" || /FF/i.test(metrics.markText), `${item.name} brand mark is canonical`, metrics.markText || "visual/asset mark");
    }

    if (item.campaignBrand) {
      record(/Connect ATX Elite/i.test(html), `${item.name} preserves team-first campaign brand`);
      record(/FutureFunded/i.test(html), `${item.name} still includes FutureFunded product brand`);
    }

    await page.close();
  }
}

await browser.close();

const failed = checks.filter((x) => !x.ok);
console.log(`\nSummary: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) process.exit(1);
