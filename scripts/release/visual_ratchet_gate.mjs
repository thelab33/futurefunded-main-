#!/usr/bin/env node
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const ROOT = process.cwd();
const OUT = path.join(ROOT, "audit_outputs", "visual-ratchet");
const BASELINE = path.join(ROOT, "docs", "release-proof", "visual-baseline");

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(BASELINE, { recursive: true });

const BASE_URL = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || process.env.OPERATOR_TOKEN || "";
const UPDATE = process.env.FF_UPDATE_VISUAL_BASELINE === "1";
const HEADLESS = process.env.PW_HEADLESS !== "0";
const MAX_DIFF = Number(process.env.FF_VISUAL_MAX_DIFF_RATIO || "0.04");

const viewports = [
  ["mobile", { width: 390, height: 844 }],
  ["desktop", { width: 1440, height: 980 }],
];

const surfaces = [
  {
    key: "platform-home",
    url: "/platform/",
    status: [200],
    tokens: ["FutureFunded"],
    selectors: ["body"],
  },
  {
    key: "campaign",
    url: "/c/connect-atx-elite",
    status: [200],
    tokens: ["data-ff-page-root", "ffCampaignConfig"],
    selectors: [
      "[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]",
      "[data-ff-open-sponsor], [data-ff-sponsor-trigger], [data-ff-sponsor-cta]",
      "[data-ff-share], [data-ff-share-trigger], [data-ff-qr-trigger]",
    ],
  },
  {
    key: "login",
    url: "/platform/login",
    status: [200],
    tokens: ["Login", "Sign in"],
    selectors: ["body"],
  },
  {
    key: "dashboard-locked",
    url: "/platform/dashboard",
    status: [401, 403],
    tokens: ["dashboard", "operator", "access", "forbidden", "login"],
    selectors: ["body"],
  },
];

if (TOKEN) {
  surfaces.push({
    key: "dashboard-token",
    url: `/platform/dashboard?operator_token=${encodeURIComponent(TOKEN)}`,
    redactedUrl: "/platform/dashboard?operator_token=<redacted>",
    status: [200],
    tokens: ["data-ff-operator-root", "dashboard", "operator"],
    selectors: ["body"],
  });
}

function hash(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function diffRatio(a, b) {
  if (!a || !b) return 1;
  const max = Math.max(a.length, b.length);
  const min = Math.min(a.length, b.length);
  let diff = Math.abs(a.length - b.length);
  for (let i = 0; i < min; i++) if (a[i] !== b[i]) diff++;
  return max ? diff / max : 0;
}

async function diagnostics(page, selectors) {
  return page.evaluate((selectors) => {
    const doc = document.documentElement;
    const body = document.body;
    const scrollWidth = Math.max(doc.scrollWidth, body?.scrollWidth || 0);
    const viewportWidth = window.innerWidth;

    return {
      title: document.title,
      url: location.href,
      viewportWidth,
      viewportHeight: window.innerHeight,
      scrollWidth,
      horizontalOverflow: scrollWidth > viewportWidth + 2,
      bodyTextPreview: document.body?.innerText?.slice(0, 900) || "",
      selectorCounts: Object.fromEntries(
        selectors.map((selector) => [selector, document.querySelectorAll(selector).length])
      ),
      visibleActions: Array.from(document.querySelectorAll("a,button"))
        .filter((el) => {
          const r = el.getBoundingClientRect();
          const s = getComputedStyle(el);
          return r.width > 0 && r.height > 0 && s.display !== "none" && s.visibility !== "hidden";
        })
        .slice(0, 30)
        .map((el) => ({
          tag: el.tagName,
          text: el.textContent.trim().replace(/\s+/g, " ").slice(0, 100),
          href: el.getAttribute("href"),
          attrs: Array.from(el.attributes)
            .filter((a) => a.name.startsWith("data-ff") || a.name === "aria-label")
            .map((a) => `${a.name}=${a.value}`),
        })),
    };
  }, selectors);
}

const browser = await chromium.launch({ headless: HEADLESS });
const errors = [];
const warnings = [];
const results = [];

try {
  for (const [vpName, viewport] of viewports) {
    const context = await browser.newContext({ viewport, ignoreHTTPSErrors: true });
    const page = await context.newPage();

    for (const surface of surfaces) {
      const key = `${surface.key}-${vpName}`;
      const fullUrl = `${BASE_URL}${surface.url}`;
      const shownUrl = surface.redactedUrl || surface.url;

      const png = path.join(OUT, `${key}.png`);
      const htmlPath = path.join(OUT, `${key}.html`);
      const jsonPath = path.join(OUT, `${key}.json`);
      const basePng = path.join(BASELINE, `${key}.png`);

      try {
        const res = await page.goto(fullUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
        await page.waitForLoadState("load", { timeout: 12000 }).catch(() => {});
        await page.waitForTimeout(600);

        const status = res?.status() || 0;
        const html = await page.content();
        fs.writeFileSync(htmlPath, html);

        if (!surface.status.includes(status)) {
          errors.push(`${key}: expected status ${surface.status.join("/")}, got ${status}`);
        }

        if (!surface.tokens.some((token) => html.includes(token))) {
          errors.push(`${key}: missing one of tokens: ${surface.tokens.join(", ")}`);
        }

        for (const selector of surface.selectors) {
          const count = await page.locator(selector).count().catch(() => 0);
          if (count < 1) errors.push(`${key}: missing selector ${selector}`);
        }

        const diag = await diagnostics(page, surface.selectors);
        if (diag.horizontalOverflow) {
          errors.push(`${key}: horizontal overflow scrollWidth=${diag.scrollWidth} viewport=${diag.viewportWidth}`);
        }

        const screenshot = await page.screenshot({ path: png, fullPage: true, animations: "disabled" });
        const currentHash = hash(screenshot);

        let baselineHash = currentHash;
        let ratio = 0;
        let baselineAction = "unchanged";

        if (UPDATE || !fs.existsSync(basePng)) {
          fs.copyFileSync(png, basePng);
          baselineAction = UPDATE ? "updated" : "created";
        } else {
          const baseline = fs.readFileSync(basePng);
          baselineHash = hash(baseline);
          ratio = diffRatio(screenshot, baseline);
          if (ratio > MAX_DIFF) errors.push(`${key}: visual diff ${ratio.toFixed(4)} > ${MAX_DIFF}`);
        }

        const record = {
          key,
          surface: surface.key,
          viewport: vpName,
          url: shownUrl,
          status,
          screenshot: png,
          baseline: basePng,
          html: htmlPath,
          diagnostics: jsonPath,
          currentHash,
          baselineHash,
          diffRatio: ratio,
          baselineAction,
          ...diag,
        };

        fs.writeFileSync(jsonPath, JSON.stringify(record, null, 2));
        results.push(record);
        console.log(`✅ ${key}: captured ${shownUrl}`);
      } catch (err) {
        const msg = `${key}: ${String(err?.message || err)}`;
        errors.push(msg);
        console.error(`❌ ${msg}`);
      }
    }

    await context.close();
  }
} finally {
  await browser.close();
}

const report = {
  ok: errors.length === 0,
  checkedAt: new Date().toISOString(),
  baseUrl: BASE_URL,
  updateBaseline: UPDATE,
  maxDiffRatio: MAX_DIFF,
  errors,
  warnings,
  results,
};

fs.writeFileSync(path.join(OUT, "latest.json"), JSON.stringify(report, null, 2));

const md = [
  "# FutureFunded Visual Ratchet Gate",
  "",
  `**Status:** ${report.ok ? "PASS ✅" : "FAIL ❌"}`,
  `**Checked:** ${report.checkedAt}`,
  "",
  "## Summary",
  "",
  `- Screenshots: ${results.length}`,
  `- Errors: ${errors.length}`,
  `- Warnings: ${warnings.length}`,
  `- Base URL: ${BASE_URL}`,
  `- Max diff ratio: ${MAX_DIFF}`,
  "",
  "## Errors",
  "",
  ...(errors.length ? errors.map((e) => `- ${e}`) : ["- None"]),
  "",
  "## Screenshots",
  "",
  ...results.map((r) => `- ✅ **${r.key}** — diff ${Number(r.diffRatio || 0).toFixed(4)} — baseline ${r.baselineAction}`),
  "",
].join("\n");

fs.writeFileSync(path.join(OUT, "latest.md"), md);
console.log("");
console.log(md);
console.log(`Report: ${path.join(OUT, "latest.json")}`);

if (!report.ok) process.exit(1);
