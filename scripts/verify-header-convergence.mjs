import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const homepageUrl =
  process.env.HOMEPAGE_URL || process.env.PLATFORM_URL || "http://127.0.0.1:5000/platform/";

const campaignUrl = process.env.CAMPAIGN_URL || "http://127.0.0.1:5000/c/connect-atx-elite";

const outDir = "artifacts/frontend-screenshots";

const pages = [
  {
    name: "homepage",
    url: homepageUrl,
    variant: "platform",
    expectedBrand: /FutureFunded/i,
    minActions: 2,
    minNavLinksDesktop: 4,
  },
  {
    name: "campaign",
    url: campaignUrl,
    variant: "campaign",
    expectedBrand: /Connect ATX Elite/i,
    minActions: 2,
    minNavLinksDesktop: 0,
  },
];

const viewports = [
  {
    name: "desktop",
    viewport: { width: 1440, height: 1400 },
    minHeight: 52,
    maxHeight: 92,
  },
  {
    name: "mobile",
    viewport: { width: 390, height: 1100 },
    minHeight: 48,
    maxHeight: 86,
  },
];

async function writeAudit(payload) {
  await fs.mkdir(outDir, { recursive: true });
  const filePath = path.join(outDir, "header-convergence.json");
  await fs.writeFile(filePath, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`🧪 Wrote ${filePath}`);
}

function isIgnorableRequest(url) {
  return url.startsWith("data:") || url.startsWith("blob:") || url.includes("/favicon.ico");
}

async function inspectHeader(page, config, viewport) {
  const selector = `[data-ff-header][data-ff-header-surface="unified"][data-ff-header-variant="${config.variant}"]`;

  const header = page.locator(selector).first();

  if (!(await header.count())) {
    throw new Error(`${config.name} missing unified header selector: ${selector}`);
  }

  await header.waitFor({ state: "visible", timeout: 10_000 });

  const result = await header.evaluate((el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();

    const text = (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();

    const actionEls = Array.from(
      el.querySelectorAll(
        [
          "a[href]",
          "button",
          '[role="button"]',
          "[data-ff-open-checkout]",
          "[data-ff-share-trigger]",
          "[data-ff-home-primary-cta]",
        ].join(",")
      )
    );

    const navLinks = Array.from(
      el.querySelectorAll(
        [
          ".ff-primary-nav a[href]",
          ".ff-site-nav a[href]",
          ".ff-main-nav a[href]",
          "[data-ff-primary-nav] a[href]",
        ].join(",")
      )
    );

    return {
      text,
      height: Math.round(rect.height),
      width: Math.round(rect.width),
      top: Math.round(rect.top),
      position: style.position,
      zIndex: style.zIndex,
      background: style.backgroundColor,
      borderBottomColor: style.borderBottomColor,
      boxShadow: style.boxShadow,
      backdropFilter: style.backdropFilter || style.webkitBackdropFilter || "none",
      actionCount: actionEls.length,
      navLinkCount: navLinks.length,
      actionLabels: actionEls.map((node) =>
        (node.innerText || node.textContent || node.getAttribute("aria-label") || "")
          .replace(/\s+/g, " ")
          .trim()
      ),
      navLabels: navLinks.map((node) =>
        (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim()
      ),
      data: {
        header: el.getAttribute("data-ff-header"),
        surface: el.getAttribute("data-ff-header-surface"),
        variant: el.getAttribute("data-ff-header-variant"),
        role: el.getAttribute("role"),
      },
    };
  });

  const failures = [];

  if (!config.expectedBrand.test(result.text)) {
    failures.push(`${config.name}/${viewport.name}: expected brand text not found in header.`);
  }

  if (result.height < viewport.minHeight || result.height > viewport.maxHeight) {
    failures.push(
      `${config.name}/${viewport.name}: header height ${result.height}px outside ${viewport.minHeight}-${viewport.maxHeight}px.`
    );
  }

  if (!["sticky", "fixed"].includes(result.position)) {
    failures.push(
      `${config.name}/${viewport.name}: expected sticky/fixed header, got ${result.position}.`
    );
  }

  if (result.actionCount < config.minActions) {
    failures.push(
      `${config.name}/${viewport.name}: expected at least ${config.minActions} actions, got ${result.actionCount}.`
    );
  }

  if (viewport.name === "desktop" && result.navLinkCount < config.minNavLinksDesktop) {
    failures.push(
      `${config.name}/${viewport.name}: expected at least ${config.minNavLinksDesktop} nav links, got ${result.navLinkCount}.`
    );
  }

  if (result.data.surface !== "unified") {
    failures.push(`${config.name}/${viewport.name}: missing unified surface data attr.`);
  }

  if (result.data.variant !== config.variant) {
    failures.push(
      `${config.name}/${viewport.name}: expected variant ${config.variant}, got ${result.data.variant}.`
    );
  }

  if (result.data.role !== "banner") {
    failures.push(`${config.name}/${viewport.name}: expected role="banner".`);
  }

  if (failures.length) {
    throw new Error(
      `Header convergence failed:\n${failures.join("\n")}\n${JSON.stringify(result, null, 2)}`
    );
  }

  console.log(
    `✅ ${config.name}/${viewport.name} unified header: ${result.height}px, ${result.actionCount} actions, ${result.navLinkCount} nav links.`
  );

  return result;
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const audit = {
    ok: true,
    checkedAt: new Date().toISOString(),
    pages: [],
  };

  try {
    for (const viewport of viewports) {
      for (const config of pages) {
        const context = await browser.newContext({
          viewport: viewport.viewport,
          deviceScaleFactor: 1,
          bypassCSP: true,
        });

        const page = await context.newPage();
        const consoleErrors = [];
        const pageErrors = [];
        const failedRequests = [];

        page.on("console", (message) => {
          if (message.type() === "error") {
            consoleErrors.push({
              text: message.text(),
              location: message.location(),
            });
          }
        });

        page.on("pageerror", (error) => {
          pageErrors.push({
            name: error.name,
            message: error.message,
            stack: error.stack,
          });
        });

        page.on("requestfailed", (request) => {
          if (isIgnorableRequest(request.url())) return;

          failedRequests.push({
            url: request.url(),
            method: request.method(),
            resourceType: request.resourceType(),
            failure: request.failure()?.errorText || "unknown failure",
          });
        });

        const response = await page.goto(config.url, {
          waitUntil: "networkidle",
          timeout: 45_000,
        });

        if (!response || !response.ok()) {
          throw new Error(
            `${config.name}/${viewport.name} did not load cleanly. Status: ${
              response?.status() ?? "no response"
            }`
          );
        }

        const header = await inspectHeader(page, config, viewport);

        if (consoleErrors.length || pageErrors.length || failedRequests.length) {
          throw new Error(
            `${config.name}/${viewport.name} browser smoke failed:\n${JSON.stringify(
              { consoleErrors, pageErrors, failedRequests },
              null,
              2
            )}`
          );
        }

        audit.pages.push({
          name: config.name,
          url: config.url,
          viewport: viewport.name,
          header,
        });

        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  await writeAudit(audit);
  console.log("");
  console.log("✅ Header convergence QA passed.");
}

run();
