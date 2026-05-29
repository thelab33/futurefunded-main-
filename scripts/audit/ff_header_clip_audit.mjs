#!/usr/bin/env node
import { chromium } from "playwright";

const BASE = (process.env.FF_AUDIT_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const TOKEN = process.env.FF_OPERATOR_ACCESS_TOKEN || "";

const surfaces = [
  {
    id: "platform",
    label: "platform",
    path: "/platform/",
    expect: [200],
    selectors: ["header", "[data-ff-header], .ff-homeHeader, .ff-siteHeader, .ff-homeTopbar, .ff-homeHeaderWrap"],
  },
  {
    id: "campaign",
    label: "campaign",
    path: "/c/connect-atx-elite",
    expect: [200],
    selectors: ["header", ".ff-campaignHeader, [data-ff-header], .ff-siteHeader"],
  },
  {
    id: "dashboard",
    label: "dashboard",
    path: TOKEN ? `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}` : "/platform/dashboard",
    expect: TOKEN ? [200] : [403],
    selectors: TOKEN
      ? ["header", ".ff-dashboardModern__topbar, .ff-dashboardHeader, .ff-dashboardShell header"]
      : ["body"],
    lockedOk: !TOKEN,
  },
];

const viewports = [
  ["desktop", { width: 1366, height: 900 }],
  ["mobile", { width: 390, height: 844, isMobile: true, hasTouch: true }],
];

function withTimeout(promise, ms, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });

  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function auditSurface(browser, surface, viewportName, viewport) {
  const context = await browser.newContext({
    viewport,
    reducedMotion: "reduce",
    ignoreHTTPSErrors: true,
  });

  const page = await context.newPage();

  try {
    const response = await withTimeout(
      page.goto(`${BASE}${surface.path}`, {
        waitUntil: "domcontentloaded",
        timeout: 9000,
      }),
      11000,
      `${surface.label} ${viewportName} goto`
    );

    const status = response?.status() || 0;

    if (!surface.expect.includes(status)) {
      return {
        ok: false,
        line: `FAIL ${surface.label} [${viewportName}] status=${status} expected=${surface.expect.join("/")}`,
      };
    }

    if (surface.lockedOk && status === 403) {
      return {
        ok: true,
        line: `SKIP ${surface.label} [${viewportName}] status=403 locked dashboard without operator token`,
      };
    }

    await page.waitForTimeout(250);

    const result = await withTimeout(
      page.evaluate((selectors) => {
        const visible = (el) => {
          if (!el) return false;
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            rect.width > 0 &&
            rect.height > 0
          );
        };

        const candidates = selectors.flatMap((selector) =>
          Array.from(document.querySelectorAll(selector))
        );

        const unique = Array.from(new Set(candidates)).filter(visible);

        const clipped = unique
          .map((el) => {
            const rect = el.getBoundingClientRect();
            return {
              label: String(el.className || el.id || el.tagName).slice(0, 100),
              top: Math.round(rect.top),
              bottom: Math.round(rect.bottom),
              height: Math.round(rect.height),
              clippedTop: rect.top < -2,
              clippedBottom: rect.bottom > window.innerHeight + 2,
            };
          })
          .filter((item) => item.clippedTop || item.clippedBottom);

        return {
          count: unique.length,
          clipped,
          overflowX: Math.max(
            0,
            document.documentElement.scrollWidth - window.innerWidth,
            document.body.scrollWidth - window.innerWidth
          ),
        };
      }, surface.selectors),
      6000,
      `${surface.label} ${viewportName} evaluate`
    );

    if (!result.count) {
      return {
        ok: false,
        line: `CHECK ${surface.label} [${viewportName}] status=${status}\n  - missing visible header surface`,
      };
    }

    if (result.overflowX > 4) {
      return {
        ok: false,
        line: `CHECK ${surface.label} [${viewportName}] status=${status}\n  - horizontal overflow ${result.overflowX}px`,
      };
    }

    if (result.clipped.length) {
      const detail = result.clipped
        .slice(0, 3)
        .map((item) => `  - clipped ${item.label} top=${item.top} bottom=${item.bottom} height=${item.height}`)
        .join("\n");

      return {
        ok: false,
        line: `CHECK ${surface.label} [${viewportName}] status=${status}\n${detail}`,
      };
    }

    return {
      ok: true,
      line: `PASS ${surface.label} [${viewportName}] status=${status}`,
    };
  } catch (error) {
    return {
      ok: false,
      line: `FAIL ${surface.label} [${viewportName}]\n  - ${error.message}`,
    };
  } finally {
    await context.close().catch(() => {});
  }
}

console.log("");
console.log("FutureFunded header clip audit");
console.log("================================");

const browser = await chromium.launch({ headless: true });
const results = [];

try {
  for (const [viewportName, viewport] of viewports) {
    for (const surface of surfaces) {
      results.push(await auditSurface(browser, surface, viewportName, viewport));
    }
  }
} finally {
  await browser.close().catch(() => {});
}

for (const result of results) {
  console.log(result.line);
}

const failures = results.filter((result) => !result.ok);

if (failures.length) {
  console.log("");
  console.log(`Header clip audit: ${failures.length} check(s) need attention`);
  process.exit(1);
}

console.log("");
console.log("Header clip audit: PASS");
