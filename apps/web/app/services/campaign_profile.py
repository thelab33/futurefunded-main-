"""FutureFunded campaign profile resolver.

This is the platform bridge between demo campaign config, onboarding records,
dashboard views, checkout metadata, emails, and future white-label tenants.

For now, the configured flagship campaign remains the safe fallback.
Later, this resolver can merge:
- database campaign records
- onboarding setup records
- tenant/org branding
- payment/email readiness
"""

from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import os
from copy import deepcopy
from typing import Any, Mapping


DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_SLUG
DEFAULT_TEAM_NAME = DEFAULT_TEAM_NAME
DEFAULT_LOCATION = DEFAULT_LOCATION
DEFAULT_BRAND_NAME = "FutureFunded"
DEFAULT_SUPPORT_EMAIL = "hello@futurefunded.com"

DEFAULT_SPONSOR_PACKAGES: list[dict[str, Any]] = [
    {
        "key": "community",
        "name": "Community Partner",
        "label": "Community Partner",
        "amount": 300,
        "price": "$300",
        "best_for": "Families, alumni, and local supporters",
        "copy": "Show up publicly for the athletes and help cover the practical costs behind the season.",
        "recognition": [
            "Campaign sponsor listing",
            "Thank-you mention",
            "Optional website link",
        ],
    },
    {
        "key": "featured",
        "name": "Featured Sponsor",
        "label": "Featured Sponsor",
        "amount": 750,
        "price": "$750",
        "best_for": "Local businesses and community brands",
        "copy": "Earn stronger visibility while helping the program fund travel, meals, gear, and tournament costs.",
        "recognition": [
            "Featured placement",
            "Logo or business name",
            "Website link",
            "Sponsor thank-you feature",
        ],
    },
    {
        "key": "legacy",
        "name": "Legacy Sponsor",
        "label": "Legacy Sponsor",
        "amount": 1500,
        "price": "$1,500",
        "best_for": "Anchor partners and season backers",
        "copy": "Become a headline supporter for the campaign and help make the season more affordable for families.",
        "recognition": [
            "Premium sponsor placement",
            "Logo, website, and sponsor message",
            "Priority thank-you feature",
            "Season-long recognition",
        ],
    },
]


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _slug(value: Any, fallback: str = DEFAULT_CAMPAIGN_SLUG) -> str:
    text = _clean(value, fallback).lower().replace("_", "-")
    text = "-".join(part for part in text.replace("/", "-").split("-") if part)
    return text or fallback


def _first(data: Mapping[str, Any], *keys: str, fallback: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return fallback


def _number(value: Any, fallback: int = 0) -> int:
    try:
        if value is None or value == "":
            return fallback
        return int(float(str(value).replace(",", "").replace("$", "").strip()))
    except Exception:
        return fallback


def _list(value: Any, fallback: list[Any] | None = None) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return list(value)
    return deepcopy(fallback or [])


def _dict(value: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    return deepcopy(fallback or {})


def _load_config_campaign(slug: str) -> dict[str, Any]:
    try:
        from apps.web.app.config.team_campaigns import get_team_campaign_context

        return dict(get_team_campaign_context(slug) or {})
    except Exception:
        return {}


def resolve_campaign_profile(
    slug: str | None = None,
    *,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a normalized campaign profile.

    The returned shape intentionally includes aliases used across the current
    Flask/Jinja codebase so we can migrate safely without breaking the current
    Connect ATX fundraiser.
    """

    requested_slug = _slug(
        slug
        or os.getenv("FF_DEMO_CAMPAIGN_SLUG")
        or os.getenv("DEMO_CAMPAIGN_SLUG")
        or DEFAULT_CAMPAIGN_SLUG
    )

    config = _load_config_campaign(requested_slug)
    merged: dict[str, Any] = {**config, **dict(overrides or {})}

    team_name = _clean(
        os.getenv("FF_DEMO_TEAM_NAME")
        or os.getenv("DEMO_CAMPAIGN_NAME")
        or _first(merged, "team_name", "organization_name", "org_name", "name", "title"),
        DEFAULT_TEAM_NAME,
    )

    campaign_slug = _slug(
        os.getenv("FF_DEMO_CAMPAIGN_SLUG")
        or os.getenv("DEMO_CAMPAIGN_SLUG")
        or _first(merged, "campaign_slug", "slug"),
        requested_slug,
    )

    campaign_url = _clean(
        os.getenv("FF_DEMO_CAMPAIGN_URL")
        or os.getenv("DEMO_CAMPAIGN_URL")
        or _first(merged, "campaign_url", "public_url"),
        f"/c/{campaign_slug}",
    )

    location = _clean(
        os.getenv("FF_DEMO_LOCATION")
        or os.getenv("DEMO_LOCATION")
        or _first(merged, "location", "city_state"),
        DEFAULT_LOCATION,
    )

    campaign_name = _clean(
        _first(merged, "campaign_name", "fund_name", "page_title"),
        f"{team_name} Season Fund",
    )

    organizer_name = _clean(
        _first(merged, "organizer_name", "owner_name", "contact_name"),
        f"{team_name} Organizer",
    )

    public_base_url = _clean(
        os.getenv("PUBLIC_BASE_URL")
        or os.getenv("FF_PUBLIC_BASE_URL")
        or os.getenv("APP_PUBLIC_URL"),
        "",
    ).rstrip("/")

    goal_amount = _number(
        _first(merged, "goal_amount", "goal", "campaign_goal", "fundraising_goal"),
        20000,
    )

    raised_amount = _number(
        _first(merged, "raised_amount", "raised", "current_amount", "amount_raised"),
        0,
    )

    supporter_count = _number(
        _first(merged, "supporter_count", "supporters", "donor_count"),
        0,
    )

    sponsor_count = _number(
        _first(merged, "sponsor_count", "sponsors_count"),
        0,
    )

    donation_amounts = _list(
        _first(merged, "donation_amounts", "quick_amounts", "amounts"),
        [25, 50, 100, 250],
    )

    sponsor_packages = _list(
        _first(merged, "sponsor_packages", "sponsor_tiers", "tiers"),
        DEFAULT_SPONSOR_PACKAGES,
    )

    theme = _dict(
        _first(merged, "theme", "brand_theme"),
        {},
    )

    team_logo_url = _clean(
        _first(merged, "team_logo_url", "logo_url", "organization_logo"),
        "",
    )

    hero_image_url = _clean(
        _first(merged, "hero_image_url", "team_photo_url", "cover_image_url"),
        "",
    )

    qr_image_url = _clean(
        _first(merged, "qr_image_url", "qr_code_url"),
        "",
    )

    support_email = _clean(
        os.getenv("FF_SUPPORT_EMAIL")
        or _first(merged, "support_email", "contact_email", "reply_to_email"),
        DEFAULT_SUPPORT_EMAIL,
    )

    brand_name = _clean(os.getenv("FF_BRAND_NAME"), DEFAULT_BRAND_NAME)

    profile = {
        # Platform identity
        "brand_name": brand_name,
        "support_email": support_email,

        # Campaign identity
        "team_name": team_name,
        "organization_name": team_name,
        "org_name": team_name,
        "name": team_name,
        "title": campaign_name,
        "campaign_name": campaign_name,
        "fund_name": campaign_name,
        "campaign_slug": campaign_slug,
        "slug": campaign_slug,
        "campaign_url": campaign_url,
        "campaign_public_url": f"{public_base_url}{campaign_url}" if public_base_url else campaign_url,
        "location": location,
        "organizer_name": organizer_name,

        # Fundraising state
        "goal_amount": goal_amount,
        "goal": goal_amount,
        "raised_amount": raised_amount,
        "raised": raised_amount,
        "supporter_count": supporter_count,
        "supporters": supporter_count,
        "sponsor_count": sponsor_count,

        # Conversion config
        "donation_amounts": donation_amounts,
        "sponsor_packages": sponsor_packages,

        # Brand/media
        "theme": theme,
        "team_logo_url": team_logo_url,
        "hero_image_url": hero_image_url,
        "qr_image_url": qr_image_url,

        # Raw config for gradual migration
        "raw": deepcopy(merged),
    }

    return profile
