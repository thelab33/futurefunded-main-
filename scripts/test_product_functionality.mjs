import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const BASE_URL =
  process.env.FF_FUNCTIONAL_BASE_URL || process.env.FF_BASE_URL || "http://127.0.0.1:5000";

const OUT_DIR = process.env.FF_FUNCTIONAL_DIR || "artifacts/functionality";
const TOKEN_FILE = "/tmp/ff_operator_token";
const ALLOW_MUTATION = process.env.FF_ALLOW_MUTATION === "1";

const HARD_FAIL_ON_WARNINGS = process.env.FF_STRICT_FUNCTIONAL === "1";

async function readToken() {
  const fromEnv = (process.env.FF_OPERATOR_ACCESS_TOKEN || "").trim();
  if (fromEnv) return fromEnv;

  try {
    const fromFile = (await fs.readFile(TOKEN_FILE, "utf8")).trim();
    if (fromFile) return fromFile;
  } catch {
    return "";
  }

  return "";
}

const token = await readToken();

const routes = {
  homepage: "/platform/",
  campaign: "/c/connect-atx-elite",
  login: "/platform/login",
  onboarding: "/platform/onboarding",
  dashboard: token
    ? `/platform/dashboard?operator_token=${encodeURIComponent(token)}`
    : "/platform/dashboard",
};

const report = {
  baseUrl: BASE_URL,
  createdAt: new Date().toISOString(),
  allowMutation: ALLOW_MUTATION,
  tokenAvailable: Boolean(token),
  results: [],
  warnings: [],
  errors: [],
};

function redact(value) {
  return token ? String(value).replaceAll(token, "<redacted>") : String(value);
}

function push(kind, pageName, check, detail = "") {
  const entry = { kind, page: pageName, check, detail: redact(detail) };

  if (kind === "error") report.errors.push(entry);
  if (kind === "warning") report.warnings.push(entry);

  report.results.push(entry);

  const prefix = kind === "error" ? "FAIL" : kind === "warning" ? "WARN" : "PASS";
  console.log(`${prefix} [${pageName}] ${check}${detail ? ` — ${redact(detail)}` : ""}`);
}

function pass(pageName, check, detail = "") {
  push("pass", pageName, check, detail);
}

function warn(pageName, check, detail = "") {
  push("warning", pageName, check, detail);
}

function fail(pageName, check, detail = "") {
  push("error", pageName, check, detail);
}

async function safeGoto(page, pageName, route) {
  const url = `${BASE_URL}${route}`;
  const response = await page.goto(url, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  try {
    await page.waitForLoadState("networkidle", { timeout: 7000 });
  } catch {
    // Polling/live pages may not become fully idle.
  }

  const status = response ? response.status() : null;
  if (!status || status >= 400) {
    fail(pageName, "route rendered", `HTTP ${status} ${url}`);
  } else {
    pass(pageName, "route rendered", `HTTP ${status}`);
  }

  return status;
}

async function visibleCount(page, selector) {
  return await page.locator(selector).evaluateAll((nodes) => {
    return nodes.filter((node) => {
      const style = window.getComputedStyle(node);
      const rect = node.getBoundingClientRect();
      return (
        style.visibility !== "hidden" &&
        style.display !== "none" &&
        rect.width > 0 &&
        rect.height > 0
      );
    }).length;
  });
}

async function expectVisible(page, pageName, selector, label) {
  const count = await visibleCount(page, selector);
  if (count > 0) {
    pass(pageName, label, `${count} visible`);
    return true;
  }

  fail(pageName, label, `Missing selector: ${selector}`);
  return false;
}

async function warnIfMissing(page, pageName, selector, label) {
  const count = await visibleCount(page, selector);
  if (count > 0) {
    pass(pageName, label, `${count} visible`);
    return true;
  }

  warn(pageName, label, `Missing optional selector: ${selector}`);
  return false;
}

async function pressEscape(page) {
  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(250);
}

async function closeCampaignOverlays(page) {
  // Use real close controls first.
  const closeSelectors = [
    "[data-ff-close-checkout]",
    "[data-ff-close-sponsor]",
    "[data-ff-close-share]",
    "[data-ff-close-modal]",
    ".ff-checkoutSheet__backdrop",
    ".ff-overlayBackdrop",
  ];

  for (const selector of closeSelectors) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      await locator.click({ force: true, timeout: 1500 }).catch(() => {});
      await page.waitForTimeout(180);
    }
  }

  await pressEscape(page);

  // Test-only cleanup for drawers that may remain visually open after prior checks.
  await page
    .evaluate(() => {
      document
        .querySelectorAll(
          "[data-ff-checkout-sheet], [data-ff-sponsor-modal], [data-ff-share-drawer], #donation-modal, #sponsor-modal, #share-drawer"
        )
        .forEach((el) => {
          el.classList.remove("is-open", "ff-is-open", "is-visible", "open");
          el.setAttribute("aria-hidden", "true");
        });

      document.body.classList.remove("ff-modal-open", "modal-open", "is-modal-open");
    })
    .catch(() => {});

  await page.waitForTimeout(300);
}

async function checkNoHorizontalOverflow(page, pageName) {
  const data = await page.evaluate(() => {
    const width = window.innerWidth;
    const docWidth = document.documentElement.scrollWidth;

    const offenders = [...document.querySelectorAll("body *")]
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          id: el.id || "",
          className: typeof el.className === "string" ? el.className : "",
          right: Math.round(rect.right),
          left: Math.round(rect.left),
          width: Math.round(rect.width),
        };
      })
      .filter((item) => item.right > width + 4 || item.left < -4)
      .slice(0, 8);

    return { width, docWidth, offenders };
  });

  if (data.docWidth > data.width + 4) {
    warn(
      pageName,
      "horizontal overflow",
      `doc=${data.docWidth}, viewport=${data.width}, offenders=${JSON.stringify(data.offenders)}`
    );
  } else {
    pass(pageName, "no page-level horizontal overflow");
  }
}

async function scanControls(page, pageName) {
  const controls = await page
    .locator("a, button, input, textarea, select, summary, [role='button']")
    .evaluateAll((nodes) => {
      return nodes.map((node) => {
        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        const visible =
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          rect.width > 0 &&
          rect.height > 0;

        const text =
          node.innerText ||
          node.value ||
          node.getAttribute("aria-label") ||
          node.getAttribute("title") ||
          node.getAttribute("name") ||
          node.getAttribute("placeholder") ||
          "";

        return {
          tag: node.tagName.toLowerCase(),
          type: node.getAttribute("type") || "",
          text: text.trim().slice(0, 80),
          href: node.getAttribute("href") || "",
          role: node.getAttribute("role") || "",
          visible,
          disabled: node.disabled || node.getAttribute("aria-disabled") === "true",
        };
      });
    });

  const visibleControls = controls.filter((item) => item.visible);
  const emptyInteractive = visibleControls.filter((item) => {
    if (["input", "textarea", "select"].includes(item.tag)) return false;
    return !item.text && !item.href;
  });

  pass(pageName, "visible interactive controls", String(visibleControls.length));

  if (emptyInteractive.length) {
    warn(
      pageName,
      "controls without accessible text",
      JSON.stringify(emptyInteractive.slice(0, 8))
    );
  }

  return visibleControls;
}

async function clickFirst(page, pageName, selector, label, options = {}) {
  const locator = page.locator(selector).first();
  const count = await locator.count();

  if (!count) {
    if (options.optional) warn(pageName, label, `Missing selector: ${selector}`);
    else fail(pageName, label, `Missing selector: ${selector}`);
    return false;
  }

  try {
    await locator.scrollIntoViewIfNeeded({ timeout: 5000 });
    await locator.click({ timeout: 8000 });
    pass(pageName, label);
    return true;
  } catch (error) {
    fail(pageName, label, error.message);
    return false;
  }
}

async function clickByRoleName(page, pageName, role, name, label, options = {}) {
  const locator = page.getByRole(role, { name }).first();
  const count = await locator.count();

  if (!count) {
    if (options.optional) warn(pageName, label, `Missing role=${role} name=${name}`);
    else fail(pageName, label, `Missing role=${role} name=${name}`);
    return false;
  }

  try {
    await locator.scrollIntoViewIfNeeded({ timeout: 5000 });
    await locator.click({ timeout: 8000 });
    pass(pageName, label);
    return true;
  } catch (error) {
    fail(pageName, label, error.message);
    return false;
  }
}

async function assertAnchorExists(page, pageName, nameRegex, label) {
  const locator = page.getByRole("link", { name: nameRegex }).first();
  const count = await locator.count();

  if (!count) {
    warn(pageName, label, `No link found for ${nameRegex}`);
    return false;
  }

  const href = await locator.getAttribute("href");
  if (!href) {
    warn(pageName, label, "Link has no href");
    return false;
  }

  pass(pageName, label, href);
  return true;
}

async function testHomepage(page) {
  const pageName = "homepage";
  await safeGoto(page, pageName, routes.homepage);
  await expectVisible(page, pageName, ".ff-home, [data-ff-home-root]", "home shell");
  await checkNoHorizontalOverflow(page, pageName);
  await scanControls(page, pageName);

  await assertAnchorExists(page, pageName, /start|fundraiser|launch/i, "primary CTA link");
  await assertAnchorExists(page, pageName, /campaign|demo/i, "campaign/demo link");
  await assertAnchorExists(page, pageName, /sponsor/i, "sponsor-oriented link");

  await warnIfMissing(page, pageName, ".ff-homeConsole", "homepage console");
  await warnIfMissing(page, pageName, ".ff-homeSponsorCard", "sponsor cards");
}

async function testCampaign(page, context) {
  const pageName = "campaign";
  await safeGoto(page, pageName, routes.campaign);
  await expectVisible(
    page,
    pageName,
    "[data-ff-page-root], .page-campaign, .campaign-page",
    "campaign shell"
  );
  await checkNoHorizontalOverflow(page, pageName);
  await scanControls(page, pageName);

  // Donate / checkout openers.
  const checkoutOpened = await clickFirst(
    page,
    pageName,
    "[data-ff-open-checkout]",
    "donate checkout opener"
  );

  if (checkoutOpened) {
    await page.waitForTimeout(500);
    const sheetVisible = await visibleCount(
      page,
      "[data-ff-checkout-sheet], [role='dialog'], .ff-checkoutSheet, .ff-checkout-sheet"
    );

    if (sheetVisible > 0)
      pass(pageName, "checkout sheet/dialog visible", `${sheetVisible} visible`);
    else
      warn(
        pageName,
        "checkout sheet/dialog visible",
        "No visible checkout sheet found after click"
      );

    await closeCampaignOverlays(page);
  }

  // Sponsor modal openers.
  const sponsorOpened = await clickFirst(
    page,
    pageName,
    "[data-ff-open-sponsor]",
    "sponsor modal opener",
    { optional: true }
  );

  if (sponsorOpened) {
    await page.waitForTimeout(500);
    const sponsorVisible = await visibleCount(
      page,
      "[data-ff-sponsor-modal], [role='dialog'], .ff-sponsorModal, .ff-sponsor-modal"
    );

    if (sponsorVisible > 0)
      pass(pageName, "sponsor modal/dialog visible", `${sponsorVisible} visible`);
    else
      warn(pageName, "sponsor modal/dialog visible", "No visible sponsor modal found after click");

    await closeCampaignOverlays(page);
  }

  // Amount buttons.
  const amountCount = await visibleCount(
    page,
    ".ff-amount, [data-ff-amount], button[name='amount']"
  );
  if (amountCount > 0) {
    await clickFirst(
      page,
      pageName,
      ".ff-amount, [data-ff-amount], button[name='amount']",
      "amount button click"
    );
  } else {
    warn(pageName, "amount buttons", "No amount buttons found");
  }

  await closeCampaignOverlays(page);

  // Share button.
  const shareCount = await visibleCount(page, "[data-ff-share]");
  if (shareCount > 0) {
    await clickFirst(page, pageName, "[data-ff-share]", "native/share opener");
    await page.waitForTimeout(500);
    pass(pageName, "share button survived click");
    await pressEscape(page);
  } else {
    warn(pageName, "share button", "No [data-ff-share] found");
  }

  // Copy share URL.
  const copyCount = await visibleCount(page, "[data-ff-copy-share-url]");
  if (copyCount > 0) {
    try {
      await context.grantPermissions(["clipboard-read", "clipboard-write"], {
        origin: new URL(BASE_URL).origin,
      });
    } catch {
      // Some origins/headless contexts may reject permissions. We still click.
    }

    await clickFirst(page, pageName, "[data-ff-copy-share-url]", "copy share URL");
    await page.waitForTimeout(650);

    try {
      const clip = await page.evaluate(async () => navigator.clipboard.readText());
      if (clip && /\/c\/|connect-atx|futurefunded|getfuturefunded/i.test(clip)) {
        pass(pageName, "clipboard contains share URL", clip.slice(0, 160));
      } else {
        warn(pageName, "clipboard contains share URL", clip || "Clipboard empty/unavailable");
      }
    } catch (error) {
      warn(pageName, "clipboard read", error.message);
    }
  } else {
    warn(pageName, "copy share URL button", "No [data-ff-copy-share-url] found");
  }

  // QR code/share surface.
  const qrSelectors = [
    "[data-ff-open-qr]",
    "[data-ff-qr]",
    "[data-ff-share-qr]",
    "button:has-text('QR')",
    "a:has-text('QR')",
  ];

  let qrClicked = false;
  for (const selector of qrSelectors) {
    if (await visibleCount(page, selector)) {
      qrClicked = await clickFirst(page, pageName, selector, "QR/share code opener", {
        optional: true,
      });
      break;
    }
  }

  if (qrClicked) {
    await page.waitForTimeout(650);
    const qrVisible = await visibleCount(
      page,
      "[data-ff-qr-code], [class*='qr'], img[src*='qr'], canvas, svg"
    );

    if (qrVisible > 0)
      pass(pageName, "QR code visual rendered", `${qrVisible} possible QR elements`);
    else warn(pageName, "QR code visual rendered", "QR opener clicked but no QR element detected");

    await closeCampaignOverlays(page);
  } else {
    warn(pageName, "QR/share code opener", "No QR control found");
  }

  // FAQ/details.
  const detailsCount = await visibleCount(page, "details summary, button[aria-expanded]");
  if (detailsCount > 0) {
    await clickFirst(
      page,
      pageName,
      "details summary, button[aria-expanded]",
      "FAQ/details toggle"
    );
  } else {
    warn(pageName, "FAQ/details toggles", "No details/aria-expanded toggles found");
  }

  await warnIfMissing(page, pageName, ".ff-mobile-rail", "mobile rail hook");
}

async function testLogin(page) {
  const pageName = "login";
  await safeGoto(page, pageName, routes.login);
  await expectVisible(page, pageName, "[data-ff-login-root]", "login root");
  await checkNoHorizontalOverflow(page, pageName);
  await scanControls(page, pageName);

  await expectVisible(page, pageName, "[data-ff-login-form], form", "login form");
  await expectVisible(
    page,
    pageName,
    "[data-ff-login-email], input[type='email'], input[name*='email' i]",
    "email field"
  );
  await expectVisible(
    page,
    pageName,
    "[data-ff-login-password], input[type='password']",
    "password field"
  );
  await expectVisible(
    page,
    pageName,
    "[data-ff-login-submit], button[type='submit']",
    "submit button"
  );

  const email = page
    .locator("[data-ff-login-email], input[type='email'], input[name*='email' i]")
    .first();
  if (await email.count()) {
    await email.fill("not-an-email");
    const valid = await email.evaluate((el) => el.checkValidity());
    if (!valid) pass(pageName, "email field validates invalid email");
    else
      warn(
        pageName,
        "email field validates invalid email",
        "Browser reported invalid email as valid"
      );
  }
}

async function testDashboard(page) {
  const pageName = "dashboard";

  if (!token) {
    warn(
      pageName,
      "dashboard auth",
      "Skipping dashboard functionality; no FF_OPERATOR_ACCESS_TOKEN or /tmp/ff_operator_token"
    );
    return;
  }

  await safeGoto(page, pageName, routes.dashboard);
  await expectVisible(page, pageName, "[data-ff-operator-root]", "operator root");
  await checkNoHorizontalOverflow(page, pageName);
  await scanControls(page, pageName);

  await expectVisible(page, pageName, "[data-ff-ledger-url]", "ledger URL hook");
  await expectVisible(page, pageName, "[data-ff-events-url]", "events URL hook");
  await expectVisible(page, pageName, "[data-ff-offline-url]", "offline URL hook");
  await expectVisible(page, pageName, "[data-ff-export-url]", "export URL hook");
  await expectVisible(page, pageName, "[data-ff-offline-donation-form]", "offline donation form");
  await expectVisible(page, pageName, "[data-ff-donations-table]", "donations table");
  await expectVisible(page, pageName, "[data-ff-sponsors-list]", "sponsors list");

  // Export CSV.
  const exportSelector =
    "a:has-text('Export CSV'), button:has-text('Export CSV'), [data-ff-export-url]";
  if (await visibleCount(page, exportSelector)) {
    const exportControl = page.locator(exportSelector).first();
    const href = await exportControl.getAttribute("href").catch(() => null);

    if (href) {
      pass(pageName, "export CSV href", href);
    } else {
      try {
        const downloadPromise = page.waitForEvent("download", { timeout: 5000 });
        await exportControl.click();
        const download = await downloadPromise;
        pass(pageName, "export CSV download", await download.suggestedFilename());
      } catch (error) {
        warn(pageName, "export CSV download", error.message);
      }
    }
  } else {
    warn(pageName, "export CSV control", "No export CSV control found");
  }

  // Refresh ledger.
  const refreshClicked = await clickByRoleName(
    page,
    pageName,
    "button",
    /refresh ledger|refresh/i,
    "refresh ledger button",
    { optional: true }
  );

  if (refreshClicked) {
    await page.waitForTimeout(1000);
    pass(pageName, "refresh ledger survived click");
  }

  // Offline donation form: safe fill only by default.
  const amount = page
    .locator(
      "[data-ff-offline-donation-form] input[name*='amount' i], [data-ff-offline-donation-form] input"
    )
    .first();
  if (await amount.count()) {
    await amount.fill("25.00");
    pass(pageName, "offline amount field fill");
  }

  const donor = page.locator("[data-ff-offline-donation-form] input[name*='donor' i]").first();
  if (await donor.count()) {
    await donor.fill("Playwright QA");
    pass(pageName, "offline donor field fill");
  }

  if (ALLOW_MUTATION) {
    await clickByRoleName(
      page,
      pageName,
      "button",
      /add offline donation|save|submit/i,
      "submit offline donation mutation",
      { optional: true }
    );
  } else {
    pass(pageName, "offline donation submit skipped", "Set FF_ALLOW_MUTATION=1 to submit");
  }
}

async function testOnboarding(page) {
  const pageName = "onboarding";
  await safeGoto(page, pageName, routes.onboarding);
  await checkNoHorizontalOverflow(page, pageName);
  await scanControls(page, pageName);

  await expectVisible(page, pageName, "form, input, textarea", "onboarding inputs/forms");
  await assertAnchorExists(page, pageName, /dashboard/i, "dashboard link");
  await assertAnchorExists(page, pageName, /campaign|preview/i, "campaign/preview link");

  const org = page
    .locator("input[name*='organization' i], input[placeholder*='organization' i]")
    .first();
  if (await org.count()) {
    await org.fill("FutureFunded QA");
    pass(pageName, "organization field fill");
  }

  const campaign = page
    .locator("input[name*='campaign' i], input[placeholder*='campaign' i]")
    .first();
  if (await campaign.count()) {
    await campaign.fill("QA Campaign");
    pass(pageName, "campaign field fill");
  }

  const previewClicked = await clickByRoleName(
    page,
    pageName,
    "button",
    /preview|summary/i,
    "preview setup summary",
    { optional: true }
  );

  if (previewClicked) {
    await page.waitForTimeout(500);
    pass(pageName, "preview button survived click");
  }

  if (ALLOW_MUTATION) {
    await clickByRoleName(
      page,
      pageName,
      "button",
      /save onboarding|save|finish setup/i,
      "save onboarding mutation",
      { optional: true }
    );
  } else {
    pass(pageName, "onboarding save skipped", "Set FF_ALLOW_MUTATION=1 to submit");
  }
}

async function run() {
  await fs.mkdir(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 390, height: 1200 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    reducedMotion: "reduce",
    colorScheme: "light",
  });

  try {
    await context.grantPermissions(["clipboard-read", "clipboard-write"], {
      origin: new URL(BASE_URL).origin,
    });
  } catch {
    // Non-fatal.
  }

  const consoleErrors = [];

  async function newTrackedPage() {
    const page = await context.newPage();

    page.on("console", (message) => {
      if (message.type() === "error") {
        const text = message.text();
        if (/favicon|devtools|CSP|Content Security Policy/i.test(text)) return;
        consoleErrors.push(text);
      }
    });

    page.on("pageerror", (error) => {
      consoleErrors.push(error.message);
    });

    return page;
  }

  const tests = [testHomepage, testCampaign, testLogin, testDashboard, testOnboarding];

  for (const testFn of tests) {
    const page = await newTrackedPage();
    try {
      await testFn(page, context);
    } catch (error) {
      fail(
        testFn.name.replace(/^test/, "").toLowerCase(),
        "unhandled test error",
        error.stack || error.message
      );
      await page
        .screenshot({
          path: path.join(OUT_DIR, `${testFn.name}-failure.png`),
          fullPage: true,
        })
        .catch(() => {});
    } finally {
      await page.close().catch(() => {});
    }
  }

  if (consoleErrors.length) {
    for (const error of consoleErrors.slice(0, 20)) {
      warn("global", "browser console error", error);
    }
  } else {
    pass("global", "no blocking browser console errors");
  }

  await browser.close();

  await fs.writeFile(
    path.join(OUT_DIR, "product-functionality-report.json"),
    JSON.stringify(report, null, 2)
  );

  console.log("");
  console.log(`Report written to ${path.join(OUT_DIR, "product-functionality-report.json")}`);
  console.log(`Passes: ${report.results.filter((item) => item.kind === "pass").length}`);
  console.log(`Warnings: ${report.warnings.length}`);
  console.log(`Errors: ${report.errors.length}`);

  if (report.errors.length || (HARD_FAIL_ON_WARNINGS && report.warnings.length)) {
    process.exit(1);
  }
}

await run();
