import { chromium } from "playwright";
import fs from "node:fs/promises";

const url =
  process.env.CAMPAIGN_URL ||
  process.env.FF_CAMPAIGN_URL ||
  "http://127.0.0.1:5000/c/connect-atx-elite";

const outDir = "artifacts/frontend-screenshots";

const allowedConsoleNoise = [/favicon/i, /ResizeObserver loop/i, /paypalobjects/i, /stripe/i];

const tapTargetAllowList = [
  ".ff-sr-only",
  ".ff-sr-only *",
  ".ff-brand-lockup",
  ".ff-brand-lockup *",
  ".ff-footerV2 a",
  "footer a",
];

function isAllowedConsoleNoise(message) {
  return allowedConsoleNoise.some((pattern) => pattern.test(message));
}

async function writeAudit(name, payload) {
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(`${outDir}/${name}.json`, JSON.stringify(payload, null, 2));
  console.log(`🧪 Wrote ${outDir}/${name}.json`);
}

async function newPage(browser, viewport) {
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    bypassCSP: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  const page = await context.newPage();

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

    if (!/favicon|analytics|stripe|paypal|paypalobjects|qrserver/i.test(requestUrl)) {
      failedRequests.push({
        url: requestUrl,
        method: request.method(),
        failure: request.failure()?.errorText || "unknown",
      });
    }
  });

  page.setDefaultTimeout(25_000);

  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 45_000,
  });

  if (!response || !response.ok()) {
    throw new Error(
      `Could not load campaign URL: ${url}. Status: ${response?.status() ?? "no response"}`
    );
  }

  await page.waitForSelector("#campaign-main");
  await page.waitForSelector("#campaign-hero");
  await page.emulateMedia({ reducedMotion: "reduce" });

  return { context, page, consoleErrors, pageErrors, failedRequests };
}

async function assertCount(page, selector, label, min = 1) {
  const count = await page.locator(selector).count();

  if (count < min) {
    throw new Error(`Missing ${label}. Selector: ${selector}`);
  }

  console.log(`✅ ${label}: ${count}`);
  return count;
}

async function runAccessibilitySmoke(page) {
  const result = await page.evaluate(() => {
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

    const missingButtonNames = Array.from(document.querySelectorAll("button, [role='button']"))
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

    const missingLinkNames = Array.from(document.querySelectorAll("a[href]"))
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

    const missingImageAlt = Array.from(document.querySelectorAll("img"))
      .filter((img) => !img.hasAttribute("alt"))
      .map((img) => ({
        src: img.currentSrc || img.src || "",
        id: img.id,
        className: String(img.className || ""),
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
      lang: document.documentElement.lang || "",
      mainCount: document.querySelectorAll("main").length,
      h1Count: document.querySelectorAll("h1").length,
      skipLinkExists: Boolean(document.querySelector("a[href='#campaign-main']")),
      missingButtonNames,
      missingLinkNames,
      missingImageAlt,
      duplicateIds,
    };
  });

  const failures = [];

  if (!result.title?.trim()) failures.push("Document title is missing.");
  if (!result.mainCount) failures.push("Main landmark is missing.");
  if (!result.h1Count) failures.push("H1 is missing.");
  if (!result.skipLinkExists) failures.push("Skip link to #campaign-main is missing.");
  if (result.missingButtonNames.length) {
    failures.push(`Buttons missing accessible names: ${result.missingButtonNames.length}`);
  }
  if (result.missingLinkNames.length) {
    failures.push(`Links missing accessible names: ${result.missingLinkNames.length}`);
  }
  if (result.missingImageAlt.length) {
    failures.push(`Images missing alt attributes: ${result.missingImageAlt.length}`);
  }
  if (result.duplicateIds.length) {
    failures.push(`Duplicate IDs found: ${result.duplicateIds.map((x) => x.id).join(", ")}`);
  }

  if (failures.length) {
    throw new Error(`Accessibility smoke failed:\n${failures.join("\n")}`);
  }

  console.log("✅ Accessibility smoke checks passed.");
  return result;
}

async function runTapTargetAudit(page, label) {
  const issues = await page.evaluate((tapTargetAllowList) => {
    const allow = (el) =>
      tapTargetAllowList.some((selector) => el.matches(selector) || el.closest(selector));

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

    return Array.from(
      document.querySelectorAll(
        "button, a[href], input, select, textarea, summary, [role='button']"
      )
    )
      .filter(visible)
      .filter((el) => !allow(el))
      .map((el) => {
        const rect = el.getBoundingClientRect();

        return {
          tag: el.tagName.toLowerCase(),
          text: (el.textContent || el.getAttribute("aria-label") || "")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, 80),
          href: el.getAttribute("href") || "",
          id: el.id || "",
          className: String(el.className || "").slice(0, 120),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      })
      .filter((item) => item.width < 36 || item.height < 32);
  }, tapTargetAllowList);

  if (issues.length) {
    throw new Error(
      `${label} tap-target audit failed. Small targets:\n${JSON.stringify(
        issues.slice(0, 20),
        null,
        2
      )}`
    );
  }

  console.log(`✅ ${label} tap-target audit passed.`);
  return issues;
}

async function runImageAudit(page) {
  await page.evaluate(() => {
    window.scrollTo(0, document.body.scrollHeight);
  });

  await page.waitForTimeout(600);

  const result = await page.evaluate(() =>
    Array.from(document.querySelectorAll("img")).map((img) => ({
      src: img.currentSrc || img.src || "",
      alt: img.getAttribute("alt"),
      complete: img.complete,
      naturalWidth: img.naturalWidth,
      naturalHeight: img.naturalHeight,
      loading: img.getAttribute("loading") || "",
      decoding: img.getAttribute("decoding") || "",
      visible: (() => {
        const style = window.getComputedStyle(img);
        const rect = img.getBoundingClientRect();
        return (
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          rect.width > 0 &&
          rect.height > 0
        );
      })(),
    }))
  );

  const broken = result.filter((img) => img.visible && (!img.complete || img.naturalWidth === 0));

  const missingAlt = result.filter((img) => img.alt === null);

  if (broken.length || missingAlt.length) {
    throw new Error(
      `Image audit failed. Broken: ${broken.length}; missing alt: ${
        missingAlt.length
      }\n${JSON.stringify({ broken, missingAlt }, null, 2)}`
    );
  }

  console.log("✅ Image load/fallback audit passed.");
  return result;
}

async function runLinkShareCopyAudit(page) {
  const result = await page.evaluate(() => {
    const links = Array.from(document.querySelectorAll("a[href]")).map((a) => ({
      text: (a.textContent || a.getAttribute("aria-label") || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 80),
      href: a.getAttribute("href") || "",
      target: a.getAttribute("target") || "",
      rel: a.getAttribute("rel") || "",
    }));

    const emptyOrUnsafeLinks = links.filter((link) => {
      const href = link.href.trim();

      if (!href) return true;
      if (href === "#") return true;
      if (/^javascript:/i.test(href)) return true;
      if (link.target === "_blank" && !/\bnoopener\b/.test(link.rel)) return true;

      return false;
    });

    return {
      links,
      emptyOrUnsafeLinks,
      shareRootExists: Boolean(document.querySelector("#share, [data-ff-share-url]")),
      shareUrl:
        document.querySelector("[data-ff-share-url]")?.getAttribute("data-ff-share-url") || "",
      copyButtons: Array.from(
        document.querySelectorAll("[data-ff-copy-share-url], [data-ff-copy-trigger]")
      ).map((el) => ({
        text: (el.textContent || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim(),
        target: el.getAttribute("data-ff-copy-target") || "",
      })),
    };
  });

  if (result.emptyOrUnsafeLinks.length) {
    throw new Error(
      `Unsafe/empty links found:\n${JSON.stringify(
        result.emptyOrUnsafeLinks.slice(0, 20),
        null,
        2
      )}`
    );
  }

  if (!result.shareRootExists) {
    throw new Error("Share root/share URL contract is missing.");
  }

  if (!result.copyButtons.length) {
    throw new Error("No copy buttons found.");
  }

  const copySelector = "[data-ff-copy-share-url], [data-ff-copy-trigger]";
  const copyButton = page.locator(copySelector).first();

  if ((await copyButton.count()) > 0) {
    await copyButton.scrollIntoViewIfNeeded().catch(() => {});
    await copyButton.click({ timeout: 5_000 }).catch(() => {});
  }

  console.log("✅ Link/share/copy audit passed.");
  return result;
}

async function runNoConsoleErrorAudit(errors) {
  if (errors.consoleErrors.length || errors.pageErrors.length || errors.failedRequests.length) {
    throw new Error(`Browser smoke failed:\n${JSON.stringify(errors, null, 2)}`);
  }

  console.log("✅ No-console-error browser smoke passed.");
}

async function run() {
  const browser = await chromium.launch({ headless: true });

  const desktop = await newPage(browser, { width: 1440, height: 1600 });

  try {
    await assertCount(desktop.page, "#campaign-main", "campaign main");
    await assertCount(desktop.page, "#campaign-hero", "campaign hero");
    await assertCount(
      desktop.page,
      "[data-ff-open-checkout], [data-ff-checkout-trigger], [data-ff-donate-cta]",
      "checkout triggers"
    );
    await assertCount(
      desktop.page,
      "[data-ff-open-sponsor], [data-ff-sponsor-trigger], [data-ff-sponsor-cta]",
      "sponsor triggers"
    );
    await assertCount(
      desktop.page,
      "[data-ff-qr-trigger], [data-ff-share-trigger], [data-ff-copy-share-url]",
      "QR/share triggers"
    );

    const accessibility = await runAccessibilitySmoke(desktop.page);
    const desktopTapTargets = await runTapTargetAudit(desktop.page, "Desktop");
    const images = await runImageAudit(desktop.page);
    const links = await runLinkShareCopyAudit(desktop.page);

    await runNoConsoleErrorAudit({
      consoleErrors: desktop.consoleErrors,
      pageErrors: desktop.pageErrors,
      failedRequests: desktop.failedRequests,
    });

    await writeAudit("campaign-launch-hardening-desktop", {
      ok: true,
      accessibility,
      desktopTapTargets,
      imageCount: images.length,
      linkCount: links.links.length,
      copyButtonCount: links.copyButtons.length,
      consoleErrors: desktop.consoleErrors,
      pageErrors: desktop.pageErrors,
      failedRequests: desktop.failedRequests,
    });
  } finally {
    await desktop.context.close();
  }

  const mobile = await newPage(browser, { width: 390, height: 1200 });

  try {
    await assertCount(
      mobile.page,
      ".ff-mobile-rail, .ff-mobileDonateBar, [data-ff-mobile-rail], [data-ff-mobile-conversion-rail]",
      "mobile rail"
    );
    const mobileTapTargets = await runTapTargetAudit(mobile.page, "Mobile");

    await runNoConsoleErrorAudit({
      consoleErrors: mobile.consoleErrors,
      pageErrors: mobile.pageErrors,
      failedRequests: mobile.failedRequests,
    });

    await writeAudit("campaign-launch-hardening-mobile", {
      ok: true,
      mobileTapTargets,
      consoleErrors: mobile.consoleErrors,
      pageErrors: mobile.pageErrors,
      failedRequests: mobile.failedRequests,
    });
  } finally {
    await mobile.context.close();
  }

  await browser.close();

  console.log("");
  console.log("✅ Campaign launch hardening QA passed.");
}

run();
