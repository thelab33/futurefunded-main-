from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.web.app.blueprints.sponsors.services import build_sponsors_service
from apps.web.app.domain.campaign import Campaign, FAQItem, GalleryItem, SupportArea, TeamSpotlight
from apps.web.app.domain.organization import Organization
from apps.web.app.domain.sponsor import SponsorTier, SponsorWallItem
from apps.web.app.services.campaign_identity import (
    DEFAULT_CAMPAIGN_SLUG,
    DEFAULT_LOCATION,
    DEFAULT_SPONSOR_CONTACT_EMAIL,
    DEFAULT_TEAM_NAME,
)
from apps.web.app.viewmodels.campaign_vm import CampaignViewModel


# =============================================================================
# FutureFunded campaign service
# -----------------------------------------------------------------------------
# Purpose:
# - Convert config/env/demo values into stable domain objects.
# - Keep public campaign templates, platform previews, and visual boards fed by
#   one predictable campaign context.
#
# Public contract intentionally preserved:
# - CampaignService
# - CampaignService.get_organization()
# - CampaignService.get_campaign()
# - CampaignService.get_campaign_context()
# - build_campaign_service(config)
# =============================================================================


_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")
_SLUG_UNSAFE_RE = re.compile(r"[^a-z0-9]+")

DEFAULT_SUPPORT_EMAIL = "support@getfuturefunded.com"
DEFAULT_CAMPAIGN_NAME = "Spring Fundraiser"
DEFAULT_HEADLINE = "Fuel the season. Fund the future."
DEFAULT_SUBHEAD = "One shared season goal for"
DEFAULT_TAGLINE = (
    "Support 6th, 7th, and 8th grade athletes across local, travel, Gold, "
    "Platinum, and national circuit pathways with one secure gift."
)
DEFAULT_STORY_TITLE = "Why this campaign matters right now"
DEFAULT_STORY_INTRO = (
    "This campaign supports the real costs behind a serious youth program — "
    "travel, training, tournament fees, equipment, and the shared expenses that "
    "keep opportunities open for families."
)
DEFAULT_STORY_BODY = (
    "The goal is not just to raise money. The goal is to keep the season moving "
    "with the kind of structure, consistency, and support that helps athletes "
    "compete, grow, and represent the program well."
)
DEFAULT_STORY_BODY_2 = (
    "Every contribution helps reduce practical pressure on families and helps "
    "the organization focus on coaching, development, competition, and community."
)

DEFAULT_GALLERY_HERO = "/static/images/connect-atx-team.jpg"
DEFAULT_GALLERY_1 = "/static/images/7thGold.jpg"
DEFAULT_GALLERY_2 = "/static/images/8thGold.jpg"

DEFAULT_TEAM_RAISED = 175


def _clean(value: Any, default: str = "") -> str:
    """Return a stripped string, falling back when the input is empty."""
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int, default: str = "") -> str:
    """Clean and cap a string for safe template/domain use."""
    return _clean(value, default)[:limit].strip()


def _int(value: Any, default: int = 0) -> int:
    """Parse integers from env/config values that may arrive as strings."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _non_negative_int(value: Any, default: int = 0) -> int:
    parsed = _int(value, default)
    return parsed if parsed >= 0 else default


def _positive_int(value: Any, default: int) -> int:
    parsed = _int(value, default)
    return parsed if parsed > 0 else default


def _slugify(value: str) -> str:
    slug = _SLUG_UNSAFE_RE.sub("-", value.lower()).strip("-")
    return slug[:120].strip("-")


def _normalize_slug(value: Any, default: str = DEFAULT_CAMPAIGN_SLUG) -> str:
    """
    Normalize a slug while preserving the previous safety contract.

    Accepts already-valid slugs, and also tolerates human-readable values like
    "Connect ATX Elite" by slugifying them to "connect-atx-elite".
    """
    fallback = _truncate(default, 120, DEFAULT_CAMPAIGN_SLUG).lower()
    raw = _truncate(value, 120, fallback).lower()

    candidates = [raw, _slugify(raw), fallback, _slugify(fallback)]
    for candidate in candidates:
        if candidate and _SLUG_RE.fullmatch(candidate):
            return candidate

    return DEFAULT_CAMPAIGN_SLUG


def _normalize_currency(value: Any, default: str = "USD") -> str:
    cleaned = _clean(value, default).upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    return default


@dataclass(slots=True)
class CampaignService:
    config: Mapping[str, Any]

    # -------------------------------------------------------------------------
    # Config accessors
    # -------------------------------------------------------------------------

    def _cfg(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def _text(self, key: str, limit: int, default: str = "") -> str:
        return _truncate(self._cfg(key), limit, default)

    def _url(self, key: str) -> str:
        return _clean(self._cfg(key)).rstrip("/")

    def _public_base_url(self) -> str:
        return self._url("PUBLIC_BASE_URL")

    def _api_base_url(self) -> str:
        return self._url("API_BASE_URL")

    def _demo_mode(self) -> str:
        return _clean(self._cfg("DEMO_MODE"), "preview")

    def _currency(self) -> str:
        return _normalize_currency(self._cfg("DEMO_CURRENCY"), "USD")

    def _sponsors_service(self):
        return build_sponsors_service(self.config)

    # -------------------------------------------------------------------------
    # Shared campaign identity
    # -------------------------------------------------------------------------

    def _organization_slug(self) -> str:
        return _normalize_slug(self._cfg("DEMO_ORG_SLUG"), DEFAULT_CAMPAIGN_SLUG)

    def _campaign_slug(self, slug: str | None = None) -> str:
        default_slug = _normalize_slug(self._cfg("DEMO_CAMPAIGN_SLUG"), DEFAULT_CAMPAIGN_SLUG)
        return _normalize_slug(slug, default_slug)

    def _organization_name(self) -> str:
        return self._text("DEMO_ORGANIZATION_NAME", 120, DEFAULT_TEAM_NAME)

    def _location(self) -> str:
        return self._text("DEMO_LOCATION", 120, DEFAULT_LOCATION)

    def _support_email(self) -> str:
        return self._text("SUPPORT_EMAIL", 254, DEFAULT_SUPPORT_EMAIL)

    def _sponsor_contact_email(self) -> str:
        return self._text(
            "SPONSOR_CONTACT_EMAIL",
            254,
            _clean(self._cfg("SUPPORT_EMAIL"), DEFAULT_SPONSOR_CONTACT_EMAIL),
        )

    # -------------------------------------------------------------------------
    # Public domain assembly
    # -------------------------------------------------------------------------

    def get_organization(self) -> Organization:
        public_base_url = self._public_base_url()

        return Organization.from_dict(
            {
                "slug": self._organization_slug(),
                "name": self._organization_name(),
                "location": self._location(),
                "support_email": self._support_email(),
                "sponsor_contact_email": self._sponsor_contact_email(),
                "organizer_label": self._text(
                    "DEMO_ORGANIZER_LABEL",
                    120,
                    "Program Organizer",
                ),
                "description": self._text(
                    "DEMO_ORGANIZATION_DESCRIPTION",
                    600,
                    "A youth basketball program focused on development, competition, and community.",
                ),
                "logo_url": _clean(self._cfg("PLATFORM_LOGO")),
                "website_url": public_base_url,
                "theme": self._theme_payload(),
                "metadata": {
                    "public_base_url": public_base_url,
                    "api_base_url": self._api_base_url(),
                },
            }
        )

    def get_campaign(self, slug: str | None = None) -> Campaign:
        org_name = self._organization_name()
        goal = _positive_int(self._cfg("DEMO_GOAL"), 20000)

        return Campaign(
            slug=self._campaign_slug(slug),
            org_name=org_name,
            campaign_name=self._text("DEMO_CAMPAIGN_NAME", 120, DEFAULT_CAMPAIGN_NAME),
            headline=self._text("DEMO_HEADLINE", 160, DEFAULT_HEADLINE),
            subhead=self._text("DEMO_SUBHEAD", 120, DEFAULT_SUBHEAD),
            tagline=self._text("DEMO_TAGLINE", 320, DEFAULT_TAGLINE),
            location=self._location(),
            raised=_non_negative_int(self._cfg("DEMO_RAISED"), 11850),
            goal=goal,
            supporters=_non_negative_int(self._cfg("DEMO_SUPPORTERS"), 143),
            story_title=self._text("DEMO_STORY_TITLE", 120, DEFAULT_STORY_TITLE),
            story_intro=self._text("DEMO_STORY_INTRO", 500, DEFAULT_STORY_INTRO),
            story_body=self._text("DEMO_STORY_BODY", 700, DEFAULT_STORY_BODY),
            story_body_2=self._text("DEMO_STORY_BODY_2", 700, DEFAULT_STORY_BODY_2),
            gallery=self._gallery(org_name),
            support_areas=self._support_areas(),
            teams=self._teams(goal),
            faq=self._faq(),
            sponsor_tiers=self._sponsor_tiers(),
            sponsor_wall=self._sponsor_wall(),
            metadata={
                "mode": self._demo_mode(),
                "currency": self._currency(),
            },
        )

    def get_campaign_context(self, slug: str | None = None) -> dict[str, Any]:
        organization = self.get_organization()
        campaign = self.get_campaign(slug)
        public_base_url = self._public_base_url()

        vm = CampaignViewModel.from_domain(
            campaign=campaign,
            organization=organization,
            public_base_url=public_base_url,
        )

        context = vm.to_template_context()

        # Template compatibility layer.
        # Keep these keys stable because campaign, platform preview, checkout,
        # sponsor, and board templates may consume them directly.
        context.update(
            {
                "page_title": vm.page_title,
                "page_description": vm.page_description,
                "org_name": organization.display_name,
                "campaign_name": campaign.campaign_name,
                "campaign_slug": campaign.slug,
                "theme": organization.theme.theme,
                "density": organization.theme.density,
                "theme_color": organization.theme.theme_color,
                "theme_color_dark": organization.theme.theme_color_dark,
                "platform_logo": organization.theme.platform_logo,
                "support_email": organization.support_email,
                "organizer_email": organization.support_email,
                "sponsor_contact_email": organization.primary_contact_email,
                "ff_data_mode": self._demo_mode(),
                "terms_url": _clean(self._cfg("TERMS_URL"), "/terms"),
                "privacy_url": _clean(self._cfg("PRIVACY_URL"), "/privacy"),
                "stripe_pk": _clean(self._cfg("STRIPE_PUBLISHABLE_KEY")),
                "paypal_client_id": _clean(self._cfg("PAYPAL_CLIENT_ID")),
                "currency": self._currency(),
                "public_base_url": public_base_url,
                "api_base_url": self._api_base_url(),
            }
        )

        return context

    # -------------------------------------------------------------------------
    # Payload builders
    # -------------------------------------------------------------------------

    def _theme_payload(self) -> dict[str, str]:
        return {
            "theme": _clean(self._cfg("DEFAULT_THEME"), "dark"),
            "density": _clean(self._cfg("DEFAULT_DENSITY"), "compact"),
            "theme_color": _clean(self._cfg("THEME_COLOR"), "#f97316"),
            "theme_color_dark": _clean(self._cfg("THEME_COLOR_DARK"), "#0b0f17"),
            "platform_logo": _clean(self._cfg("PLATFORM_LOGO")),
        }

    def _gallery_item(
        self,
        *,
        src_key: str,
        default_src: str,
        alt: str,
        caption: str,
        body: str,
    ) -> GalleryItem:
        return GalleryItem(
            src=_clean(self._cfg(src_key), default_src),
            alt=alt,
            caption=caption,
            body=body,
        )

    def _gallery(self, org_name: str) -> list[GalleryItem]:
        return [
            self._gallery_item(
                src_key="DEMO_GALLERY_HERO",
                default_src=DEFAULT_GALLERY_HERO,
                alt=org_name,
                caption=org_name,
                body=(
                    "A better fundraising surface should help people see the program clearly, "
                    "trust the need, and understand where support goes."
                ),
            ),
            self._gallery_item(
                src_key="DEMO_GALLERY_1",
                default_src=DEFAULT_GALLERY_1,
                alt="Team photo",
                caption="Development and competition",
                body=(
                    "Support helps fund the real work behind training, preparation, "
                    "and game-day performance."
                ),
            ),
            self._gallery_item(
                src_key="DEMO_GALLERY_2",
                default_src=DEFAULT_GALLERY_2,
                alt="Program image",
                caption="Training and tournament travel",
                body=(
                    "The season depends on more than one weekend — support keeps "
                    "the full schedule moving."
                ),
            ),
        ]

    def _support_areas(self) -> list[SupportArea]:
        return [
            SupportArea(
                amount=2500,
                title="Travel and tournament access",
                body=(
                    "Support helps cover entry fees, weekend travel, lodging pressure, "
                    "and the logistics that come with serious competition."
                ),
                featured=True,
            ),
            SupportArea(
                amount=1800,
                title="Training and gym time",
                body=(
                    "Funding supports practice access, development sessions, and the "
                    "repetition needed to keep athletes improving across the season."
                ),
            ),
            SupportArea(
                amount=1200,
                title="Shared team needs",
                body=(
                    "Equipment, uniforms, media, recovery essentials, and other "
                    "program-wide costs add up quickly and need clean, predictable support."
                ),
            ),
        ]

    def _team_photo(self, key: str, default: str) -> str:
        return _clean(self._cfg(key), default)

    def _teams(self, goal: int) -> list[TeamSpotlight]:
        team_goal = goal or 10000
        team_raised = max(
            DEFAULT_TEAM_RAISED,
            _non_negative_int(self._cfg("DEMO_TEAM_RAISED"), DEFAULT_TEAM_RAISED),
        )

        return [
            TeamSpotlight(
                id="6g",
                name="6th Grade Gold",
                tier="Gold",
                meta="First AAU reps — fundamentals, spacing, and confidence.",
                goal=team_goal,
                raised=team_raised,
                featured=True,
                photo=self._team_photo("DEMO_TEAM_6G_PHOTO", DEFAULT_GALLERY_HERO),
                ask=(
                    "Support helps cover tournament fees, gym time, and shared "
                    "development costs for the full program while keeping this group moving forward."
                ),
                label="Featured team",
            ),
            TeamSpotlight(
                id="7g",
                name="7th Grade Gold",
                tier="Gold",
                meta="Speed, pressure reps, and weekend competition growth.",
                goal=team_goal,
                raised=team_raised,
                featured=True,
                photo=self._team_photo("DEMO_TEAM_7G_PHOTO", DEFAULT_GALLERY_1),
                ask=(
                    "Support helps relieve travel and entry-fee pressure while giving "
                    "the program more room to focus on training and competition."
                ),
                label="Featured team",
            ),
            TeamSpotlight(
                id="7b",
                name="7th Grade Black",
                tier="Black",
                meta="Defense, physicality, and team habits that translate to game day.",
                goal=team_goal,
                raised=team_raised,
                needs=True,
                photo=self._team_photo("DEMO_TEAM_7B_PHOTO", "/static/images/7thBlack.png"),
                ask=(
                    "Support helps cover uniforms, training, weekend logistics, and "
                    "the program-wide essentials that keep this team prepared."
                ),
                label="Program support",
            ),
            TeamSpotlight(
                id="8g",
                name="8th Grade Gold",
                tier="Gold",
                meta="Leadership, late-season discipline, and stronger finish-through-contact play.",
                goal=team_goal,
                raised=team_raised,
                photo=self._team_photo("DEMO_TEAM_8G_PHOTO", DEFAULT_GALLERY_2),
                ask=(
                    "Support helps fund gym rentals, competition costs, and the shared "
                    "resources needed to finish the season well."
                ),
                label="Program support",
            ),
        ]

    def _faq(self) -> list[FAQItem]:
        return [
            FAQItem(
                question="What does support for this campaign help cover?",
                answer=(
                    "Support helps cover the real costs behind the season and the program, "
                    "including travel, training, tournament fees, equipment, and shared team "
                    "needs that keep opportunities open for families."
                ),
            ),
            FAQItem(
                question="Can I contribute without creating an account?",
                answer=(
                    "Yes. The giving experience is designed to be straightforward and "
                    "low-friction, with a secure checkout path that does not require "
                    "supporters to create a separate account first."
                ),
            ),
            FAQItem(
                question="Is this page only for donations, or can businesses sponsor too?",
                answer=(
                    "Both are supported. Individual supporters can give directly, and "
                    "businesses can use the sponsor lane to review package options and "
                    "submit interest through a cleaner, more structured process."
                ),
            ),
            FAQItem(
                question="Does support go to one specific team or the broader program?",
                answer=(
                    "The campaign is structured to support the broader organization and "
                    "shared season costs. Team spotlights are shown to give context and "
                    "visibility, but the fundraising surface is designed to support the "
                    "program as a whole."
                ),
            ),
            FAQItem(
                question="How do I ask a question about support, receipts, or sponsorship?",
                answer=(
                    "Use the contact path provided on this page or reach out to the "
                    "organizer/support email listed below. The goal is to make follow-up "
                    "clear for donors, families, and sponsor contacts."
                ),
            ),
        ]

    def _sponsor_tiers(self) -> list[SponsorTier]:
        return self._sponsors_service().get_sponsor_tiers()

    def _sponsor_wall(self) -> list[SponsorWallItem]:
        return self._sponsors_service().get_sponsor_wall()


def build_campaign_service(config: Mapping[str, Any]) -> CampaignService:
    return CampaignService(config=config)
