/*
  FutureFunded Checkout Direct Authority
  File: apps/web/app/static/js/ff-checkout-direct.js
  Version: checkout-direct-authority-v3

  Owns:
  - visible public donation modal Continue button
  - donor email validation
  - donor-only payload construction
  - POST to /c/<slug>/checkout/session via XMLHttpRequest
  - redirect to Stripe hosted checkout

  Does NOT own:
  - checkout modal open/close
  - amount UI sync
  - sponsor package UI
  - share/QR drawer
*/

(() => {
  "use strict";

  const VERSION = "checkout-direct-authority-v3";
  const GLOBAL_KEY = "FutureFundedCheckoutDirect";

  if (window[GLOBAL_KEY]?.version === VERSION) return;

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const LOCK_MS = 14000;

  const SELECTORS = {
    checkoutShell: [
      "[data-ff-embedded-checkout-shell]",
      ".ff-embeddedCheckout",
      ".ff-checkoutModal",
      "[role='dialog'][aria-modal='true']"
    ].join(","),

    continueButton: [
      "[data-ff-start-embedded-checkout]",
      "[data-ff-checkout-continue]",
      "[data-ff-payment-continue]",
      "[data-ff-submit-checkout]",
      ".ff-checkoutContinue"
    ].join(","),

    donorEmail: [
      "[data-ff-checkout-donor-email]",
      "[data-ff-donor-email]",
      "[data-ff-receipt-email]",
      "input[type='email']",
      "input[name*='email' i]",
      "input[id*='email' i]"
    ].join(","),

    donorName: [
      "[data-ff-checkout-donor-name]",
      "[data-ff-donor-name]",
      "input[name*='name' i]",
      "input[id*='name' i]"
    ].join(","),

    amountSource: [
      "[data-ff-checkout-amount][aria-pressed='true']",
      "[data-ff-checkout-amount].is-selected",
      "[data-ff-donation-amount][aria-pressed='true']",
      "[data-ff-donation-amount].is-selected",
      "[data-ff-amount-cents][aria-pressed='true']",
      "[data-ff-amount-cents].is-selected",
      "[data-ff-selected='true']",
      ".ff-checkoutAmount.is-selected",
      ".ff-amountButton.is-selected"
    ].join(","),

    customAmount: [
      "[data-ff-checkout-custom-input]",
      "[data-ff-custom-amount]",
      "input[name='custom_amount']",
      "input[name*='amount' i]",
      "input[type='number']"
    ].join(","),

    status: "[data-ff-checkout-direct-status]",
    campaignPage: "[data-ff-campaign-page], [data-campaign-slug]",
    csrf: "meta[name='csrf-token'], input[name='csrf_token'], input[name='csrfmiddlewaretoken']"
  };

  const state = {
    inFlight: false,
    lockUntil: 0,
    lastButton: null
  };

  const qsa = (selector, root = document) => {
    try {
      return Array.from(root.querySelectorAll(selector));
    } catch {
      return [];
    }
  };

  const qs = (selector, root = document) => {
    try {
      return root.querySelector(selector);
    } catch {
      return null;
    }
  };

  function log(...args) {
    console.info("[FutureFunded checkout direct]", ...args);
  }

  function textOf(node) {
    return String(node?.textContent || node?.value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function visible(node) {
    if (!node) return false;
    if (node.hidden) return false;
    if (node.getAttribute?.("aria-hidden") === "true") return false;

    const rect = node.getBoundingClientRect?.();
    const css = window.getComputedStyle?.(node);

    return Boolean(
      rect &&
      rect.width > 0 &&
      rect.height > 0 &&
      css &&
      css.display !== "none" &&
      css.visibility !== "hidden" &&
      Number(css.opacity || 1) !== 0
    );
  }

  function campaignSlug() {
    const pathMatch = window.location.pathname.match(/\/c\/([^/?#]+)/);
    const page = qs(SELECTORS.campaignPage);

    return (
      page?.getAttribute("data-campaign-slug") ||
      page?.getAttribute("data-ff-campaign-slug") ||
      document.body?.getAttribute("data-ff-campaign-slug") ||
      pathMatch?.[1] ||
      "connect-atx-elite"
    );
  }

  function checkoutModal() {
    const candidates = qsa(SELECTORS.checkoutShell);

    return (
      candidates.find((node) => visible(node) && /complete your donation|secure donation|choose how you want to help/i.test(textOf(node))) ||
      candidates.find(visible) ||
      candidates[0] ||
      null
    );
  }

  function donorEmail(root) {
    return qsa(SELECTORS.donorEmail, root || document)
      .find((node) => node instanceof HTMLInputElement && visible(node)) || null;
  }

  function donorName(root) {
    return qsa(SELECTORS.donorName, root || document)
      .find((node) => node instanceof HTMLInputElement && visible(node)) || null;
  }

  function readCentsFromNode(node) {
    if (!node) return 0;

    const rawCents =
      node.getAttribute("data-ff-amount-cents") ||
      node.getAttribute("data-amount-cents") ||
      node.dataset?.ffAmountCents ||
      node.dataset?.amountCents;

    if (rawCents && Number(rawCents) > 0) return Math.round(Number(rawCents));

    const rawDollars =
      node.getAttribute("data-ff-checkout-amount") ||
      node.getAttribute("data-ff-donation-amount") ||
      node.getAttribute("data-ff-amount") ||
      node.getAttribute("data-amount") ||
      node.dataset?.ffCheckoutAmount ||
      node.dataset?.ffDonationAmount ||
      node.dataset?.ffAmount ||
      node.dataset?.amount ||
      textOf(node);

    const dollars = Number(String(rawDollars || "").replace(/[^0-9.]/g, ""));
    return Number.isFinite(dollars) && dollars > 0 ? Math.round(dollars * 100) : 0;
  }

  function selectedAmountCents(root) {
    const scopedRoot = root || document;

    const custom = qsa(SELECTORS.customAmount, scopedRoot).find((node) => {
      if (!(node instanceof HTMLInputElement)) return false;
      if (!visible(node)) return false;
      const value = Number(String(node.value || "").replace(/[^0-9.]/g, ""));
      return Number.isFinite(value) && value > 0;
    });

    if (custom) return Math.max(100, Math.round(Number(custom.value) * 100));

    const selected = qsa(SELECTORS.amountSource, scopedRoot).find(visible);
    const selectedCents = readCentsFromNode(selected);
    if (selectedCents > 0) return Math.max(100, selectedCents);

    const globalAmount =
      Number(window.__ffSelectedDonationAmountCents) ||
      Number(window.FutureFundedCampaign?.getDonationAmount?.() * 100) ||
      Number(window.ffGetDonationAmount?.() * 100);

    if (Number.isFinite(globalAmount) && globalAmount > 0) return Math.max(100, Math.round(globalAmount));

    const textMatch = textOf(scopedRoot).match(/Continue with \$\s*([0-9]+(?:\.[0-9]{1,2})?)/i);
    if (textMatch) return Math.max(100, Math.round(Number(textMatch[1]) * 100));

    return 5000;
  }

  function continueButtons(root) {
    const scopedRoot = root || checkoutModal() || document;

    return qsa(
      [
        SELECTORS.continueButton,
        "button",
        "a",
        "[role='button']"
      ].join(","),
      scopedRoot
    )
      .filter(visible)
      .filter((node) => {
        if (node.matches?.(SELECTORS.continueButton)) return true;
        return /continue with|continue to payment|secure payment|complete payment|opening secure checkout/i.test(textOf(node));
      });
  }

  function getCsrfToken() {
    const node = qs(SELECTORS.csrf);
    return node?.getAttribute?.("content") || node?.value || "";
  }

  function statusMessage(root, message, tone = "info") {
    if (!root) return;

    let node = qs(SELECTORS.status, root);

    if (!node) {
      node = document.createElement("p");
      node.setAttribute("data-ff-checkout-direct-status", "true");
      node.setAttribute("role", "status");
      node.setAttribute("aria-live", "polite");
      node.className = "ff-checkoutDirectStatus";

      const email = donorEmail(root);
      const anchor =
        email?.closest("label, .ff-checkoutField, .ff-checkoutDonorFields") ||
        continueButtons(root)[0];

      if (anchor?.parentNode) {
        anchor.parentNode.insertBefore(node, anchor.nextSibling);
      } else {
        root.appendChild(node);
      }
    }

    node.textContent = message;
    node.setAttribute("data-tone", tone);
  }

  function setButtonBusy(button, busy) {
    if (!button) return;

    if (busy) {
      button.setAttribute("aria-busy", "true");
      button.setAttribute("data-ff-checkout-direct-busy", "true");
      button.dataset.ffOriginalText = button.dataset.ffOriginalText || textOf(button) || "Continue";
      button.textContent = "Opening secure checkout…";
    } else {
      button.removeAttribute("aria-busy");
      button.removeAttribute("data-ff-checkout-direct-busy");

      if (button.dataset.ffOriginalText) {
        button.textContent = button.dataset.ffOriginalText;
      }
    }
  }

  function resetLocks() {
    state.inFlight = false;
    state.lockUntil = 0;

    qsa("[data-ff-checkout-direct-busy='true'], [data-ff-checkout-pending='true']").forEach((node) => {
      node.removeAttribute("aria-busy");
      node.removeAttribute("data-ff-checkout-direct-busy");
      node.removeAttribute("data-ff-checkout-pending");
      node.removeAttribute("data-ff-checkout-pending-until");

      if (node.dataset?.ffOriginalText) {
        node.textContent = node.dataset.ffOriginalText;
      }
    });
  }

  function lockSubmit(button) {
    const now = Date.now();

    if (state.inFlight && state.lockUntil > now) return false;

    state.inFlight = true;
    state.lockUntil = now + LOCK_MS;
    state.lastButton = button || null;

    if (button) {
      button.setAttribute("data-ff-checkout-pending", "true");
      button.setAttribute("data-ff-checkout-pending-until", String(state.lockUntil));
    }

    window.setTimeout(() => {
      if (state.lockUntil <= Date.now()) resetLocks();
    }, LOCK_MS + 100);

    return true;
  }

  function buildPayload(root) {
    const emailNode = donorEmail(root);
    const email = String(emailNode?.value || "").trim();
    const name = String(donorName(root)?.value || "").trim();
    const amountCents = Math.max(100, selectedAmountCents(root));
    const slug = campaignSlug();

    return {
      flow: "donation",
      kind: "donation",
      type: "donation",
      payment_flow: "donation",
      checkout_mode: "donation",
      amount_cents: amountCents,
      amountCents,
      amount: amountCents / 100,
      donor_email: email,
      customer_email: email,
      email,
      donor_name: name,
      name,
      campaign_slug: slug,
      source: VERSION
    };
  }

  function postJson(url, payload) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.open("POST", url, true);
      xhr.withCredentials = true;
      xhr.timeout = 20000;
      xhr.setRequestHeader("Accept", "application/json");
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

      const csrf = getCsrfToken();
      if (csrf) {
        xhr.setRequestHeader("X-CSRFToken", csrf);
        xhr.setRequestHeader("X-CSRF-Token", csrf);
      }

      xhr.onload = () => {
        let data = {};
        const raw = xhr.responseText || "";

        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          data = { raw };
        }

        resolve({
          ok: xhr.status >= 200 && xhr.status < 300,
          status: xhr.status,
          data,
          raw
        });
      };

      xhr.onerror = () => reject(new Error("Network error while creating checkout session."));
      xhr.ontimeout = () => reject(new Error("Checkout session request timed out."));
      xhr.send(JSON.stringify(payload));
    });
  }

  function checkoutUrlFrom(data) {
    return (
      data?.url ||
      data?.checkout_url ||
      data?.checkoutUrl ||
      data?.redirect_url ||
      data?.redirectUrl ||
      ""
    );
  }

  async function start(button = null) {
    const root = checkoutModal();

    if (!root) {
      log("blocked: no visible checkout modal");
      return false;
    }

    const emailNode = donorEmail(root);
    const email = String(emailNode?.value || "").trim();

    if (!emailNode || !EMAIL_RE.test(email)) {
      emailNode?.setAttribute("aria-invalid", "true");
      emailNode?.focus?.({ preventScroll: false });
      statusMessage(root, "Add a valid receipt email before continuing to Stripe.", "error");
      log("blocked: invalid email");
      return false;
    }

    emailNode.removeAttribute("aria-invalid");

    if (!lockSubmit(button)) {
      log("blocked: checkout already in flight");
      return false;
    }

    const slug = campaignSlug();
    const endpoint = `/c/${encodeURIComponent(slug)}/checkout/session`;
    const payload = buildPayload(root);

    setButtonBusy(button, true);
    statusMessage(root, "Creating secure Stripe checkout…", "info");

    window.dispatchEvent(new CustomEvent("ff:checkout:direct:start", {
      detail: {
        version: VERSION,
        endpoint,
        amountCents: payload.amount_cents
      }
    }));

    let result;

    try {
      result = await postJson(endpoint, payload);
    } catch (error) {
      console.error("[FutureFunded checkout direct] request error", error);
      resetLocks();
      setButtonBusy(button, false);
      statusMessage(root, "Checkout could not start. Please try again.", "error");
      window.dispatchEvent(new CustomEvent("ff:checkout:error", { detail: { version: VERSION, error: String(error) } }));
      return false;
    }

    if (!result.ok) {
      resetLocks();
      setButtonBusy(button, false);
      statusMessage(
        root,
        result.data?.error || result.data?.message || `Checkout failed with ${result.status}.`,
        "error"
      );
      window.dispatchEvent(new CustomEvent("ff:checkout:error", {
        detail: {
          version: VERSION,
          status: result.status,
          data: result.data
        }
      }));
      return false;
    }

    const checkoutUrl = checkoutUrlFrom(result.data);

    if (!checkoutUrl || !/^https:\/\/checkout\.stripe\.com\//.test(checkoutUrl)) {
      resetLocks();
      setButtonBusy(button, false);
      statusMessage(root, "Stripe session was created, but no checkout URL was returned.", "error");
      console.error("[FutureFunded checkout direct] missing Stripe checkout URL", result.data);
      window.dispatchEvent(new CustomEvent("ff:checkout:error", {
        detail: {
          version: VERSION,
          status: result.status,
          reason: "missing_checkout_url"
        }
      }));
      return false;
    }

    statusMessage(root, "Redirecting to Stripe Checkout…", "success");
    window.dispatchEvent(new CustomEvent("ff:checkout:direct:redirect", {
      detail: {
        version: VERSION,
        amountCents: payload.amount_cents
      }
    }));

    window.location.assign(checkoutUrl);
    return true;
  }

  function ownButton(button) {
    if (!button || button.dataset.ffCheckoutDirectOwned === VERSION) return;

    button.dataset.ffCheckoutDirectOwned = VERSION;
    button.removeAttribute("disabled");

    const handler = (event) => {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation?.();
      start(button);
    };

    button.addEventListener("click", handler, true);
    button.addEventListener("pointerup", handler, true);
    button.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") handler(event);
    }, true);
  }

  function bind() {
    const root = checkoutModal();
    if (!root) return;

    continueButtons(root).forEach(ownButton);
  }

  function boot() {
    bind();

    document.addEventListener("click", bind, true);
    document.addEventListener("pointerdown", bind, true);

    const observer = new MutationObserver(bind);
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["hidden", "aria-hidden", "class", "data-ff-checkout-state"]
    });

    window.addEventListener("pageshow", resetLocks);
    window.addEventListener("popstate", resetLocks);
    window.addEventListener("focus", () => window.setTimeout(resetLocks, 120));

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        window.setTimeout(resetLocks, 120);
      }
    });

    ["ff:checkout:error", "ff:checkout:closed", "ff:modal:closed", "ff:payment:error"].forEach((eventName) => {
      window.addEventListener(eventName, resetLocks);
      document.addEventListener(eventName, resetLocks);
    });

    window[GLOBAL_KEY] = {
      installed: true,
      version: VERSION,
      bind,
      start,
      resetLocks,
      modal: checkoutModal,
      continueButtons: () => continueButtons(checkoutModal()),
      donorEmail: () => donorEmail(checkoutModal()),
      selectedAmountCents: () => selectedAmountCents(checkoutModal())
    };

    log("installed", VERSION);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
