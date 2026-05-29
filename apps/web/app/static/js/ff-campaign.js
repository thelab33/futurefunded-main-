/*!
 * FutureFunded Campaign Safe Runtime
 * Marker: ff-campaign-safe-runtime-v1
 *
 * Emergency purpose:
 * Keep the campaign page visible, scrollable, and contract-safe while the
 * heavier campaign runtime is isolated. Checkout/direct payment scripts remain
 * loaded separately and should continue owning payment behavior.
 */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;
  var body = doc.body;

  if (!root || !body) return;

  root.classList.remove("ff-no-js");
  root.classList.add("ff-js");
  body.classList.add("ff-campaign-runtime-safe");

  function qs(selector, scope) {
    return Array.prototype.slice.call((scope || doc).querySelectorAll(selector));
  }

  function isVisible(el) {
    if (!el) return false;
    if (el.hidden || el.getAttribute("aria-hidden") === "true") return false;

    var style = window.getComputedStyle(el);
    var rect = el.getBoundingClientRect();

    return (
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      Number(style.opacity || 1) !== 0 &&
      rect.width > 8 &&
      rect.height > 8
    );
  }

  function visibleModalExists() {
    return qs([
      "#checkout",
      "#sponsor-modal",
      "#qr-modal",
      "[data-ff-checkout-modal]",
      "[data-ff-sponsor-modal]",
      "[data-ff-qr-modal]",
      "[data-ff-share-drawer]",
      ".ff-checkoutModal",
      ".ff-embeddedCheckout",
      ".ff-sponsorModal",
      ".ff-shareDrawer"
    ].join(",")).some(isVisible);
  }

  function unlockIfNoModal() {
    if (visibleModalExists()) return;

    root.classList.remove(
      "ff-modal-open",
      "ff-checkout-open",
      "ff-checkoutOpen",
      "ff-embeddedCheckoutOpen",
      "ff-sponsor-open",
      "ff-share-open",
      "ff-qr-open"
    );

    body.classList.remove(
      "ff-modal-open",
      "ff-checkout-open",
      "ff-checkoutOpen",
      "ff-embeddedCheckoutOpen",
      "ff-sponsor-open",
      "ff-share-open",
      "ff-qr-open"
    );

    root.style.overflow = "";
    body.style.overflow = "";
    body.style.height = "";
  }

  function failOpenReveal() {
    qs("[data-ff-reveal], [data-ff-animate], .ff-reveal, .ff-revealItem, .ff-animateIn, .ff-idle, .is-idle").forEach(function (el) {
      if (el.hidden || el.getAttribute("aria-hidden") === "true") return;

      el.style.opacity = "1";
      el.style.visibility = "visible";
      el.style.transform = "none";
      el.style.translate = "none";
      el.style.scale = "1";
      el.classList.remove("ff-idle", "is-idle");
      el.classList.add("ff-reveal-ready");
    });
  }

  function closeModal(el) {
    if (!el) return;
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
    el.setAttribute("data-ff-state", "closed");
    unlockIfNoModal();
  }

  function openModal(el) {
    if (!el) return;
    el.hidden = false;
    el.setAttribute("aria-hidden", "false");
    el.setAttribute("data-ff-state", "open");
    root.classList.add("ff-modal-open");
    body.classList.add("ff-modal-open");
  }

  function bindSponsorFallback() {
    var modal =
      doc.querySelector("[data-ff-sponsor-modal]") ||
      doc.querySelector("#sponsor-modal") ||
      doc.querySelector(".ff-sponsorModal");

    qs("[data-ff-open-sponsor], [data-ff-sponsor-trigger]").forEach(function (trigger) {
      if (trigger.__ffSponsorSafeBound) return;
      trigger.__ffSponsorSafeBound = true;

      trigger.addEventListener("click", function (event) {
        if (!modal) return;
        event.preventDefault();
        openModal(modal);
      });
    });

    qs("[data-ff-close-sponsor], [data-ff-modal-close], [data-ff-close-modal]").forEach(function (trigger) {
      if (trigger.__ffModalSafeBound) return;
      trigger.__ffModalSafeBound = true;

      trigger.addEventListener("click", function (event) {
        var target =
          trigger.closest("[data-ff-sponsor-modal], #sponsor-modal, .ff-sponsorModal, [data-ff-qr-modal], #qr-modal, [data-ff-share-drawer]");

        if (!target) return;
        event.preventDefault();
        closeModal(target);
      });
    });
  }

  function bindShareFallback() {
    qs("[data-ff-share-trigger]").forEach(function (trigger) {
      if (trigger.__ffShareSafeBound) return;
      trigger.__ffShareSafeBound = true;

      trigger.addEventListener("click", function (event) {
        var title = doc.title || "FutureFunded campaign";
        var url = window.location.href;

        if (navigator.share) {
          event.preventDefault();
          navigator.share({ title: title, url: url }).catch(function () {});
          return;
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
          event.preventDefault();
          navigator.clipboard.writeText(url).catch(function () {});
        }
      });
    });
  }

  function markDonationTriggers() {
    qs("[data-ff-open-checkout], [data-ff-donate-trigger], [data-ff-payment-trigger]").forEach(function (trigger) {
      trigger.setAttribute("data-ff-safe-runtime-observed", "true");
    });
  }

  function boot() {
    failOpenReveal();
    unlockIfNoModal();
    bindSponsorFallback();
    bindShareFallback();
    markDonationTriggers();

    window.dispatchEvent(new CustomEvent("ff:campaign-safe-runtime-ready", {
      detail: {
        runtime: "ff-campaign-safe-runtime-v1"
      }
    }));
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  window.addEventListener("pageshow", function () {
    failOpenReveal();
    unlockIfNoModal();
  });

  doc.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;

    qs("[data-ff-sponsor-modal], #sponsor-modal, .ff-sponsorModal, [data-ff-qr-modal], #qr-modal, [data-ff-share-drawer]").forEach(function (modal) {
      if (isVisible(modal)) closeModal(modal);
    });
  });
})();

