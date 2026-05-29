#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const BASE = (process.env.FF_AUDIT_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const SLUG = process.env.FF_AUDIT_CAMPAIGN_SLUG || "connect-atx-elite";
const OUT = "audit_outputs/functional-buttons/latest";

function readToken() {
  if (process.env.FF_OPERATOR_ACCESS_TOKEN) return process.env.FF_OPERATOR_ACCESS_TOKEN.trim();
  for (const file of ["/tmp/ff_operator_token.private", "/tmp/ff_operator_token"]) {
    try {
      const token = fs.readFileSync(file, "utf8").trim();
      if (token) return token;
    } catch {}
  }
  return "";
}

const TOKEN = readToken();
const rows = [];
let failures = 0;

function clean(text = "") {
  let value = String(text);
  if (TOKEN) value = value.replaceAll(TOKEN, "[TOKEN]");
  return value.replace(/\s+/g, " ").trim();
}

function row(status, surface, code, message, detail = "") {
  rows.push({ status, surface, code, message: clean(message), detail: clean(detail) });
  console.log(`${status} ${surface} ${code} — ${clean(message)}`);
  if (status === "FAIL") failures += 1;
}

async function pageHealth(page, surface) {
  const errors = page.__errors || [];
  const failed = page.__failed || [];

  if (errors.length) row("FAIL", surface, "console_or_page_errors", `${errors.length} error(s)`, errors.slice(0, 4).join(" | "));
  else row("PASS", surface, "console_or_page_errors", "No blocking console/page errors");

  if (failed.length) row("FAIL", surface, "request_failures", `${failed.length} failed request(s)`, failed.slice(0, 4).join(" | "));
  else row("PASS", surface, "request_failures", "No blocking request failures");
}

async function makePage(context) {
  const page = await context.newPage();
  page.__errors = [];
  page.__failed = [];

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (/favicon|ResizeObserver|preloaded|cloudflareinsights|Failed to load resource.*(403|FORBIDDEN)|server responded with a status of 403/i.test(text)) return;
    page.__errors.push(text);
  });

  page.on("pageerror", (err) => page.__errors.push(err.message || String(err)));

  page.on("requestfailed", (req) => {
    const url = req.url();
    if (/favicon|chrome-extension|cloudflareinsights|analytics/i.test(url)) return;
    page.__failed.push(`${url} ${req.failure()?.errorText || "failed"}`);
  });

  return page;
}

async function goto(page, surface, url, expected = [200]) {
  const res = await page.goto(`${BASE}${url}`, { waitUntil: "domcontentloaded", timeout: 30000 });
  const status = res?.status() || 0;
  if (expected.includes(status)) row("PASS", surface, "http_status", `status=${status}`);
  else row("FAIL", surface, "http_status", `expected ${expected.join("/")} got ${status}`);
  await page.waitForTimeout(250);
}

async function visible(page, surface, selector, code, label) {
  const loc = page.locator(selector).first();
  if (!(await loc.count())) {
    row("FAIL", surface, code, `${label} missing`, selector);
    return false;
  }
  if (!(await loc.isVisible().catch(() => false))) {
    row("FAIL", surface, code, `${label} not visible`, selector);
    return false;
  }
  row("PASS", surface, code, `${label} visible`);
  return true;
}

async function click(page, surface, selector, code, label, options = {}) {
  const { optional = false } = options;
  const loc = page.locator(selector);
  const count = await loc.count();

  if (!count) {
    row(optional ? "WARN" : "FAIL", surface, code, `${label} missing`, selector);
    return false;
  }

  let lastError = "";

  for (let i = 0; i < Math.min(count, 12); i++) {
    const item = loc.nth(i);

    let isVisible = false;
    try {
      isVisible = await item.isVisible({ timeout: 900 });
    } catch {}

    if (!isVisible) continue;

    try {
      await item.scrollIntoViewIfNeeded({ timeout: 3000 });
      await item.click({ timeout: 5000 });
      await page.waitForTimeout(250);
      row("PASS", surface, code, `${label} clicked`);
      return true;
    } catch (err) {
      lastError = err.message || String(err);

      try {
        await item.evaluate((node) => {
          if (node instanceof HTMLElement) node.click();
        });
        await page.waitForTimeout(250);
        row("PASS", surface, code, `${label} clicked with DOM fallback`);
        return true;
      } catch (fallbackErr) {
        lastError = fallbackErr.message || String(fallbackErr);
      }
    }
  }

  row(optional ? "WARN" : "FAIL", surface, code, `${label} click failed`, lastError || selector);
  return false;
}

async function checkSameOriginLinks(page, surface) {
  const links = await page.locator("a[href]").evaluateAll((nodes) =>
    nodes.map((node) => ({
      text: (node.textContent || "").trim(),
      href: node.getAttribute("href") || "",
    }))
  );

  const unique = [];
  const seen = new Set();

  for (const link of links) {
    if (!link.href || link.href.startsWith("#") || /^(mailto|tel|javascript):/i.test(link.href)) continue;

    let url;
    try {
      url = new URL(link.href, BASE);
    } catch {
      row("FAIL", surface, "link_parse", `Invalid link ${link.text}`, link.href);
      continue;
    }

    if (url.origin !== BASE) continue;
    if (seen.has(url.href)) continue;
    seen.add(url.href);
    unique.push({ text: link.text || url.pathname, url: url.href });
  }

  for (const link of unique.slice(0, 24)) {
    const res = await page.request.get(link.url, { timeout: 15000 });
    const status = res.status();
    const ok = status < 400 || (link.url.includes("/platform/dashboard") && status === 403);
    row(ok ? "PASS" : "FAIL", surface, "same_origin_link", `${link.text} -> ${status}`, link.url);
  }
}

async function auditPlatform(context) {
  const surface = "platform";
  const page = await makePage(context);
  await goto(page, surface, "/platform/");

  await visible(page, surface, "header a[href]", "header_nav", "Header nav");
  await visible(page, surface, "a[href*='/platform/onboarding']", "setup_cta", "Setup CTA");
  await visible(page, surface, "a[href*='/c/']", "campaign_cta", "Campaign CTA");

  for (const hash of ["#product", "#campaigns", "#sponsors", "#launch", "#faq"]) {
    if (await page.locator(`a[href='${hash}']`).count()) {
      await click(page, surface, `a[href='${hash}']`, `nav_${hash.slice(1)}`, `Nav ${hash}`);
    }
  }

  if (await page.locator("details summary").count()) {
    await click(page, surface, "details summary", "faq_toggle", "FAQ toggle", { optional: true });
  } else {
    row("WARN", surface, "faq_toggle", "No details FAQ toggles found");
  }

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function auditCampaign(context) {
  const surface = "campaign";
  const page = await makePage(context);
  let checkoutSeen = false;

  await page.route("**/checkout/session", async (route) => {
    checkoutSeen = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "cs_test_functional_contract",
        url: "https://checkout.stripe.com/c/pay/cs_test_functional_contract",
      }),
    });
  });

  await page.route("https://checkout.stripe.com/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>Stripe checkout intercepted by functional QA</title><main>Stripe checkout intercepted by functional QA.</main>",
    });
  });

  await goto(page, surface, `/c/${SLUG}`);

  await visible(page, surface, "[data-ff-open-checkout], [data-ff-donate-trigger]", "donate_cta", "Donate CTA");
  await visible(page, surface, "[data-ff-amount-button], .ff-donationAmount", "amount_buttons", "Amount buttons");
  await visible(page, surface, "[data-ff-custom-amount], input[name='custom_amount']", "custom_amount", "Custom amount input");

  const amountButtons = page.locator("[data-ff-amount-button], .ff-donationAmount");
  const amountCount = await amountButtons.count();

  if (amountCount >= 2) {
    await amountButtons.nth(0).click();
    await amountButtons.nth(1).click();
    row("PASS", surface, "amount_clicks", `${amountCount} amount buttons clickable`);
  } else {
    row("FAIL", surface, "amount_clicks", `Expected multiple amount buttons, found ${amountCount}`);
  }

  const custom = page.locator("[data-ff-custom-amount], input[name='custom_amount']").first();
  if (await custom.count()) {
    await custom.fill("5");
    const value = await custom.inputValue();
    row(value === "5" ? "PASS" : "FAIL", surface, "custom_amount_fill", `custom amount value=${value}`);
  }

  await click(page, surface, "[data-ff-share-trigger], [data-ff-share]", "share_action", "Share action");
  await click(page, surface, "[data-ff-open-sponsor], [data-ff-sponsor-trigger], a[href='#sponsors']", "sponsor_action", "Sponsor action", { optional: true });

  const submit = "[data-ff-donate-submit], [data-ff-payment-trigger], button[type='submit'][data-ff-open-checkout]";
  if (await page.locator(submit).count()) {
    await page.locator(submit).first().scrollIntoViewIfNeeded();
    await page.locator(submit).first().click({ timeout: 7000 }).catch(() => {});
    await page.waitForTimeout(900);
    row(checkoutSeen ? "PASS" : "WARN", surface, "checkout_trigger", checkoutSeen ? "Checkout session attempted" : "Clicked donate submit but checkout request not observed");
  } else {
    row("FAIL", surface, "checkout_trigger", "Donate submit missing");
  }

  if (await page.locator("details summary").count()) {
    await click(page, surface, "details summary", "faq_toggle", "FAQ toggle", { optional: true });
  }

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function auditLogin(context) {
  const surface = "login";
  const page = await makePage(context);
  await goto(page, surface, "/platform/login");

  await visible(page, surface, "input[type='email'], input[name*='email' i]", "email_input", "Email input");
  await visible(page, surface, "input[type='password'], input[name*='password' i]", "password_input", "Password input");
  await visible(page, surface, "button[type='submit'], .ff-button--primary", "login_submit", "Login submit");

  const pass = page.locator("input[type='password'], input[name*='password' i]").first();
  const toggle = page.getByRole("button", { name: /show|hide/i }).first();

  if ((await pass.count()) && (await toggle.count())) {
    const before = await pass.getAttribute("type");
    await toggle.click();
    const after = await pass.getAttribute("type");
    row(before !== after ? "PASS" : "WARN", surface, "password_toggle", `type ${before} -> ${after}`);
  }

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function auditOnboarding(context) {
  const surface = "onboarding";
  const page = await makePage(context);
  await goto(page, surface, "/platform/onboarding");

  await visible(page, surface, "form, input, textarea, select", "setup_form", "Setup form/fields");
  await visible(page, surface, "a[href*='/c/']", "campaign_preview", "Campaign preview link");
  await visible(page, surface, "a[href*='/platform/dashboard'], button, .ff-button", "setup_actions", "Setup actions");

  const fields = page.locator("input:not([type='hidden']):not([disabled]), textarea:not([disabled])");
  const count = await fields.count();

  for (let i = 0; i < Math.min(count, 4); i++) {
    const field = fields.nth(i);
    const type = ((await field.getAttribute("type")) || "").toLowerCase();
    if (/checkbox|radio|file|button|submit/.test(type)) continue;
    await field.fill("Functional QA");
  }

  row(count ? "PASS" : "WARN", surface, "field_editability", `${count} editable field(s) found`);

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function auditDashboardLocked(context) {
  const surface = "dashboard_locked";
  const page = await makePage(context);
  await goto(page, surface, "/platform/dashboard", [403]);

  await visible(page, surface, "a[href*='/platform/login'], a[href*='login']", "locked_login", "Login link");
  await visible(page, surface, "a[href*='/platform/onboarding'], a[href*='onboarding']", "locked_setup", "Setup link");
  await visible(page, surface, "a[href*='/c/']", "locked_campaign", "Campaign link");

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function auditDashboardOperator(context) {
  const surface = "dashboard_operator";

  if (!TOKEN) {
    row("WARN", surface, "operator_token", "No FF_OPERATOR_ACCESS_TOKEN; skipping operator dashboard");
    return;
  }

  const page = await makePage(context);
  await goto(page, surface, `/platform/dashboard?access_token=${encodeURIComponent(TOKEN)}`);

  await visible(page, surface, "a[href*='/c/'], button, .ff-button", "operator_actions", "Operator actions");
  await visible(page, surface, "body", "operator_body", "Operator dashboard body");

  const actions = await page.locator("button:not([type='submit']), a.ff-button, .ff-button").evaluateAll((nodes) =>
    nodes.map((node) => ({
      text: (node.textContent || "").trim().replace(/\s+/g, " "),
      tag: node.tagName.toLowerCase(),
      href: node.getAttribute("href") || "",
      disabled: node.hasAttribute("disabled") || node.getAttribute("aria-disabled") === "true",
      visible: !!(node.offsetWidth || node.offsetHeight || node.getClientRects().length),
    }))
  );

  const safeActions = actions
    .filter((item) => item.visible)
    .filter((item) => !item.disabled)
    .filter((item) => !/delete|remove|trash|refund|send/i.test(item.text));

  if (safeActions.length) {
    row("PASS", surface, "operator_button_sample", `${safeActions.length} visible safe dashboard action(s) available`);
  } else {
    row("WARN", surface, "operator_button_sample", "No visible safe dashboard actions found");
  }

  await checkSameOriginLinks(page, surface);
  await pageHealth(page, surface);
  await page.close();
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });

  console.log("\nFutureFunded Functional Button Contracts");
  console.log("=======================================");
  console.log(`Base: ${BASE}`);
  console.log(`Campaign: ${SLUG}`);
  console.log(`Operator token: ${TOKEN ? "present" : "missing"}`);
  console.log("");

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    baseURL: BASE,
    viewport: { width: 1440, height: 1200 },
    ignoreHTTPSErrors: true,
    permissions: ["clipboard-read", "clipboard-write"],
  });

  try {
    const audits = [
      ["platform", auditPlatform],
      ["campaign", auditCampaign],
      ["login", auditLogin],
      ["onboarding", auditOnboarding],
      ["dashboard_locked", auditDashboardLocked],
      ["dashboard_operator", auditDashboardOperator],
    ];

    for (const [surface, audit] of audits) {
      try {
        await audit(context);
      } catch (error) {
        row("FAIL", surface, "audit_exception", error.message || String(error));
      }
    }
  } finally {
    await context.close();
    await browser.close();
  }

  const report = {
    status: failures ? "FAIL" : "PASS",
    baseUrl: BASE,
    campaignSlug: SLUG,
    generatedAt: new Date().toISOString(),
    counts: {
      total: rows.length,
      failures,
      warnings: rows.filter((item) => item.status === "WARN").length,
      passes: rows.filter((item) => item.status === "PASS").length,
    },
    results: rows,
  };

  fs.writeFileSync(path.join(OUT, "functional-button-contracts.json"), JSON.stringify(report, null, 2));

  const md = [
    "# FutureFunded Functional Button Contracts",
    "",
    `Status: **${report.status}**`,
    `Base: \`${BASE}\``,
    `Campaign: \`${SLUG}\``,
    `Generated: \`${report.generatedAt}\``,
    "",
    `Passes: **${report.counts.passes}**`,
    `Warnings: **${report.counts.warnings}**`,
    `Failures: **${report.counts.failures}**`,
    "",
    "| Status | Surface | Code | Message |",
    "|---|---|---|---|",
    ...rows.map((item) => `| ${item.status} | ${item.surface} | \`${item.code}\` | ${item.message.replace(/\|/g, "\\|")} |`),
    "",
  ].join("\n");

  fs.writeFileSync(path.join(OUT, "functional-button-contracts.md"), md);

  console.log("");
  console.log(`Report: ${path.join(OUT, "functional-button-contracts.md")}`);
  console.log(`JSON:   ${path.join(OUT, "functional-button-contracts.json")}`);
  console.log("");
  console.log(`FUNCTIONAL BUTTON CONTRACTS: ${report.status}`);

  process.exit(failures ? 1 : 0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
