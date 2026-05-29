import { chromium } from "playwright";
import fs from "node:fs/promises";

const url =
  process.env.HOMEPAGE_URL || process.env.PLATFORM_URL || "http://127.0.0.1:5000/platform/";

const outDir = "artifacts/frontend-screenshots";

const allowedConsoleNoise = [/favicon/i, /ResizeObserver loop/i, /stripe/i, /paypal/i];

function isAllowedConsoleNoise(message) {
  return allowedConsoleNoise.some((pattern) => pattern.test(message));
}

async function writeAudit(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, JSON.stringify(payload, null, 2));
  console.log(`🧪 Wrote ${outDir}/${name}.json`);
}

const browser = await chromium.launch({ headless: true });

try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1400 },
    deviceScaleFactor: 1,
    bypassCSP: true,
  });

  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on("console", (msg) => {
    const text = msg.text();
    if (msg.type() === "error" && !isAllowedConsoleNoise(text)) {
      consoleErrors.push(text);
    }
  });

  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });

  page.on("requestfailed", (request) => {
    const requestUrl = request.url();

    if (!/favicon|analytics|stripe|paypal|paypalobjects/i.test(requestUrl)) {
      failedRequests.push({
        url: requestUrl,
        method: request.method(),
        failure: request.failure()?.errorText || "unknown",
      });
    }
  });

  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });

  if (!response || !response.ok()) {
    throw new Error(
      `Could not load homepage URL: ${url}. Status: ${response?.status() ?? "no response"}`
    );
  }

  await page.waitForSelector("[data-ff-home-root]");
  await page.waitForSelector("[data-ff-home-header]");
  await page.waitForSelector("#home-main");

  const audit = await page.evaluate(() => {
    const exists = (selector) => Boolean(document.querySelector(selector));

    const visible = (el) => {
      const style = window.getComputedStyle(el);
      const rect = el.getBoundingClientRect();

      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        Number(style.opacity) !== 0 &&
        rect.width > 0 &&
        rect.height > 0
      );
    };

    const navLinks = Array.from(document.querySelectorAll(".ff-homeNav__links a")).map((a) => ({
      text: (a.textContent || "").replace(/\s+/g, " ").trim(),
      href: a.getAttribute("href") || "",
    }));

    const ctas = Array.from(
      document.querySelectorAll(
        "[data-ff-home-primary-cta], [data-ff-home-launch-cta], [data-ff-home-demo-cta], .ff-homeFinal__actions a"
      )
    ).map((a) => ({
      text: (a.textContent || "").replace(/\s+/g, " ").trim(),
      href: a.getAttribute("href") || "",
    }));

    const buttonsWithoutNames = Array.from(document.querySelectorAll("button, [role='button']"))
      .filter(visible)
      .filter((el) => {
        const name =
          el.getAttribute("aria-label") || el.getAttribute("title") || el.textContent || "";
        return !name.trim();
      })
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        id: el.id,
        className: String(el.className || ""),
      }));

    const linksWithoutNames = Array.from(document.querySelectorAll("a[href]"))
      .filter(visible)
      .filter((el) => {
        const name =
          el.getAttribute("aria-label") || el.getAttribute("title") || el.textContent || "";
        return !name.trim();
      })
      .map((el) => ({
        href: el.getAttribute("href"),
        id: el.id,
        className: String(el.className || ""),
      }));

    const images = Array.from(document.querySelectorAll("img")).map((img) => ({
      src: img.currentSrc || img.src || "",
      alt: img.getAttribute("alt"),
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
    }));

    const duplicateIds = Object.entries(
      Array.from(document.querySelectorAll("[id]")).reduce((acc, el) => {
        acc[el.id] = (acc[el.id] || 0) + 1;
        return acc;
      }, {})
    )
      .filter(([, count]) => count > 1)
      .map(([id, count]) => ({ id, count }));

    return {
      title: document.title,
      hasRoot: exists("[data-ff-home-root]"),
      hasMain: exists("#home-main"),
      hasSkipLink: exists("a[href='#home-main']"),
      hasHeader: exists("[data-ff-home-header]"),
      hasHeaderBridge: exists("[data-ff-header][data-ff-home-header]"),
      hasBannerRole: exists("header[role='banner'][data-ff-home-header]"),
      hasHero: exists("[data-ff-home-section='hero']"),
      hasProduct: exists("[data-ff-home-section='product']"),
      hasCampaigns: exists("[data-ff-home-section='campaigns']"),
      hasSponsors: exists("[data-ff-home-section='sponsors']"),
      hasOperators: exists("[data-ff-home-section='operators']"),
      hasFinalCta: exists("[data-ff-home-section='final-cta']"),
      h1Count: document.querySelectorAll("h1").length,
      navLinkCount: navLinks.length,
      ctaCount: ctas.length,
      navLinks,
      ctas,
      buttonsWithoutNames,
      linksWithoutNames,
      brokenImages: images.filter((img) => img.complete && img.naturalWidth === 0),
      imagesMissingAlt: images.filter((img) => img.alt === null),
      duplicateIds,
    };
  });

  const failures = [];

  if (!audit.title?.trim()) failures.push("Missing document title.");
  if (!audit.hasRoot) failures.push("Missing [data-ff-home-root].");
  if (!audit.hasMain) failures.push("Missing #home-main.");
  if (!audit.hasSkipLink) failures.push("Missing skip link to #home-main.");
  if (!audit.hasHeader) failures.push("Missing [data-ff-home-header].");
  if (!audit.hasHeaderBridge) failures.push("Missing [data-ff-header][data-ff-home-header].");
  if (!audit.hasBannerRole) failures.push("Missing banner role on homepage header.");
  if (!audit.hasHero) failures.push("Missing homepage hero section.");
  if (!audit.hasProduct) failures.push("Missing product section.");
  if (!audit.hasCampaigns) failures.push("Missing campaigns section.");
  if (!audit.hasSponsors) failures.push("Missing sponsors section.");
  if (!audit.hasOperators) failures.push("Missing operators section.");
  if (!audit.hasFinalCta) failures.push("Missing final CTA section.");
  if (audit.h1Count !== 1) failures.push(`Expected exactly one h1, found ${audit.h1Count}.`);
  if (audit.navLinkCount < 4)
    failures.push(`Expected at least 4 nav links, found ${audit.navLinkCount}.`);
  if (audit.ctaCount < 3)
    failures.push(`Expected at least 3 homepage CTAs, found ${audit.ctaCount}.`);
  if (audit.buttonsWithoutNames.length)
    failures.push(`Buttons missing accessible names: ${audit.buttonsWithoutNames.length}.`);
  if (audit.linksWithoutNames.length)
    failures.push(`Links missing accessible names: ${audit.linksWithoutNames.length}.`);
  if (audit.imagesMissingAlt.length)
    failures.push(`Images missing alt attributes: ${audit.imagesMissingAlt.length}.`);
  if (audit.brokenImages.length) failures.push(`Broken images: ${audit.brokenImages.length}.`);
  if (audit.duplicateIds.length)
    failures.push(`Duplicate IDs: ${audit.duplicateIds.map((x) => x.id).join(", ")}.`);
  if (consoleErrors.length) failures.push(`Console errors: ${consoleErrors.join(" | ")}`);
  if (pageErrors.length) failures.push(`Page errors: ${pageErrors.join(" | ")}`);
  if (failedRequests.length)
    failures.push(`Failed requests: ${failedRequests.map((x) => x.url).join(" | ")}`);

  await writeAudit("homepage-surface", {
    ok: failures.length === 0,
    audit,
    consoleErrors,
    pageErrors,
    failedRequests,
  });

  if (failures.length) {
    throw new Error(`Homepage surface verification failed:\n${failures.join("\n")}`);
  }

  await context.close();

  console.log("✅ Homepage surface contracts verified.");
} finally {
  await browser.close();
}
