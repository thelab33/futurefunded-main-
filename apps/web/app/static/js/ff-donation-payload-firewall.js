/*
  FutureFunded Donation Payload Firewall
  File: apps/web/app/static/js/ff-donation-payload-firewall.js
  Version: donation-payload-firewall-v2

  Purpose:
  - Defensive safety guard for donor checkout requests.
  - Removes sponsor metadata from donation checkout payloads.
  - Supports both fetch() and XMLHttpRequest legacy callers.
  - Current payment authority is ff-checkout-direct.js.
*/

/* FF_DONATION_PAYLOAD_FIREWALL_V2_START */
(() => {
  "use strict";

  const VERSION = "donation-payload-firewall-v2";

  if (window.FutureFundedDonationPayloadFirewall?.version === VERSION) return;

  const SPONSOR_KEYS = [
    "sponsor_intake",
    "business_name",
    "contact_email",
    "recognition_name",
    "website",
    "recognition_note",
    "package",
    "package_label",
    "package_amount",
    "package_amount_cents",
    "package_key",
    "package_name",
    "sponsor_package",
    "sponsor_tier",
    "tier",
    "tier_label",
    "tier_amount",
    "tier_amount_cents",
  ];

  function requestUrl(input) {
    if (typeof input === "string") return input;
    if (input?.url) return String(input.url);
    return "";
  }

  function isCheckoutSessionUrl(input) {
    return requestUrl(input).includes("/checkout/session");
  }

  function parseBody(body) {
    if (!body || typeof body !== "string") return null;

    try {
      return JSON.parse(body);
    } catch {
      return null;
    }
  }

  function isDonation(payload) {
    if (!payload || typeof payload !== "object") return false;

    const source = String(payload.source || "");

    return (
      payload.flow === "donation" ||
      payload.kind === "donation" ||
      payload.type === "donation" ||
      payload.payment_flow === "donation" ||
      payload.checkout_mode === "donation" ||
      source.startsWith("checkout-direct") ||
      source.includes("campaign-v1-authority-smoke") ||
      source === VERSION
    );
  }

  function cleanDonationPayload(payload) {
    const cleaned = { ...(payload || {}) };

    for (const key of SPONSOR_KEYS) {
      delete cleaned[key];
    }

    cleaned.flow = "donation";
    cleaned.kind = "donation";
    cleaned.type = "donation";
    cleaned.payment_flow = "donation";
    cleaned.checkout_mode = "donation";
    cleaned.payload_firewall = VERSION;

    return cleaned;
  }

  const nativeFetch = window.fetch ? window.fetch.bind(window) : null;

  if (nativeFetch) {
    window.fetch = function ffDonationPayloadFirewallFetch(input, init = {}) {
      try {
        if (isCheckoutSessionUrl(input) && init?.body) {
          const payload = parseBody(init.body);

          if (isDonation(payload)) {
            init = {
              ...init,
              body: JSON.stringify(cleanDonationPayload(payload)),
            };
          }
        }
      } catch (error) {
        console.warn("[FutureFunded donation payload firewall] fetch warning", error);
      }

      return nativeFetch(input, init);
    };
  }

  const nativeOpen = XMLHttpRequest.prototype.open;
  const nativeSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function ffFirewallXhrOpen(method, url, ...rest) {
    this.__ffDonationFirewallUrl = String(url || "");
    return nativeOpen.call(this, method, url, ...rest);
  };

  XMLHttpRequest.prototype.send = function ffFirewallXhrSend(body) {
    try {
      if (isCheckoutSessionUrl(this.__ffDonationFirewallUrl) && typeof body === "string") {
        const payload = parseBody(body);

        if (isDonation(payload)) {
          return nativeSend.call(this, JSON.stringify(cleanDonationPayload(payload)));
        }
      }
    } catch (error) {
      console.warn("[FutureFunded donation payload firewall] XHR warning", error);
    }

    return nativeSend.call(this, body);
  };

  window.FutureFundedDonationPayloadFirewall = {
    installed: true,
    version: VERSION,
    sponsorKeys: SPONSOR_KEYS.slice(),
    cleanDonationPayload,
  };

  console.info("[FutureFunded donation payload firewall] installed", VERSION);
})();
/* FF_DONATION_PAYLOAD_FIREWALL_V2_END */
