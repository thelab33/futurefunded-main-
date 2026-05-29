#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
const outDir = path.join(root, "audit_outputs", "wave5b-mobile-pixel-qa");
fs.mkdirSync(outDir, { recursive: true });

const routes = [
  {
    name: "campaign",
    url: "http://127.0.0.1:5000/c/connect-atx-elite",
    contracts: [
      "[data-ff-open-checkout]",
      "[data-ff-open-sponsor]",
      "[data-ff-share-trigger]",
      ".ff-embeddedCheckout"
    ]
  },
  {
    name: "platform",
    url: "http://127.0.0.1:5000/platform",
    contracts: ["body"]
  },
  {
    name: "onboarding",
    url: "http://127.0.0.1:5000/platform/onboarding",
    contracts: ["[data-ff-onboard-root]", "[data-ff-operator-command-strip]"]
  }
];

const viewports = [
  ["iphone-se", 375, 667],
  ["iphone-14", 390, 844],
  ["pixel-7", 412, 915],
  ["tablet", 768, 1024],
  ["desktop", 1440, 1100]
];

async function pageAudit(page, contracts) {
  return await page.evaluate((contracts) => {
    const visible = (el) => {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return s.display !== "none" && s.visibility !== "hidden" && r.width > 0 && r.height > 0;
    };

    const contractStatus = {};
    for (const selector of contracts) {
      contractStatus[selector] = Boolean(document.querySelector(selector));
    }

    const doc = document.documentElement;
    const overflowEls = [...document.querySelectorAll("body *")]
      .filter((el) => {
        const r = el.getBoundingClientRect();
        return r.right > innerWidth + 2 || r.left < -2;
      })
      .slice(0, 12)
      .map((el) => {
        const r = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          id: el.id || "",
          className: String(el.className || "").slice(0, 110),
          left: Math.round(r.left),
          right: Math.round(r.right),
          width: Math.round(r.width)
        };
      });

    const smallTargets = [...document.querySelectorAll("a,button,input,select,textarea,summary,[role='button']")]
      .filter(visible)
      .map((el) => {
        const r = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          label: (el.innerText || el.getAttribute("aria-label") || el.getAttribute("name") || el.tagName).trim().replace(/\s+/g, " ").slice(0, 80),
          width: Math.round(r.width),
          height: Math.round(r.height),
          className: String(el.className || "").slice(0, 90)
        };
      })
      .filter((x) => x.width < 40 || x.height < 40)
      .slice(0, 20);

    return {
      title: document.title,
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      horizontalOverflow: doc.scrollWidth > doc.clientWidth + 2,
      contractStatus,
      overflowEls,
      smallTargets
    };
  }, contracts);
}

const browser = await chromium.launch({
  headless: true,
  args: ["--disable-dev-shm-usage", "--no-sandbox"]
});
const results = [];

for (const [viewportName, width, height] of viewports) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: width < 900 ? 2 : 1,
    isMobile: width < 900,
    hasTouch: width < 900
  });

  const page = await context.newPage();

  for (const route of routes) {
    const base = `${stamp}-${route.name}-${viewportName}`;
    const screenshotPath = path.join(outDir, `${base}.png`);

    let status = null;
    let metrics = null;
    let error = null;

    try {
      const response = await page.goto(route.url, { waitUntil: "domcontentloaded", timeout: 12000 });
      await page.waitForTimeout(900);
      status = response ? response.status() : null;
      await page.screenshot({ path: screenshotPath, fullPage: true });
      metrics = await pageAudit(page, route.contracts);
    } catch (err) {
      error = `${err.name || "Error"}: ${err.message}`;
    }

    results.push({
      route: route.name,
      viewport: viewportName,
      url: route.url,
      status,
      error,
      screenshot: path.relative(root, screenshotPath),
      metrics
    });
  }

  await context.close();
}

await browser.close();

const jsonPath = path.join(outDir, `ff_wave5b_mobile_pixel_qa_${stamp}.json`);
const mdPath = path.join(outDir, `ff_wave5b_mobile_pixel_qa_${stamp}.md`);

fs.writeFileSync(jsonPath, JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2));

const lines = [];
lines.push("# FutureFunded Wave 5B Mobile Pixel QA");
lines.push("");
lines.push(`- **Generated:** \`${new Date().toISOString()}\``);
lines.push(`- **Screenshots:** \`${path.relative(root, outDir)}\``);
lines.push("");
lines.push("## Summary");
lines.push("");
lines.push("| Route | Viewport | HTTP | Overflow | Small targets | Missing contracts | Screenshot |");
lines.push("| --- | --- | ---: | --- | ---: | --- | --- |");

for (const r of results) {
  const m = r.metrics;
  const missing = m ? Object.entries(m.contractStatus).filter(([, ok]) => !ok).map(([k]) => k) : ["metrics_failed"];
  lines.push(
    `| ${r.route} | ${r.viewport} | ${r.status ?? "ERR"} | ` +
    `${m?.horizontalOverflow ? "❌" : "✅"} | ` +
    `${m?.smallTargets?.length ?? "?"} | ` +
    `${missing.length ? missing.map((x) => `\`${x}\``).join(", ") : "✅"} | ` +
    `\`${r.screenshot}\` |`
  );
}

lines.push("");
lines.push("## Review details");
lines.push("");

for (const r of results) {
  const m = r.metrics;
  if (!m) {
    lines.push(`### ${r.route} / ${r.viewport}`);
    lines.push(`- Error: ${r.error}`);
    lines.push("");
    continue;
  }

  const missing = Object.entries(m.contractStatus).filter(([, ok]) => !ok).map(([k]) => k);
  const needsReview = m.horizontalOverflow || m.overflowEls.length || m.smallTargets.length || missing.length;
  if (!needsReview) continue;

  lines.push(`### ${r.route} / ${r.viewport}`);
  lines.push(`- Screenshot: \`${r.screenshot}\``);
  lines.push(`- Horizontal overflow: \`${m.horizontalOverflow}\``);

  if (missing.length) {
    lines.push(`- Missing contracts: ${missing.map((x) => `\`${x}\``).join(", ")}`);
  }

  if (m.overflowEls.length) {
    lines.push("- Overflow candidates:");
    for (const x of m.overflowEls.slice(0, 8)) {
      lines.push(`  - \`${x.tag}\` id=\`${x.id}\` class=\`${x.className}\` right=${x.right} width=${x.width}`);
    }
  }

  if (m.smallTargets.length) {
    lines.push("- Small tap target candidates:");
    for (const x of m.smallTargets.slice(0, 10)) {
      lines.push(`  - \`${x.tag}\` ${x.width}x${x.height} — ${x.label}`);
    }
  }

  lines.push("");
}

fs.writeFileSync(mdPath, lines.join("\n"));

console.log(`✅ Wave 5B mobile pixel QA: ${mdPath}`);
console.log(`JSON: ${jsonPath}`);
