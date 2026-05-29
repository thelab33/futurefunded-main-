#!/usr/bin/env node
// ff-visual-launch-gate-safe-bounded-v1
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE_URL = (process.env.FF_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const STRICT = process.env.FF_VISUAL_STRICT === "1";
const OUT_DIR = path.resolve("audit_outputs/visual-launch-gate/latest");
const SHOT_DIR = path.join(OUT_DIR, "screenshots");

fs.mkdirSync(SHOT_DIR, { recursive: true });

// Marker: hoi-visual-gate-token-fallback-v1
const baseUrlForToken = process.env.FF_BASE_URL || process.env.BASE_URL || "http://127.0.0.1:5000";
const isLocalTokenProof = /^(http:\/\/127\.0\.0\.1|http:\/\/localhost)/.test(baseUrlForToken);
const operatorToken =
  process.env.FF_OPERATOR_ACCESS_TOKEN ||
  process.env.OPERATOR_ACCESS_TOKEN ||
  process.env.OPERATOR_TOKEN ||
  (isLocalTokenProof ? "dev-operator-20260529123018" : "");

const surfaces = [
  {
    name: "Platform homepage",
    path: "/platform/",
    expected: [200],
    minH1: 1,
    minCta: 0,
  },
  {
    name: "Campaign page",
    path: "/c/connect-atx-elite",
    expected: [200],
    minH1: 1,
    minCta: 20,
    campaign: true,
  },
  {
    name: "Operator login",
    path: "/platform/login",
    expected: [200],
    minH1: 1,
    minCta: 1,
  },
  {
    name: "Launch onboarding",
    path: "/platform/onboarding",
    expected: [200],
    minH1: 1,
    minCta: 4,
  },
  {
    name: "Dashboard locked",
    path: "/platform/dashboard",
    expected: [200, 401, 403],
    minH1: 0,
    minCta: 0,
  },
];

if (operatorToken) {
  surfaces.push({
    name: "Dashboard token",
    path: `/platform/dashboard?access_token=${encodeURIComponent(operatorToken)}`,
    expected: [200],
    minH1: 1,
    minCta: 0,
  });
}

const viewports = [
  { name: "mobile", width: 390, height: 844, isMobile: true },
  { name: "tablet", width: 834, height: 1112, isMobile: false },
  { name: "desktop", width: 1440, height: 980, isMobile: false },
];

function safeName(input) {
  return input.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

async function withTimeout(label, ms, fn) {
  let timer;
  try {
    return await Promise.race([
      fn(),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function closeFast(browser) {
  if (!browser) return;
  await Promise.race([
    browser.close().catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 1500)),
  ]).catch(() => {});
}

async function installRoutes(page) {
  await page.route("**/*", async (route) => {
    const req = route.request();
    const url = req.url();
    const type = req.resourceType();

    const local =
      url.startsWith(BASE_URL) ||
      url.startsWith("http://127.0.0.1") ||
      url.startsWith("http://localhost") ||
      url.startsWith("data:");

    if (!local) {
      return route.abort().catch(() => {});
    }

    // Keep CSS/JS/local HTML. Avoid heavy media/font waits.
    if (["font", "media"].includes(type)) {
      return route.abort().catch(() => {});
    }

    return route.continue().catch(() => {});
  });
}

async function normalizePage(page) {
  await page.evaluate(() => {
    const modalSelectors = [
      "#checkout",
      "#sponsor-modal",
      "#qr-modal",
      "[data-ff-checkout-modal]",
      "[data-ff-sponsor-modal]",
      "[data-ff-qr-modal]",
      "[data-ff-share-drawer]",
      ".ff-checkoutModal",
      ".ff-embeddedCheckout",
      ".ff-sponsorModal",
      ".ff-shareDrawer",
    ];

    for (const selector of modalSelectors) {
      for (const node of document.querySelectorAll(selector)) {
        if (!(node instanceof HTMLElement)) continue;
        node.hidden = true;
        node.setAttribute("hidden", "");
        node.setAttribute("aria-hidden", "true");
        node.setAttribute("data-ff-state", "closed");
        node.classList.remove("is-open", "ff-is-open");
      }
    }

    document.documentElement.classList.remove(
      "ff-modal-open",
      "ff-checkout-open",
      "ff-sponsor-open",
      "ff-share-open"
    );

    document.body?.classList.remove(
      "ff-modal-open",
      "ff-checkout-open",
      "ff-sponsor-open",
      "ff-share-open"
    );

    window.scrollTo(0, 0);
  }).catch(() => {});
}

async function auditSurface(surface, viewport) {
  const url = `${BASE_URL}${surface.path}`;
  console.log(`Auditing ${surface.name} / ${viewport.name} → ${url.replace(/access_token=[^&]+/, "access_token=<redacted>")}`);

  let browser;
  let page;

  const result = {
    surface: surface.name,
    viewport: viewport.name,
    url,
    ok: false,
    status: null,
    h1Count: 0,
    ctaCount: 0,
    overflowX: false,
    screenshot: null,
    errors: [],
  };

  try {
    browser = await chromium.launch({
      headless: true,
      timeout: 20000,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-dev-tools",
        "--disable-features=site-per-process,Translate,BackForwardCache",
        "--no-first-run",
        "--no-default-browser-check",
      ],
    });

    browser.on("disconnected", () => {
      result.errors.push("browser disconnected");
    });

    const context = await browser.newContext({
      viewport: { width: viewport.width, height: viewport.height },
      isMobile: viewport.isMobile,
      javaScriptEnabled: false,
    });

    page = await context.newPage();
    page.setDefaultTimeout(8000);

    await installRoutes(page);

    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 20000,
    });

    result.status = response ? response.status() : null;

    await normalizePage(page);
    await page.waitForTimeout(250).catch(() => {});

    const metrics = await page.evaluate(() => {
      const buttonish = document.querySelectorAll([
        "a[href]",
        "button",
        "[role='button']",
        "[data-ff-open-checkout]",
        "[data-ff-donate-trigger]",
        "[data-ff-payment-trigger]",
        "[data-ff-open-sponsor]",
        "[data-ff-sponsor-trigger]",
        "[data-ff-share-trigger]",
        "[data-ff-qr-trigger]",
      ].join(","));

      return {
        title: document.title,
        h1Count: document.querySelectorAll("h1").length,
        ctaCount: buttonish.length,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        bodyTextLength: document.body?.innerText?.trim()?.length || 0,
      };
    });

    result.title = metrics.title;
    result.h1Count = metrics.h1Count;
    result.ctaCount = metrics.ctaCount;
    result.overflowX = metrics.scrollWidth > metrics.clientWidth + 4;
    result.bodyTextLength = metrics.bodyTextLength;

    const shotName = `${safeName(surface.name)}-${viewport.name}.png`;
    const shotPath = path.join(SHOT_DIR, shotName);

    await page.screenshot({
      path: shotPath,
      fullPage: true,
      timeout: 12000,
    });

    result.screenshot = shotPath;

    const statusOk = surface.expected.includes(result.status);
    const h1Ok = result.h1Count >= surface.minH1;
    const ctaOk = result.ctaCount >= surface.minCta;
    const bodyOk = result.bodyTextLength > 100;
    const overflowOk = !result.overflowX;

    result.ok = statusOk && h1Ok && ctaOk && bodyOk && overflowOk;

    if (!statusOk) result.errors.push(`Expected status ${surface.expected.join("/")} but got ${result.status}`);
    if (!h1Ok) result.errors.push(`Expected at least ${surface.minH1} H1; got ${result.h1Count}`);
    if (!ctaOk) result.errors.push(`Expected at least ${surface.minCta} CTA/buttonish controls; got ${result.ctaCount}`);
    if (!bodyOk) result.errors.push(`Body text too small: ${result.bodyTextLength}`);
    if (!overflowOk) result.errors.push(`Horizontal overflow: scrollWidth ${metrics.scrollWidth}, clientWidth ${metrics.clientWidth}`);
  } catch (error) {
    result.ok = false;
    result.error = error?.stack || error?.message || String(error);
  } finally {
    await closeFast(browser);
  }

  return result;
}

const startedAt = new Date().toISOString();
const results = [];

for (const surface of surfaces) {
  for (const viewport of viewports) {
    const result = await withTimeout(
      `${surface.name} / ${viewport.name}`,
      Number(process.env.FF_VISUAL_SURFACE_TIMEOUT_MS || 35000),
      () => auditSurface(surface, viewport)
    ).catch((error) => ({
      surface: surface.name,
      viewport: viewport.name,
      url: `${BASE_URL}${surface.path}`,
      ok: false,
      error: error?.stack || error?.message || String(error),
      errors: [error?.message || String(error)],
    }));

    results.push(result);
  }
}

const failed = results.filter((result) => !result.ok);
const ok = failed.length === 0;
const score = ok ? 100 : Math.max(0, Math.round(((results.length - failed.length) / Math.max(1, results.length)) * 100));

const report = {
  generatedAt: startedAt,
  baseUrl: BASE_URL,
  strict: STRICT,
  score,
  ok,
  failedCount: failed.length,
  total: results.length,
  results,
};

fs.writeFileSync(path.join(OUT_DIR, "report.json"), JSON.stringify(report, null, 2));

fs.writeFileSync(
  path.join(OUT_DIR, "report.md"),
  [
    "# FutureFunded Safe Visual Launch Gate",
    "",
    `Status: ${ok ? "PASS ✅" : "FAIL ❌"}`,
    `Score: ${score}/100`,
    `Base URL: ${BASE_URL}`,
    `Generated: ${startedAt}`,
    "",
    "| Surface | Viewport | Result | Status | H1 | CTA | Overflow | Screenshot |",
    "|---|---|---:|---:|---:|---:|---:|---|",
    ...results.map((r) => `| ${r.surface} | ${r.viewport} | ${r.ok ? "PASS" : "FAIL"} | ${r.status ?? "-"} | ${r.h1Count ?? "-"} | ${r.ctaCount ?? "-"} | ${r.overflowX ? "YES" : "NO"} | ${r.screenshot || "-"} |`),
    "",
    failed.length ? "## Failures" : "## Failures",
    "",
    ...(failed.length
      ? failed.flatMap((r) => [
          `### ${r.surface} / ${r.viewport}`,
          "",
          "```",
          JSON.stringify({ error: r.error, errors: r.errors }, null, 2),
          "```",
          "",
        ])
      : ["None. ✅", ""]),
  ].join("\n")
);

console.log("");
console.log(`FutureFunded visual launch gate: ${score}/100 ${ok ? "PASS" : "FAIL"}`);
console.log(`Report: ${path.join(OUT_DIR, "report.md")}`);

if (!ok) {
  for (const r of failed) {
    console.error(`❌ ${r.surface} / ${r.viewport}: ${(r.errors || [r.error]).filter(Boolean).join("; ")}`);
  }
}

process.exit(ok || !STRICT ? 0 : 1);
