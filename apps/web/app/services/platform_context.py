"""Shared FutureFunded platform identity context."""

from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

from typing import Any


def build_platform_context() -> dict[str, Any]:
    """Return Jinja context for platform/demo campaign identity."""
    from apps.web.app.services.campaign_profile import resolve_campaign_profile

    profile = resolve_campaign_profile(DEFAULT_CAMPAIGN_SLUG)

    try:
        from apps.web.app.services.sponsor_lead_repository import (
            public_sponsor_recognitions,
            recent_sponsor_leads,
        )

        sponsor_leads = recent_sponsor_leads(profile["campaign_slug"], limit=6)
        public_sponsor_recognitions_list = public_sponsor_recognitions(
            profile["campaign_slug"],
            limit=12,
        )
    except Exception:
        sponsor_leads = []
        public_sponsor_recognitions_list = []

    return {
        "ff_platform": {
            "brand_name": profile["brand_name"],
            "support_email": profile["support_email"],
            "team_name": profile["team_name"],
            "campaign_name": profile["campaign_name"],
            "campaign_slug": profile["campaign_slug"],
            "campaign_url": profile["campaign_url"],
            "campaign_public_url": profile["campaign_public_url"],
            "location": profile["location"],
            "organizer_name": profile["organizer_name"],
        },
        "ff_campaign_profile": profile,
        "ff_sponsor_leads": sponsor_leads,
        "ff_public_sponsor_recognitions": public_sponsor_recognitions_list,
    }


def register_platform_identity_context(app: Any) -> None:
    """Register shared platform identity context on the Flask app."""

    @app.context_processor
    def _ff_platform_identity_context() -> dict[str, Any]:
        try:
            return build_platform_context()
        except Exception:
            return {
                "ff_platform": {
                    "brand_name": "FutureFunded",
                    "support_email": "hello@futurefunded.com",
                    "team_name": DEFAULT_TEAM_NAME,
                    "campaign_name": DEFAULT_CAMPAIGN_NAME,
                    "campaign_slug": DEFAULT_CAMPAIGN_SLUG,
                    "campaign_url": f"/c/{DEFAULT_CAMPAIGN_SLUG}",
                    "campaign_public_url": f"/c/{DEFAULT_CAMPAIGN_SLUG}",
                    "location": DEFAULT_LOCATION,
                    "organizer_name": f"{DEFAULT_TEAM_NAME} Organizer",
                },
                "ff_campaign_profile": {},
            }
