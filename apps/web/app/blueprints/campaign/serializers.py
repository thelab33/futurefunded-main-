from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def serialize_campaign_config(context: Mapping[str, Any]) -> dict[str, Any]:
    campaign = context.get("campaign") or {}

    return {
        "app": "futurefunded",
        "page": "campaign",
        "mode": context.get("ff_data_mode", "preview"),
        "campaignSlug": campaign.get("slug", context.get("campaign_slug", "")),
        "campaignName": campaign.get("campaign_name", context.get("campaign_name", "")),
        "orgName": campaign.get("org_name", context.get("org_name", "")),
        "shareUrl": context.get("share_url", ""),
        "canonicalUrl": context.get("canonical_url", ""),
        "raised": campaign.get("raised", context.get("raised", 0)),
        "goal": campaign.get("goal", context.get("goal", 0)),
        "currency": context.get("currency", "USD"),
        "stripePublishableKey": context.get("stripe_pk", ""),
        "paypalClientId": context.get("paypal_client_id", ""),
        "termsUrl": context.get("terms_url", "/terms"),
        "privacyUrl": context.get("privacy_url", "/privacy"),
    }


def serialize_campaign_selectors() -> dict[str, Any]:
    return {
        "hooks": {
            "openCheckout": "[data-ff-open-checkout]",
            "closeCheckout": "[data-ff-close-checkout]",
            "checkoutSheet": "[data-ff-checkout-sheet]",
            "checkoutViewport": "[data-ff-checkout-viewport]",
            "checkoutContent": "[data-ff-checkout-content]",
            "checkoutScroll": "[data-ff-checkout-scroll]",
            "checkoutShell": "[data-ff-checkout-shell]",
            "checkoutStatus": "[data-ff-checkout-status]",
            "checkoutSuccess": "[data-ff-checkout-success]",
            "checkoutError": "[data-ff-checkout-error]",
            "donationForm": "#donationForm",
            "amountInput": "[data-ff-amount-input]",
            "amountChip": "[data-ff-amount]",
            "summaryAmount": "[data-ff-summary-amount]",
            "teamId": "[data-ff-team-id]",
            "paymentMount": "[data-ff-payment-element]",
            "stripeMount": "[data-ff-stripe-mount]",
            "paypalMount": "[data-ff-paypal-mount]",
            "toasts": "[data-ff-toasts]",
            "live": "[data-ff-live]",
            "share": "[data-ff-share]",
            "themeToggle": "[data-ff-theme-toggle]",
            "openDrawer": "[data-ff-open-drawer]",
            "closeDrawer": "[data-ff-close-drawer]",
            "drawer": "[data-ff-drawer]",
            "openSponsor": "[data-ff-open-sponsor]",
            "closeSponsor": "[data-ff-close-sponsor]",
            "sponsorModal": "[data-ff-sponsor-modal]",
            "sponsorForm": "#sponsorForm",
            "sponsorTier": "[data-ff-sponsor-tier]",
            "sponsorTierGrid": "[data-ff-sponsor-tier-grid]",
            "sponsorTierSelected": "[data-ff-sponsor-tier-selected]",
            "sponsorSubmit": "[data-ff-sponsor-submit]",
            "sponsorStatus": "[data-ff-sponsor-status]",
            "sponsorError": "[data-ff-sponsor-error]",
            "sponsorSuccess": "[data-ff-sponsor-success]",
            "openVideo": "[data-ff-open-video]",
            "closeVideo": "[data-ff-close-video]",
            "videoModal": "[data-ff-video-modal]",
            "videoFrame": "[data-ff-video-frame]",
            "openTerms": "[data-ff-open-terms]",
            "closeTerms": "[data-ff-close-terms]",
            "termsModal": "[data-ff-terms-modal]",
            "openPrivacy": "[data-ff-open-privacy]",
            "closePrivacy": "[data-ff-close-privacy]",
            "privacyModal": "[data-ff-privacy-modal]",
            "openOnboard": "[data-ff-open-onboard]",
            "closeOnboard": "[data-ff-close-onboard]",
            "onboardModal": "[data-ff-onboard-modal]",
            "onboardForm": "[data-ff-onboard-form]",
            "onboardNext": "[data-ff-onboard-next]",
            "onboardPrev": "[data-ff-onboard-prev]",
            "onboardFinish": "[data-ff-onboard-finish]",
            "onboardSummary": "[data-ff-onboard-summary]",
            "onboardStatus": "[data-ff-onboard-status]",
            "onboardResult": "[data-ff-onboard-result]",
            "onboardEmail": "[data-ff-onboard-email]",
            "onboardCopy": "[data-ff-onboard-copy]",
            "stepPill": "[data-ff-step-pill]",
            "stepPanel": "[data-ff-step]",
            "floatingDonate": "[data-ff-floating-donate]",
            "backToTop": "[data-ff-backtotop]",
            "tabs": "[data-ff-tabs]",
            "story": "[data-ff-story]",
        }
    }


def serialize_campaign_context(context: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(context)
    payload["ff_config"] = serialize_campaign_config(context)
    payload["ff_selectors"] = serialize_campaign_selectors()
    return payload
