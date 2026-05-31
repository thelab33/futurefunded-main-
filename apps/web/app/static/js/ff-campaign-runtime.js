/*
  FutureFunded Campaign Runtime
  Marker: ff-campaign-runtime-single-authority-v2

  Owns campaign modal open/close and amount sync.
  Does NOT own Stripe continuation. ff-checkout-direct.js owns Continue -> Stripe.
*/
(() => {
  "use strict";

  const VERSION = "ff-campaign-runtime-single-authority-v2";
  const doc = document;
  const root = doc.documentElement;
  const body = doc.body;

  if (window.FutureFundedCampaignRuntime?.version === VERSION) return;

  const $ = (selector, scope = doc) => {
    try { return scope.querySelector(selector); } catch { return null; }
  };

  const $$ = (selector, scope = doc) => {
    try { return Array.from(scope.querySelectorAll(selector)); } catch { return []; }
  };

  const checkoutSelector = "#checkout,[data-ff-embedded-checkout-shell],[data-ff-checkout-sheet],[data-ff-checkout-modal],.ff-embeddedCheckout,.ff-checkoutModal";
  const checkoutOpenSelector = "[data-ff-open-checkout],[data-ff-donate-cta],[data-ff-donate-trigger],[data-ff-payment-trigger],[data-ff-donate-submit],.ff-donateSubmit";
  const checkoutCloseSelector = "[data-ff-close-embedded-checkout],[data-ff-close-checkout],[data-ff-checkout-close],[aria-label='Close checkout']";

  const sponsorSelector = "#sponsor-modal,[data-ff-sponsor-modal],.ff-sponsorModal";
  const sponsorOpenSelector = "[data-ff-open-sponsor],[data-ff-sponsor-trigger],[data-ff-sponsor-cta]";
  const sponsorCloseSelector = "[data-ff-sponsor-close],[data-ff-close-sponsor],[aria-label='Close sponsor options']";

  const shareSelector = "#qr-modal,[data-ff-share-drawer],[data-ff-qr-modal],.ff-shareDrawer";
  const shareOpenSelector = "[data-ff-share],[data-ff-share-trigger],[data-ff-qr-trigger]";
  const shareCloseSelector = "[data-ff-share-close],[data-ff-close-qr-modal],[aria-label='Close share drawer']";

  const continueSelector = "[data-ff-start-embedded-checkout],[data-ff-checkout-continue],[data-ff-payment-continue],[data-ff-submit-checkout],.ff-checkoutContinue";

  const modals = {
    checkout: { selector: checkoutSelector, rootClass: "ff-checkout-open", stateAttr: "data-ff-checkout-state" },
    sponsor: { selector: sponsorSelector, rootClass: "ff-sponsor-open", stateAttr: "data-ff-sponsor-state" },
    share: { selector: shareSelector, rootClass: "ff-share-open", stateAttr: "data-ff-share-state" },
  };

  function isCampaignPage() {
    return Boolean(
      root?.getAttribute("data-ff-page") === "campaign" ||
      body?.classList.contains("ff-campaignBody") ||
      $(".ff-campaignPage")
    );
  }

  function nodeFor(name) {
    return $(modals[name]?.selector || "");
  }

  function isVisible(node) {
    if (!node || node.hidden || node.getAttribute("aria-hidden") === "true") return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      Number(style.opacity || 1) !== 0 &&
      rect.width > 10 &&
      rect.height > 10;
  }

  function anyVisibleModal() {
    return Object.keys(modals).some((name) => isVisible(nodeFor(name)));
  }

  function syncAmount(trigger) {
    if (!trigger) return;

    const raw =
      trigger.getAttribute("data-ff-checkout-amount") ||
      trigger.getAttribute("data-ff-donation-amount") ||
      trigger.getAttribute("data-ff-amount") ||
      "";

    const amount = Number(String(raw).replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(amount) || amount <= 0) return;

    window.__ffSelectedDonationAmountCents = Math.round(amount * 100);

    $$("[data-ff-checkout-amount],[data-ff-donation-amount],[data-ff-amount]").forEach((el) => {
      const value = Number(String(
        el.getAttribute("data-ff-checkout-amount") ||
        el.getAttribute("data-ff-donation-amount") ||
        el.getAttribute("data-ff-amount") ||
        ""
      ).replace(/[^0-9.]/g, ""));

      const selected = Number.isFinite(value) && value === amount;
      el.classList.toggle("is-selected", selected);
      if (el.matches("button,[role='button']")) el.setAttribute("aria-pressed", selected ? "true" : "false");
    });

    $$("[data-ff-checkout-custom-input],[data-ff-custom-amount],input[name='custom_amount']").forEach((input) => {
      if ("value" in input) input.value = String(amount);
    });

    $$("[data-ff-start-embedded-checkout],[data-ff-checkout-continue],.ff-checkoutContinue").forEach((button) => {
      button.setAttribute("data-ff-checkout-amount", String(amount));
      if (/continue/i.test(button.textContent || "")) button.textContent = `Continue with $${amount}`;
    });

    $$("[data-ff-checkout-payment-summary-amount],[data-ff-summary-amount]").forEach((el) => {
      el.textContent = `$${amount} donation`;
    });
  }

  function openModal(name, trigger = null) {
    const cfg = modals[name];
    const node = nodeFor(name);
    if (!cfg || !node) return false;

    if (name === "checkout") syncAmount(trigger);

    node.hidden = false;
    node.removeAttribute("hidden");
    node.setAttribute("aria-hidden", "false");
    node.setAttribute("data-ff-state", "open");
    node.setAttribute("data-ff-modal-state", "open");
    node.setAttribute(cfg.stateAttr, "open");
    node.classList.add("is-open", "ff-is-open");

    root.classList.add("ff-modal-open", cfg.rootClass);
    body?.classList.add("ff-modal-open", cfg.rootClass);
    root.setAttribute("data-ff-modal-open", "true");
    body?.setAttribute("data-ff-modal-open", "true");

    const focusTarget = $("[autofocus],input,button,[href],[tabindex]:not([tabindex='-1'])", node);
    setTimeout(() => {
      try { focusTarget?.focus?.({ preventScroll: true }); } catch {}
    }, 40);

    window.dispatchEvent(new CustomEvent("ff:campaign-runtime:open", { detail: { name, version: VERSION } }));
    return true;
  }

  function closeModal(name) {
    const cfg = modals[name];
    const node = nodeFor(name);
    if (!cfg || !node) return false;

    node.hidden = true;
    node.setAttribute("hidden", "");
    node.setAttribute("aria-hidden", "true");
    node.setAttribute("data-ff-state", "closed");
    node.setAttribute("data-ff-modal-state", "closed");
    node.setAttribute(cfg.stateAttr, "closed");
    node.classList.remove("is-open", "ff-is-open");

    root.classList.remove(cfg.rootClass);
    body?.classList.remove(cfg.rootClass);

    if (!anyVisibleModal()) {
      root.classList.remove("ff-modal-open");
      body?.classList.remove("ff-modal-open");
      root.removeAttribute("data-ff-modal-open");
      body?.removeAttribute("data-ff-modal-open");
    }

    return true;
  }

  function handleClick(event) {
    if (!isCampaignPage()) return;

    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    if (target.closest(continueSelector)) {
      return; // Stripe continuation belongs to ff-checkout-direct.js.
    }

    const checkoutClose = target.closest(checkoutCloseSelector);
    if (checkoutClose) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      closeModal("checkout");
      return;
    }

    const sponsorClose = target.closest(sponsorCloseSelector);
    if (sponsorClose) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      closeModal("sponsor");
      return;
    }

    const shareClose = target.closest(shareCloseSelector);
    if (shareClose) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      closeModal("share");
      return;
    }

    const checkoutOpen = target.closest(checkoutOpenSelector);
    if (checkoutOpen) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      openModal("checkout", checkoutOpen);
      return;
    }

    const sponsorOpen = target.closest(sponsorOpenSelector);
    if (sponsorOpen) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      openModal("sponsor", sponsorOpen);
      return;
    }

    const shareOpen = target.closest(shareOpenSelector);
    if (shareOpen) {
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      openModal("share", shareOpen);
      return;
    }

    const amountButton = target.closest("[data-ff-amount-button],[data-ff-checkout-amount],[data-ff-donation-amount],[data-ff-amount]");
    if (amountButton) syncAmount(amountButton);
  }

  function boot() {
    if (!isCampaignPage()) return;

    root.classList.remove("ff-no-js");
    root.classList.add("ff-js");
    body?.classList.add("ff-campaign-runtime-ready");

    doc.addEventListener("click", handleClick, true);
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape") Object.keys(modals).forEach(closeModal);
    }, true);

    window.FutureFundedCampaignRuntime = { version: VERSION, open: openModal, close: closeModal, selectAmount: syncAmount };
    window.FutureFundedCampaign = {
      ...(window.FutureFundedCampaign || {}),
      openCheckout: (trigger = null) => openModal("checkout", trigger),
      closeCheckout: () => closeModal("checkout"),
      getDonationAmount: () => Number(window.__ffSelectedDonationAmountCents || 5000) / 100,
    };

    window.dispatchEvent(new CustomEvent("ff:campaign-runtime:ready", { detail: { version: VERSION } }));
  }

  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
