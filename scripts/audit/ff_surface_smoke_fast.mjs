#!/usr/bin/env node
import { chromium } from "playwright";

const BASE = (process.env.FF_AUDIT_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const SURFACES = {
  platform: {
    label: "Platform homepage",
    path: "/platform/",
    expect: [200],
    selectors: ["main", "a[href*='/platform/onboarding']", "a[href*='/c/connect-atx-elite']"],
  },
  campaign: {
    label: "Campaign page",
    path: "/c/connect-atx-elite",
    expect: [200],
    selectors: [
      "main",
      "[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]",
      "[data-ff-share-trigger], [data-ff-qr-trigger]",
      "[data-ff-open-sponsor], [data-ff-sponsor-trigger]",
    ],
  },
  login: {
    label: "Operator login",
    path: "/platform/login",
    expect: [200],
    selectors: ["main", "form", "input:not([type='hidden'])", "button, [type='submit']"],
  },
  onboarding: {
    label: "Launch workspace",
    path: "/platform/onboarding",
    expect: [200],
    selectors: ["main", "[data-ff-onboard-root]", "a[href*='/c/connect-atx-elite']"],
  },
  dashboard_locked: {
    label: "Dashboard locked",
    path: "/platform/dashboard",
    expect: [403],
    selectors: ["body"],
    allow403Console: true,
  },
  dashboard_operator: {
    label: "Dashboard operator",
    path: TOKEN ? `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}` : "",
    expect: [200],
    selectors: ["body", "main"],
    needsToken: true,
  },
};

const alias = {
  home: "platform",
  onboard: "onboarding",
  dash: "dashboard_locked",
  dashboard: "dashboard_locked",
  operator: "dashboard_operator",
};

const arg = process.argv[2] || process.env.FF_SMOKE_SURFACES || "platform,campaign";
const wanted = arg
  .split(",")
  .map((x) => x.trim())
  .filter(Boolean)
  .map((x) => alias[x] || x);

const unknown = wanted.filter((x) => !SURFACES[x]);
if (unknown.length) {
  console.error(`Unknown surface(s): ${unknown.join(", ")}`);
  console.error(`Known: ${Object.keys(SURFACES).join(", ")}`);
  process.exit(2);
}

const viewports = [
  ["desktop", { width: 1366, height: 900, isMobile: false }],
  ["mobile", { width: 390, height: 844, isMobile: true, hasTouch: true }],
];

function shouldIgnoreConsole(surface, text) {
  if (/favicon/i.test(text)) return true;
  if (/ResizeObserver loop/i.test(text)) return true;
  if (surface.allow403Console && /403|FORBIDDEN/i.test(text)) return true;
  return false;
}

const browser = await chromium.launch({ headless: true });
let failures = 0;
let checks = 0;

console.log("");
console.log("FutureFunded fast surface smoke");
console.log("================================");
console.log(`Base: ${BASE}`);
console.log(`Surfaces: ${wanted.join(", ")}`);
console.log("");

for (const key of wanted) {
  const surface = SURFACES[key];

  if (surface.needsToken && !TOKEN) {
    console.log(`SKIP ${surface.label}: FF_OPERATOR_ACCESS_TOKEN not set`);
    continue;
  }

  for (const [viewportName, viewport] of viewports) {
    checks += 1;

    const context = await browser.newContext({
      viewport,
      reducedMotion: "reduce",
      ignoreHTTPSErrors: true,
    });

    const page = await context.newPage();
    const consoleErrors = [];
    const pageErrors = [];

    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      if (!shouldIgnoreConsole(surface, text)) consoleErrors.push(text);
    });

    page.on("pageerror", (err) => {
      pageErrors.push(err.message);
    });

    const url = `${BASE}${surface.path}`;
    let status = 0;
    let result = "PASS";
    const notes = [];

    try {
      const response = await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 12000,
      });

      status = response?.status() || 0;

      // Small settle only. Do not wait for full network idle.
      await page.waitForTimeout(500);

      if (!surface.expect.includes(status)) {
        result = "FAIL";
        notes.push(`status=${status}, expected=${surface.expect.join("/")}`);
      }

      const dom = await page.evaluate((selectors) => {
        const counts = Object.fromEntries(
          selectors.map((selector) => [selector, document.querySelectorAll(selector).length])
        );

        const overflowX = Math.max(
          0,
          document.documentElement.scrollWidth - window.innerWidth,
          document.body.scrollWidth - window.innerWidth
        );

        return {
          title: document.title,
          counts,
          overflowX,
        };
      }, surface.selectors);

      for (const [selector, count] of Object.entries(dom.counts)) {
        if (!count) {
          result = "FAIL";
          notes.push(`missing selector: ${selector}`);
        }
      }

      if (dom.overflowX > 4) {
        result = "FAIL";
        notes.push(`overflowX=${dom.overflowX}px`);
      }

      if (consoleErrors.length) {
        result = "FAIL";
        notes.push(`console=${consoleErrors.slice(0, 2).join(" | ")}`);
      }

      if (pageErrors.length) {
        result = "FAIL";
        notes.push(`pageerror=${pageErrors.slice(0, 2).join(" | ")}`);
      }
    } catch (err) {
      result = "FAIL";
      notes.push(`load error: ${err.message}`);
    }

    if (result !== "PASS") failures += 1;

    console.log(
      `${result} ${surface.label} [${viewportName}] status=${status || "n/a"}${
        notes.length ? ` — ${notes.join("; ")}` : ""
      }`
    );

    await context.close();
  }
}

await browser.close();

console.log("");
console.log(`Summary: ${checks - failures}/${checks} passed`);

process.exit(failures ? 1 : 0);
