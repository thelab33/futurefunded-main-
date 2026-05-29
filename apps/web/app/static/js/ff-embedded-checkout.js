(() => {
  "use strict";

  /*
   * FutureFunded embedded checkout compatibility shim.
   *
   * This file intentionally remains a no-op compatibility layer so older
   * templates, audits, and cache paths that expect js/ff-embedded-checkout.js
   * stay contract-safe without double-binding checkout events.
   *
   * Runtime owners:
   * - ff-campaign.js: modal open/close + amount sync
   * - ff-checkout-direct.js: donor checkout submit + Stripe redirect
   */

  window.FutureFundedEmbeddedCheckoutCompat = {
    version: "compat-shim-2026-05-21",
    runtime: "ff-campaign.js + ff-checkout-direct.js",
    ownsCheckoutSubmit: false,
    ownsModalState: false,
    ok: true,
    open() {
      return window.FutureFundedCampaign?.openCheckout?.() || false;
    },
    close() {
      return window.FutureFundedCampaign?.closeCheckout?.() || false;
    },
  };
})();
