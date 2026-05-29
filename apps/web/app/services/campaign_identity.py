"""FutureFunded campaign identity defaults.

This module is the single fallback source for the flagship/demo campaign identity.
Production/white-label campaigns should override these values from DB/config/profile
data, but active templates and services should not scatter hard-coded demo strings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignIdentityDefaults:
    brand_name: str
    team_name: str
    campaign_slug: str
    location: str
    campaign_name: str
    campaign_title: str
    campaign_accent: str
    public_base_url: str
    sponsor_contact_email: str
    team_logo_url: str


def _env(name: str, fallback: str = "") -> str:
    return (os.environ.get(name) or fallback).strip()


def get_campaign_identity_defaults() -> CampaignIdentityDefaults:
    team_name = _env("FF_DEFAULT_TEAM_NAME", "Connect ATX Elite")
    campaign_slug = _env("FF_DEFAULT_CAMPAIGN_SLUG", "connect-atx-elite")

    return CampaignIdentityDefaults(
        brand_name=_env("FF_DEFAULT_BRAND_NAME", "FutureFunded"),
        team_name=team_name,
        campaign_slug=campaign_slug,
        location=_env("FF_DEFAULT_LOCATION", "Austin, TX"),
        campaign_name=_env("FF_DEFAULT_CAMPAIGN_NAME", f"{team_name} Season Fund"),
        campaign_title=_env("FF_DEFAULT_CAMPAIGN_TITLE", "Fuel the season. Fund the future."),
        campaign_accent=_env("FF_DEFAULT_CAMPAIGN_ACCENT", "Back the athletes."),
        public_base_url=_env("PUBLIC_BASE_URL", _env("FF_PUBLIC_BASE_URL", "http://127.0.0.1:5000")),
        sponsor_contact_email=_env("FF_SPONSOR_CONTACT_EMAIL", "sponsor@futurefunded.com"),
        team_logo_url=_env("FF_DEFAULT_TEAM_LOGO_URL", "/static/images/teams/connect-atx-elite/logo.jpg"),
    )


DEFAULT_CAMPAIGN_IDENTITY = get_campaign_identity_defaults()
DEFAULT_BRAND_NAME = DEFAULT_CAMPAIGN_IDENTITY.brand_name
DEFAULT_TEAM_NAME = DEFAULT_CAMPAIGN_IDENTITY.team_name
DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_IDENTITY.campaign_slug
DEFAULT_LOCATION = DEFAULT_CAMPAIGN_IDENTITY.location
DEFAULT_CAMPAIGN_NAME = DEFAULT_CAMPAIGN_IDENTITY.campaign_name
DEFAULT_CAMPAIGN_TITLE = DEFAULT_CAMPAIGN_IDENTITY.campaign_title
DEFAULT_CAMPAIGN_ACCENT = DEFAULT_CAMPAIGN_IDENTITY.campaign_accent
DEFAULT_PUBLIC_BASE_URL = DEFAULT_CAMPAIGN_IDENTITY.public_base_url
DEFAULT_SPONSOR_CONTACT_EMAIL = DEFAULT_CAMPAIGN_IDENTITY.sponsor_contact_email
DEFAULT_TEAM_LOGO_URL = DEFAULT_CAMPAIGN_IDENTITY.team_logo_url
