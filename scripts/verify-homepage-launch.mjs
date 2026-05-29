import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

const url =
  process.env.HOMEPAGE_URL || process.env.PLATFORM_URL || "http://127.0.0.1:5000/platform/";

const expectedCampaignPath = process.env.HOMEPAGE_EXPECTED_CAMPAIGN_PATH || "/c/connect-atx-elite";

const expectedLaunchPath = process.env.HOMEPAGE_EXPECTED_LAUNCH_PATH || "/platform/onboarding";

const latestDir = "artifacts/frontend-screenshots";
const startedAt = Date.now();

const anchorIds = ["product", "campaigns", "sponsors", "operators", "faq"];

const requiredSelectors = [
  ["[data-ff-home-root]", "homepage root"],
  ["[data-ff-header][data-ff-home-header]", "homepage header"],
  ['header[role="banner"]', "banner header role"],
  ["#home-main", "homepage main"],
  ["[data-ff-home-section='hero']", "hero section"],
  ["[data-ff-home-console]", "hero command console"],
  ["[data-ff-home-primary-cta]", "header primary CTA"],
  ["[data-ff-home-launch-cta]", "hero launch CTA"],
  ["[data-ff-home-demo-cta]", "hero demo CTA"],
  ["[data-ff-home-campaign-preview-cta]", "campaign preview CTA"],
  ["[data-ff-home-footer]", "homepage footer"],
];

const tapTargetAllowList = [
  ".ff-sr-only",
  ".ff-sr-only *",
  ".ff-site-nav a",
  ".ff-homeFooter a",
  ".ff-homeFooter nav a",
  ".ff-brand-lockup",
  ".ff-brand-lockup *",
];

function normalizePathname(input) {
  try {
    const parsed = new URL(input, url);
    const path = parsed.pathname.replace(/\/+$/, "");
    return path || "/";
  } catch {
    return "";
  }
}

function samePath(a, b) {
  return normalizePathname(a) === normalizePathname(b);
}

async function writeAudit(name, payload) {
  await fs.mkdir(latestDir, { recursive: true });
  const filePath = path.join(latestDir, `${name}.json`);
  await fs.writeFile(filePath, `${JSON.stringify(payload, null, 2)}\n`);
  console.log(`🧪 Wrote ${filePath}`);
}

async function assertCount(page, selector, label, min = 1) {
  const count = await page.locator(selector).count();

  if (count < min) {
    throw new Error(`Missing ${label}. Selector: ${selector}`);
  }

  console.log(`✅ ${label}: ${count}`);
  return count;
}

async function assertVisible(page, selector, label) {
  const loc = page.locator(selector).first();

  if (!(await loc.count())) {
    throw new Error(`Missing ${label}. Selector: ${selector}`);
  }

  await loc.waitFor({ state: "visible", timeout: 10_000 });
  console.log(`✅ ${label} visible.`);
}

function isLikelyIgnorableRequest(urlValue) {
  return (
    urlValue.startsWith("data:") ||
    urlValue.startsWith("blob:") ||
    urlValue.includes("/favicon.ico")
  );
}

async function createObservedPage(browser, viewportName, viewport) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    bypassCSP: true,
  });

  const page = await context.newPage();
  page.setDefaultTimeout(25_000);

  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push({
        type: message.type(),
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
    const requestUrl = request.url();

    if (isLikelyIgnorableRequest(requestUrl)) return;

    failedRequests.push({
      url: requestUrl,
      method: request.method(),
      resourceType: request.resourceType(),
      failure: request.failure()?.errorText || "unknown failure",
    });
  });

  const response = await page.goto(url, {
    waitUntil: "networkidle",
    timeout: 45_000,
  });

  if (!response || !response.ok()) {
    throw new Error(
      `${viewportName} homepage did not load cleanly. Status: ${
        response?.status() ?? "no response"
      }`
    );
  }

  await page.evaluate(() => window.scrollTo(0, 0));

  return {
    context,
    page,
    consoleErrors,
    pageErrors,
    failedRequests,
  };
}

async function refreshScreenshots() {
  if (process.env.FF_SKIP_HOMEPAGE_SCREENSHOT_REFRESH === "1") {
    console.log("↪️ Skipping homepage screenshot refresh by env override.");
    return;
  }

  console.log("📸 Refreshing homepage screenshot aliases...");

  const result = spawnSync(process.execPath, ["scripts/capture-homepage-screenshot.mjs"], {
    stdio: "inherit",
    env: {
      ...process.env,
      HOMEPAGE_URL: url,
    },
  });

  if (result.status !== 0) {
    throw new Error(`Homepage screenshot capture failed with exit code ${result.status}.`);
  }
}

async function verifyScreenshotAliases() {
  const files = ["homepage-desktop.png", "homepage-mobile.png"];
  const results = [];

  for (const file of files) {
    const filePath = path.join(latestDir, file);
    const stat = await fs.stat(filePath);

    if (stat.size < 10_000) {
      throw new Error(`Homepage screenshot alias looks too small: ${filePath}`);
    }

    if (process.env.FF_SKIP_HOMEPAGE_SCREENSHOT_REFRESH !== "1") {
      const freshnessSlackMs = 5_000;

      if (stat.mtimeMs < startedAt - freshnessSlackMs) {
        throw new Error(`Homepage screenshot alias was not refreshed during this run: ${filePath}`);
      }
    }

    results.push({
      file,
      path: filePath,
      sizeBytes: stat.size,
      updatedAt: stat.mtime.toISOString(),
    });
  }

  console.log("✅ Homepage screenshot aliases refreshed.");
  return results;
}

async function runAccessibilitySmoke(page) {
  for (const [selector, label] of requiredSelectors) {
    await assertCount(page, selector, label);
  }

  const audit = await page.evaluate(() => {
    const textOf = (el) => (el.innerText || el.textContent || "").trim();

    const h1s = Array.from(document.querySelectorAll("main h1"));
    const title = document.title.trim();
    const metaDescription = document
      .querySelector('meta[name="description"]')
      ?.getAttribute("content")
      ?.trim();

    const emptyLinks = Array.from(document.querySelectorAll("a")).filter((el) => {
      const label = textOf(el) || el.getAttribute("aria-label") || el.getAttribute("title") || "";
      return !label.trim();
    });

    const emptyButtons = Array.from(document.querySelectorAll("button")).filter((el) => {
      const label = textOf(el) || el.getAttribute("aria-label") || el.getAttribute("title") || "";
      return !label.trim();
    });

    const badImages = Array.from(document.querySelectorAll("img")).filter(
      (img) => !img.hasAttribute("alt")
    );

    const detailsWithoutSummary = Array.from(document.querySelectorAll("details")).filter(
      (details) => !details.querySelector("summary")
    );

    const skipLink = document.querySelector(".ff-sr-only[href='#home-main']");

    return {
      title,
      metaDescription,
      h1Count: h1s.length,
      h1Text: h1s.map(textOf),
      emptyLinks: emptyLinks.map((el) => el.outerHTML.slice(0, 240)),
      emptyButtons: emptyButtons.map((el) => el.outerHTML.slice(0, 240)),
      badImages: badImages.map((img) => img.outerHTML.slice(0, 240)),
      detailsWithoutSummary: detailsWithoutSummary.length,
      hasSkipLink: Boolean(skipLink),
      hasMain: Boolean(document.querySelector("#home-main")),
      hasBanner: Boolean(document.querySelector('header[role="banner"]')),
    };
  });

  const failures = [];

  if (!audit.title || audit.title.length < 12) {
    failures.push("Document title is missing or too short.");
  }

  if (!audit.metaDescription || audit.metaDescription.length < 40) {
    failures.push("Meta description is missing or too short.");
  }

  if (audit.h1Count !== 1) {
    failures.push(`Expected exactly one main h1, found ${audit.h1Count}.`);
  }

  if (!audit.hasSkipLink) {
    failures.push("Missing accessible skip link to #home-main.");
  }

  if (!audit.hasMain) {
    failures.push("Missing #home-main.");
  }

  if (!audit.hasBanner) {
    failures.push("Missing banner header role.");
  }

  if (audit.emptyLinks.length) {
    failures.push(`Found empty links: ${JSON.stringify(audit.emptyLinks)}`);
  }

  if (audit.emptyButtons.length) {
    failures.push(`Found empty buttons: ${JSON.stringify(audit.emptyButtons)}`);
  }

  if (audit.badImages.length) {
    failures.push(`Found images without alt: ${JSON.stringify(audit.badImages)}`);
  }

  if (audit.detailsWithoutSummary) {
    failures.push(`Found ${audit.detailsWithoutSummary} details element(s) without summary.`);
  }

  if (failures.length) {
    throw new Error(`Homepage accessibility smoke failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Homepage accessibility smoke checks passed.");
  return audit;
}

async function runAnchorAudit(page) {
  const result = await page.evaluate((anchorIds) => {
    const missing = anchorIds.filter((id) => !document.getElementById(id));

    const missingLinks = anchorIds.filter(
      (id) => !document.querySelector(`a[href="#${CSS.escape(id)}"]`)
    );

    const brokenHashLinks = Array.from(document.querySelectorAll('a[href^="#"]'))
      .map((el) => ({
        href: el.getAttribute("href") || "",
        text: (el.innerText || el.textContent || "").trim(),
      }))
      .filter((link) => {
        if (!link.href || link.href === "#") return false;
        const id = decodeURIComponent(link.href.slice(1));
        return !document.getElementById(id);
      });

    return {
      missing,
      missingLinks,
      brokenHashLinks,
    };
  }, anchorIds);

  if (result.missing.length || result.missingLinks.length || result.brokenHashLinks.length) {
    throw new Error(
      `Homepage anchor audit failed before click checks:
${JSON.stringify(result, null, 2)}`
    );
  }

  for (const id of anchorIds) {
    const selector = `a[href="#${id}"]`;
    const link = page.locator(selector).first();

    if (!(await link.count())) {
      throw new Error(`Missing anchor link for #${id}. Selector: ${selector}`);
    }

    await page.evaluate(() => {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    });

    await page.waitForTimeout(80);
    await link.click({ timeout: 10_000 });

    try {
      await page.waitForFunction(
        (id) => {
          const target = document.getElementById(id);
          if (!target) return false;

          const rect = target.getBoundingClientRect();
          const visibleTopLimit = window.innerHeight * 0.82;

          return rect.top < visibleTopLimit && rect.bottom > 72;
        },
        id,
        { timeout: 5_000 }
      );
    } catch {
      const debug = await page.evaluate((id) => {
        const target = document.getElementById(id);
        const rect = target?.getBoundingClientRect();

        return {
          id,
          hash: window.location.hash,
          scrollY: window.scrollY,
          innerHeight: window.innerHeight,
          targetExists: Boolean(target),
          rect: rect
            ? {
                top: Math.round(rect.top),
                right: Math.round(rect.right),
                bottom: Math.round(rect.bottom),
                left: Math.round(rect.left),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
              }
            : null,
          matchingLinks: Array.from(document.querySelectorAll(`a[href="#${CSS.escape(id)}"]`)).map(
            (el) => ({
              text: (el.innerText || el.textContent || "").trim(),
              className: typeof el.className === "string" ? el.className.slice(0, 180) : "",
              visible: (() => {
                const style = window.getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return (
                  style.display !== "none" &&
                  style.visibility !== "hidden" &&
                  Number(style.opacity) !== 0 &&
                  r.width > 0 &&
                  r.height > 0
                );
              })(),
            })
          ),
        };
      }, id);

      throw new Error(
        `Anchor link did not scroll target into view: #${id}
${JSON.stringify(debug, null, 2)}`
      );
    }

    console.log(`✅ Anchor link reachable: #${id}`);
  }

  await page.evaluate(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  });

  return result;
}

async function runRouteAudit(page) {
  const routeChecks = [
    {
      selector: "[data-ff-home-primary-cta]",
      label: "header primary CTA",
      expected: [expectedLaunchPath],
    },
    {
      selector: "[data-ff-home-launch-cta]",
      label: "hero launch CTA",
      expected: [expectedLaunchPath],
    },
    {
      selector: "[data-ff-home-demo-cta]",
      label: "hero demo CTA",
      expected: [expectedCampaignPath],
    },
    {
      selector: "[data-ff-home-console-link]",
      label: "console campaign link",
      expected: [expectedCampaignPath],
    },
    {
      selector: "[data-ff-home-campaign-preview-cta]",
      label: "campaign preview CTA",
      expected: [expectedCampaignPath],
    },
  ];

  const failures = [];
  const seen = [];

  for (const check of routeChecks) {
    const hrefs = await page.locator(check.selector).evaluateAll((els) =>
      els.map((el) => ({
        href: el.getAttribute("href") || "",
        text: (el.innerText || el.textContent || "").trim(),
      }))
    );

    if (!hrefs.length) {
      failures.push(`Missing ${check.label}: ${check.selector}`);
      continue;
    }

    for (const item of hrefs) {
      const ok = check.expected.some((expected) => samePath(item.href, expected));

      seen.push({
        label: check.label,
        selector: check.selector,
        href: item.href,
        expected: check.expected,
        ok,
      });

      if (!item.href || item.href === "#") {
        failures.push(`${check.label} has empty/hash href.`);
      } else if (!ok) {
        failures.push(
          `${check.label} href mismatch. Got ${item.href}; expected one of ${check.expected.join(
            ", "
          )}`
        );
      }
    }
  }

  const allLinks = await page.locator("a[href]").evaluateAll((els) =>
    els.map((el) => ({
      href: el.getAttribute("href") || "",
      text: (el.innerText || el.textContent || "").trim(),
    }))
  );

  const badLinks = allLinks.filter((link) => !link.href || link.href === "#");

  if (badLinks.length) {
    failures.push(`Found empty/hash links: ${JSON.stringify(badLinks)}`);
  }

  if (failures.length) {
    throw new Error(`Homepage route/link audit failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Homepage CTA route/link audit passed.");
  return {
    routeChecks: seen,
    linkCount: allLinks.length,
  };
}

async function runTapTargetAudit(page, label, minimumSize) {
  const smallTargets = await page.evaluate(
    ({ minimumSize, allowList }) => {
      const isVisible = (el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          Number(style.opacity) !== 0 &&
          rect.width > 0 &&
          rect.height > 0 &&
          !el.hidden &&
          el.getAttribute("aria-hidden") !== "true"
        );
      };

      const isAllowed = (el) =>
        allowList.some((selector) => {
          try {
            return el.matches(selector) || Boolean(el.closest(selector));
          } catch {
            return false;
          }
        });

      const interactive = Array.from(
        document.querySelectorAll(
          [
            "a[href]",
            "button",
            "summary",
            "input",
            "select",
            "textarea",
            '[role="button"]',
            '[tabindex]:not([tabindex="-1"])',
          ].join(",")
        )
      );

      return interactive
        .filter((el) => isVisible(el) && !isAllowed(el))
        .map((el) => {
          const rect = el.getBoundingClientRect();

          return {
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.textContent || "").trim().slice(0, 80),
            href: el.getAttribute("href") || "",
            id: el.id || "",
            className: typeof el.className === "string" ? el.className.slice(0, 180) : "",
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        })
        .filter((item) => item.width < minimumSize || item.height < minimumSize);
    },
    {
      minimumSize,
      allowList: tapTargetAllowList,
    }
  );

  if (smallTargets.length) {
    throw new Error(
      `${label} tap-target audit failed. Small targets:\n${JSON.stringify(smallTargets, null, 2)}`
    );
  }

  console.log(`✅ ${label} tap-target audit passed.`);
  return {
    minimumSize,
    checked: true,
  };
}

async function runImageAudit(page) {
  const result = await page.evaluate(() => {
    const images = Array.from(document.querySelectorAll("img"));

    return images.map((img) => ({
      src: img.currentSrc || img.src || "",
      alt: img.getAttribute("alt"),
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      loading: img.getAttribute("loading"),
    }));
  });

  const broken = result.filter((img) => img.src && (!img.complete || img.naturalWidth <= 0));

  const missingAlt = result.filter((img) => img.alt === null);

  if (broken.length || missingAlt.length) {
    throw new Error(
      `Homepage image audit failed:\n${JSON.stringify({ broken, missingAlt }, null, 2)}`
    );
  }

  console.log("✅ Homepage image load/fallback audit passed.");
  return {
    imageCount: result.length,
    images: result,
  };
}

async function runLayoutAudit(page, label) {
  const result = await page.evaluate(() => {
    const doc = document.documentElement;

    return {
      innerWidth: window.innerWidth,
      scrollWidth: doc.scrollWidth,
      overflowX: doc.scrollWidth - window.innerWidth,
    };
  });

  if (result.overflowX > 2) {
    throw new Error(`${label} layout audit failed. Horizontal overflow: ${JSON.stringify(result)}`);
  }

  console.log(`✅ ${label} horizontal overflow audit passed.`);
  return result;
}

async function runNoConsoleErrorAudit({ consoleErrors, pageErrors, failedRequests, label }) {
  const failures = [];

  if (consoleErrors.length) {
    failures.push(`Console errors: ${JSON.stringify(consoleErrors, null, 2)}`);
  }

  if (pageErrors.length) {
    failures.push(`Page errors: ${JSON.stringify(pageErrors, null, 2)}`);
  }

  if (failedRequests.length) {
    failures.push(`Failed requests: ${JSON.stringify(failedRequests, null, 2)}`);
  }

  if (failures.length) {
    throw new Error(`${label} browser smoke failed:\n${failures.join("\n")}`);
  }

  console.log(`✅ ${label} no-console-error browser smoke passed.`);
}

async function runDesktopAudits(browser, screenshotAliases) {
  const desktop = await createObservedPage(browser, "Desktop", {
    width: 1440,
    height: 2200,
  });

  try {
    const accessibility = await runAccessibilitySmoke(desktop.page);
    const anchors = await runAnchorAudit(desktop.page);
    const routes = await runRouteAudit(desktop.page);
    const tapTargets = await runTapTargetAudit(desktop.page, "Desktop", 30);
    const images = await runImageAudit(desktop.page);
    const layout = await runLayoutAudit(desktop.page, "Desktop");

    await runNoConsoleErrorAudit({
      label: "Desktop",
      consoleErrors: desktop.consoleErrors,
      pageErrors: desktop.pageErrors,
      failedRequests: desktop.failedRequests,
    });

    const payload = {
      ok: true,
      url,
      expectedCampaignPath,
      expectedLaunchPath,
      screenshotAliases,
      accessibility,
      anchors,
      routes,
      tapTargets,
      images,
      layout,
      consoleErrors: desktop.consoleErrors,
      pageErrors: desktop.pageErrors,
      failedRequests: desktop.failedRequests,
      checkedAt: new Date().toISOString(),
    };

    await writeAudit("homepage-launch-hardening-desktop", payload);
  } finally {
    await desktop.context.close();
  }
}

async function runMobileAudits(browser, screenshotAliases) {
  const mobile = await createObservedPage(browser, "Mobile", {
    width: 390,
    height: 2200,
  });

  try {
    await assertCount(mobile.page, "[data-ff-home-root]", "mobile homepage root");
    await assertVisible(mobile.page, "[data-ff-home-primary-cta]", "mobile header primary CTA");
    await assertVisible(mobile.page, "[data-ff-home-launch-cta]", "mobile hero launch CTA");

    const tapTargets = await runTapTargetAudit(mobile.page, "Mobile", 44);
    const layout = await runLayoutAudit(mobile.page, "Mobile");

    await runNoConsoleErrorAudit({
      label: "Mobile",
      consoleErrors: mobile.consoleErrors,
      pageErrors: mobile.pageErrors,
      failedRequests: mobile.failedRequests,
    });

    const payload = {
      ok: true,
      url,
      screenshotAliases,
      tapTargets,
      layout,
      consoleErrors: mobile.consoleErrors,
      pageErrors: mobile.pageErrors,
      failedRequests: mobile.failedRequests,
      checkedAt: new Date().toISOString(),
    };

    await writeAudit("homepage-launch-hardening-mobile", payload);
  } finally {
    await mobile.context.close();
  }
}

async function run() {
  await refreshScreenshots();
  const screenshotAliases = await verifyScreenshotAliases();

  const browser = await chromium.launch({ headless: true });

  try {
    await runDesktopAudits(browser, screenshotAliases);
    await runMobileAudits(browser, screenshotAliases);
  } finally {
    await browser.close();
  }

  console.log("");
  console.log("✅ Homepage launch hardening QA passed.");
}

run();
