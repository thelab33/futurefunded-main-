#!/usr/bin/env node
import { chromium } from "playwright";

const base = process.env.FF_BASE_URL || process.argv[2] || "https://getfuturefunded.com";
const slug = process.env.FF_CAMPAIGN_SLUG || process.argv[3] || "connect-atx-elite";
const url = `${base.replace(/\/$/, "")}/c/${slug}?csp_trace=${Date.now()}`;

const browser = await chromium.launch({
  headless: process.env.FF_HEADLESS !== "0",
});

const page = await browser.newPage({
  viewport: { width: 1366, height: 900 },
});

const findings = {
  ok: true,
  url,
  cspViolations: [],
  consoleErrors: [],
  styleMutationCalls: [],
  checkoutRequests: [],
  notes: [],
};

await page.addInitScript(() => {
  window.__ffCspTrace = { styleMutationCalls: [], cspViolations: [] };

  const pushTrace = (kind, target, prop, value) => {
    try {
      const stack = new Error().stack || "";
      window.__ffCspTrace.styleMutationCalls.push({
        kind,
        target,
        prop,
        value,
        stack: stack.split("\n").slice(0, 8).join("\n"),
      });
    } catch {}
  };

  document.addEventListener("securitypolicyviolation", (event) => {
    window.__ffCspTrace.cspViolations.push({
      blockedURI: event.blockedURI,
      violatedDirective: event.violatedDirective,
      effectiveDirective: event.effectiveDirective,
      sourceFile: event.sourceFile,
      lineNumber: event.lineNumber,
      columnNumber: event.columnNumber,
      sample: event.sample,
      disposition: event.disposition,
    });
  });

  const originalSetAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function patchedSetAttribute(name, value) {
    if (String(name).toLowerCase() === "style") {
      pushTrace("setAttribute(style)", this.tagName, name, String(value).slice(0, 200));
    }
    return originalSetAttribute.apply(this, arguments);
  };

  const originalCreateElement = Document.prototype.createElement;
  Document.prototype.createElement = function patchedCreateElement(name, options) {
    const el = originalCreateElement.call(this, name, options);
    if (String(name).toLowerCase() === "style") {
      pushTrace("createElement(style)", "STYLE", "style", "");
    }
    return el;
  };

  const originalSetProperty = CSSStyleDeclaration.prototype.setProperty;
  CSSStyleDeclaration.prototype.setProperty = function patchedSetProperty(prop, value, priority) {
    pushTrace("style.setProperty", "CSSStyleDeclaration", prop, String(value).slice(0, 200));
    return originalSetProperty.apply(this, arguments);
  };
});

page.on("console", (msg) => {
  const text = msg.text();
  if (msg.type() === "error" || /content security policy|inline style/i.test(text)) {
    findings.consoleErrors.push({ type: msg.type(), text });
  }
});

page.on("request", (req) => {
  if (req.url().includes("/checkout/session")) {
    findings.checkoutRequests.push({
      method: req.method(),
      url: req.url(),
      postData: req.postData(),
    });
  }
});

try {
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });

  const modalAlreadyOpen = await page.evaluate(() => {
    const shell = document.querySelector("[data-ff-embedded-checkout-shell]");
    if (!shell) return false;
    const aria = shell.getAttribute("aria-hidden");
    const hidden = shell.hidden;
    const rect = shell.getBoundingClientRect();
    return aria === "false" && !hidden && rect.width > 0 && rect.height > 0;
  });

  if (modalAlreadyOpen) {
    findings.notes.push("Checkout modal was already open on page load; skipped trigger click.");
  } else {
    const clicked = await page.evaluate(() => {
      const candidates = [
        ...document.querySelectorAll("[data-ff-open-checkout], [data-ff-donate-trigger], button, a"),
      ].filter((node) => {
        if (node.closest("[data-ff-embedded-checkout-shell]")) return false;
        const text = `${node.textContent || ""} ${node.getAttribute("aria-label") || ""}`.toLowerCase();
        const hasHook = node.matches("[data-ff-open-checkout], [data-ff-donate-trigger]");
        const looksDonate = /donate|give|support|checkout/.test(text);
        const rect = node.getBoundingClientRect();
        return (hasHook || looksDonate) && rect.width > 0 && rect.height > 0;
      });

      const target = candidates[0];
      if (!target) return false;
      target.scrollIntoView({ block: "center", inline: "center" });
      target.click();
      return true;
    });

    findings.notes.push(clicked ? "Clicked checkout trigger via DOM click." : "No checkout trigger found.");
  }

  await page.waitForTimeout(2500);

  await page.evaluate(() => {
    const email =
      document.querySelector('input[type="email"]') ||
      document.querySelector('[name*="email" i]');

    if (email) {
      email.value = `receipt+csp-${Date.now()}@example.com`;
      email.dispatchEvent(new Event("input", { bubbles: true }));
      email.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  await page.waitForTimeout(400);

  const submitted = await page.evaluate(() => {
    const shell = document.querySelector("[data-ff-embedded-checkout-shell]") || document;
    const buttons = [...shell.querySelectorAll("button, [role='button'], a")];
    const target = buttons.find((node) => {
      const text = `${node.textContent || ""} ${node.getAttribute("aria-label") || ""}`.toLowerCase();
      return /continue|checkout|donate|pay/.test(text);
    });

    if (!target) return false;
    target.scrollIntoView({ block: "center", inline: "center" });
    target.click();
    return true;
  });

  findings.notes.push(submitted ? "Clicked checkout submit via DOM click." : "No checkout submit found.");

  await page.waitForTimeout(3500);
} catch (error) {
  findings.ok = false;
  findings.notes.push(`${error.name || "Error"}: ${error.message || String(error)}`);
}

findings.cspViolations = await page.evaluate(() => window.__ffCspTrace?.cspViolations || []).catch(() => []);
findings.styleMutationCalls = await page.evaluate(() => window.__ffCspTrace?.styleMutationCalls || []).catch(() => []);

await browser.close();

const hasInlineStyleError = findings.consoleErrors.some((x) =>
  /inline style|content security policy/i.test(x.text)
);

if (hasInlineStyleError || findings.cspViolations.length) {
  findings.ok = false;
}

console.log(JSON.stringify(findings, null, 2));

if (!findings.ok) process.exitCode = 2;
