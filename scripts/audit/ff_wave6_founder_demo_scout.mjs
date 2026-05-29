#!/usr/bin/env node
/**
 * FutureFunded • Wave 6 Founder Demo Scout
 *
 * Safe:
 * - Does not print env secrets
 * - Captures demo screenshots
 * - Checks founder-demo surfaces and visible CTA/trust contracts
 */

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = process.cwd();
const STAMP = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
const OUT_DIR = path.join(ROOT, "audit_outputs", "wave6-founder-demo");
fs.mkdirSync(OUT_DIR, { recursive: true });

const routes = [
  {
    name: "platform",
    url: "http://127.0.0.1:5000/platform",
    expectStatus: [200],
    contracts: [
      "FutureFunded",
      "View campaign",
      "Start",
      "sponsor"
    ]
  },
  {
    name: "onboarding",
    url: "http://127.0.0.1:5000/platform/onboarding",
    expectStatus: [200],
    contracts: [
      "Launch workspace",
      "launch",
      "sponsor",
      "payment"
    ]
  },
  {
    name: "dashboard",
    url: "http://127.0.0.1:5000/platform/dashboard",
    expectStatus: [200, 403],
    contracts: [
      "Operator",
      "dashboard",
      "launch"
    ]
  },
  {
    name: "campaign",
    url: "http://127.0.0.1:5000/c/connect-atx-elite",
    expectStatus: [200],
    selectors: [
      "[data-ff-open-checkout]",
      "[data-ff-open-sponsor]",
      "[data-ff-share-trigger]",
      ".ff-embeddedCheckout"
    ],
    contracts: [
      "Connect ATX Elite",
      "Give",
      "Sponsor",
      "Share",
      "secure"
    ]
  }
];

const viewports = [
  { name: "mobile", width: 390, height: 844, mobile: true },
  { name: "desktop", width: 1440, height: 1100, mobile: false }
];

function rel(file) {
  return path.relative(ROOT, file);
}

async function inspect(page, route) {
  return page.evaluate(({ selectors = [], contracts = [] }) => {
    const text = document.body.innerText.replace(/\s+/g, " ").trim();

    const visible = (el) => {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return s.display !== "none" && s.visibility !== "hidden" && r.width > 0 && r.height > 0;
    };

    const ctas = [...document.querySelectorAll("a,button")]
      .filter(visible)
      .map((el) => ({
        label: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 80),
        href: el.getAttribute("href") || "",
        type: el.tagName.toLowerCase(),
        classes: String(el.className || "").slice(0, 120)
      }))
      .filter((x) => x.label)
      .slice(0, 40);

    const headings = [...document.querySelectorAll("h1,h2,h3")]
      .filter(visible)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: el.innerText.trim().replace(/\s+/g, " ").slice(0, 120)
      }))
      .slice(0, 40);

    const missingSelectors = selectors.filter((sel) => !document.querySelector(sel));
    const missingText = contracts.filter((needle) => !text.toLowerCase().includes(String(needle).toLowerCase()));

    const doc = document.documentElement;
    const overflow = doc.scrollWidth > doc.clientWidth + 2;

    const hasFollowupLanguage = /receipt|confirmation|thank|follow|email|secure|verified|sponsor review|operator/i.test(text);
    const hasPaymentTrust = /secure|stripe|checkout|payment|receipt|verified/i.test(text);
    const hasSponsorPath = /sponsor|package|business|partner|recognition/i.test(text);

    return {
      title: document.title,
      url: location.href,
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      overflow,
      missingSelectors,
      missingText,
      headings,
      ctas,
      signals: {
        hasFollowupLanguage,
        hasPaymentTrust,
        hasSponsorPath
      }
    };
  }, route);
}

const browser = await chromium.launch({
  headless: true,
  args: ["--disable-dev-shm-usage", "--no-sandbox"]
});

const results = [];

for (const viewport of viewports) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.mobile ? 2 : 1,
    isMobile: viewport.mobile,
    hasTouch: viewport.mobile
  });

  const page = await context.newPage();

  for (const route of routes) {
    const shot = path.join(OUT_DIR, `${STAMP}-${route.name}-${viewport.name}.png`);
    let status = null;
    let error = null;
    let metrics = null;

    try {
      const response = await page.goto(route.url, { waitUntil: "domcontentloaded", timeout: 15000 });
      status = response?.status() ?? null;
      await page.waitForTimeout(900);
      await page.screenshot({ path: shot, fullPage: true });
      metrics = await inspect(page, route);
    } catch (err) {
      error = `${err.name || "Error"}: ${err.message}`;
    }

    results.push({
      route: route.name,
      viewport: viewport.name,
      status,
      expected: route.expectStatus,
      okStatus: route.expectStatus.includes(status),
      error,
      screenshot: rel(shot),
      metrics
    });
  }

  await context.close();
}

await browser.close();

const jsonPath = path.join(OUT_DIR, `ff_wave6_founder_demo_scout_${STAMP}.json`);
const mdPath = path.join(OUT_DIR, `ff_wave6_founder_demo_scout_${STAMP}.md`);

fs.writeFileSync(jsonPath, JSON.stringify({ generatedAt: new Date().toISOString(), results }, null, 2));

const lines = [];
lines.push("# FutureFunded Wave 6 Founder Demo Scout");
lines.push("");
lines.push(`- **Generated:** \`${new Date().toISOString()}\``);
lines.push(`- **Screenshots:** \`${rel(OUT_DIR)}\``);
lines.push("");
lines.push("## Summary");
lines.push("");
lines.push("| Route | Viewport | HTTP | Overflow | Missing selectors | Missing copy | Follow-up | Payment trust | Sponsor path | Screenshot |");
lines.push("| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |");

for (const r of results) {
  const m = r.metrics;
  lines.push(
    `| ${r.route} | ${r.viewport} | ${r.status ?? "ERR"} ${r.okStatus ? "✅" : "❌"} | ` +
    `${m?.overflow ? "❌" : "✅"} | ` +
    `${m?.missingSelectors?.length ? m.missingSelectors.map((x) => `\`${x}\``).join(", ") : "✅"} | ` +
    `${m?.missingText?.length ? m.missingText.map((x) => `\`${x}\``).join(", ") : "✅"} | ` +
    `${m?.signals?.hasFollowupLanguage ? "✅" : "⚠️"} | ` +
    `${m?.signals?.hasPaymentTrust ? "✅" : "⚠️"} | ` +
    `${m?.signals?.hasSponsorPath ? "✅" : "⚠️"} | ` +
    `\`${r.screenshot}\` |`
  );
}

lines.push("");
lines.push("## Demo CTA/headline review");
lines.push("");

for (const r of results) {
  const m = r.metrics;
  if (!m) continue;

  lines.push(`### ${r.route} / ${r.viewport}`);
  lines.push("");
  lines.push("**Headings**");
  for (const h of m.headings.slice(0, 10)) {
    lines.push(`- \`${h.tag}\` ${h.text}`);
  }
  lines.push("");
  lines.push("**Visible CTAs**");
  for (const c of m.ctas.slice(0, 16)) {
    lines.push(`- ${c.type}: ${c.label}${c.href ? ` → \`${c.href}\`` : ""}`);
  }
  lines.push("");
}

lines.push("## Recommended Wave 6B patch direction");
lines.push("");
lines.push("1. Tighten campaign post-donation/post-sponsor trust copy.");
lines.push("2. Make onboarding read like a guided launch workspace, not a form.");
lines.push("3. Make protected dashboard state demo-friendly.");
lines.push("4. Produce a 7-minute founder walkthrough script.");
lines.push("5. Capture final mobile screenshots for stakeholder sharing.");
lines.push("");

fs.writeFileSync(mdPath, lines.join("\n"));

console.log(`✅ Wave 6 founder demo scout: ${mdPath}`);
console.log(`JSON: ${jsonPath}`);
