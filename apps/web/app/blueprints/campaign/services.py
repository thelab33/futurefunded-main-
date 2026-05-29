from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.web.app.blueprints.sponsors.services import build_sponsors_service
from apps.web.app.domain.campaign import Campaign, FAQItem, GalleryItem, SupportArea, TeamSpotlight
from apps.web.app.domain.organization import Organization
from apps.web.app.domain.sponsor import SponsorTier, SponsorWallItem
from apps.web.app.viewmodels.campaign_vm import CampaignViewModel

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int, default: str = "") -> str:
    return _clean(value, default)[:limit].strip()


def _int(value: Any, default: int = 0) -> int:
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


def _normalize_slug(value: Any, default: str = DEFAULT_CAMPAIGN_SLUG) -> str:
    cleaned = _truncate(value, 120, default).lower()
    if cleaned and _SLUG_RE.fullmatch(cleaned):
        return cleaned
    return default


def _normalize_currency(value: Any, default: str = "USD") -> str:
    cleaned = _clean(value, default).upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    return default


@dataclass(slots=True)
class CampaignService:
    config: Mapping[str, Any]

    def _public_base_url(self) -> str:
        return _clean(self.config.get("PUBLIC_BASE_URL")).rstrip("/")

    def _api_base_url(self) -> str:
        return _clean(self.config.get("API_BASE_URL")).rstrip("/")

    def _demo_mode(self) -> str:
        return _clean(self.config.get("DEMO_MODE"), "preview")

    def _sponsors_service(self):
        return build_sponsors_service(self.config)

    def get_organization(self) -> Organization:
        public_base_url = self._public_base_url()

        return Organization.from_dict(
            {
                "slug": _normalize_slug(
                    self.config.get("DEMO_ORG_SLUG"),
                    DEFAULT_CAMPAIGN_SLUG,
                ),
                "name": _truncate(
                    self.config.get("DEMO_ORGANIZATION_NAME"),
                    120,
                    DEFAULT_TEAM_NAME,
                ),
                "location": _truncate(
                    self.config.get("DEMO_LOCATION"),
                    120,
                    DEFAULT_LOCATION,
                ),
                "support_email": _truncate(
                    self.config.get("SUPPORT_EMAIL"),
                    254,
                    "support@getfuturefunded.com",
                ),
                "sponsor_contact_email": _truncate(
                    self.config.get("SPONSOR_CONTACT_EMAIL"),
                    254,
                    _clean(self.config.get("SUPPORT_EMAIL"), "support@getfuturefunded.com"),
                ),
                "organizer_label": _truncate(
                    self.config.get("DEMO_ORGANIZER_LABEL"),
                    120,
                    "Program Organizer",
                ),
                "description": _truncate(
                    self.config.get("DEMO_ORGANIZATION_DESCRIPTION"),
                    600,
                    "A youth basketball program focused on development, competition, and community.",
                ),
                "logo_url": _clean(self.config.get("PLATFORM_LOGO")),
                "website_url": public_base_url,
                "theme": {
                    "theme": _clean(self.config.get("DEFAULT_THEME"), "dark"),
                    "density": _clean(self.config.get("DEFAULT_DENSITY"), "compact"),
                    "theme_color": _clean(self.config.get("THEME_COLOR"), "#f97316"),
                    "theme_color_dark": _clean(self.config.get("THEME_COLOR_DARK"), "#0b0f17"),
                    "platform_logo": _clean(self.config.get("PLATFORM_LOGO")),
                },
                "metadata": {
                    "public_base_url": public_base_url,
                    "api_base_url": self._api_base_url(),
                },
            }
        )

    def get_campaign(self, slug: str | None = None) -> Campaign:
        default_slug = _normalize_slug(
            self.config.get("DEMO_CAMPAIGN_SLUG"),
            DEFAULT_CAMPAIGN_SLUG,
        )
        safe_slug = _normalize_slug(slug, default_slug)

        org_name = _truncate(
            self.config.get("DEMO_ORGANIZATION_NAME"),
            120,
            DEFAULT_TEAM_NAME,
        )
        campaign_name = _truncate(
            self.config.get("DEMO_CAMPAIGN_NAME"),
            120,
            "Spring Fundraiser",
        )
        location = _truncate(
            self.config.get("DEMO_LOCATION"),
            120,
            DEFAULT_LOCATION,
        )
        goal = _positive_int(self.config.get("DEMO_GOAL"), 20000)
        raised = _non_negative_int(self.config.get("DEMO_RAISED"), 11850)
        supporters = _non_negative_int(self.config.get("DEMO_SUPPORTERS"), 143)

        return Campaign(
            slug=safe_slug,
            org_name=org_name,
            campaign_name=campaign_name,
            headline=_truncate(
                self.config.get("DEMO_HEADLINE"),
                160,
                "Fuel the season. Fund the future.",
            ),
            subhead=_truncate(
                self.config.get("DEMO_SUBHEAD"),
                120,
                "One shared season goal for",
            ),
            tagline=_truncate(
                self.config.get("DEMO_TAGLINE"),
                320,
                "Support 6th, 7th, and 8th grade athletes across local, travel, Gold, Platinum, and national circuit pathways with one secure gift.",
            ),
            location=location,
            raised=raised,
            goal=goal,
            supporters=supporters,
            story_title=_truncate(
                self.config.get("DEMO_STORY_TITLE"),
                120,
                "Why this campaign matters right now",
            ),
            story_intro=_truncate(
                self.config.get("DEMO_STORY_INTRO"),
                500,
                "This campaign supports the real costs behind a serious youth program — travel, training, tournament fees, equipment, and the shared expenses that keep opportunities open for families.",
            ),
            story_body=_truncate(
                self.config.get("DEMO_STORY_BODY"),
                700,
                "The goal is not just to raise money. The goal is to keep the season moving with the kind of structure, consistency, and support that helps athletes compete, grow, and represent the program well.",
            ),
            story_body_2=_truncate(
                self.config.get("DEMO_STORY_BODY_2"),
                700,
                "Every contribution helps reduce practical pressure on families and helps the organization focus on coaching, development, competition, and community.",
            ),
            gallery=self._gallery(org_name),
            support_areas=self._support_areas(),
            teams=self._teams(goal),
            faq=self._faq(),
            sponsor_tiers=self._sponsor_tiers(),
            sponsor_wall=self._sponsor_wall(),
            metadata={
                "mode": self._demo_mode(),
                "currency": _normalize_currency(self.config.get("DEMO_CURRENCY"), "USD"),
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
                "terms_url": _clean(self.config.get("TERMS_URL"), "/terms"),
                "privacy_url": _clean(self.config.get("PRIVACY_URL"), "/privacy"),
                "stripe_pk": _clean(self.config.get("STRIPE_PUBLISHABLE_KEY")),
                "paypal_client_id": _clean(self.config.get("PAYPAL_CLIENT_ID")),
                "currency": _normalize_currency(self.config.get("DEMO_CURRENCY"), "USD"),
                "public_base_url": public_base_url,
                "api_base_url": self._api_base_url(),
            }
        )
        return context

    def _gallery(self, org_name: str) -> list[GalleryItem]:
        return [
            GalleryItem(
                src=_clean(
                    self.config.get("DEMO_GALLERY_HERO"),
                    "/static/images/connect-atx-team.jpg",
                ),
                alt=org_name,
                caption=org_name,
                body="A better fundraising surface should help people see the program clearly, trust the need, and understand where support goes.",
            ),
            GalleryItem(
                src=_clean(
                    self.config.get("DEMO_GALLERY_1"),
                    "/static/images/7thGold.jpg",
                ),
                alt="Team photo",
                caption="Development and competition",
                body="Support helps fund the real work behind training, preparation, and game-day performance.",
            ),
            GalleryItem(
                src=_clean(
                    self.config.get("DEMO_GALLERY_2"),
                    "/static/images/8thGold.jpg",
                ),
                alt="Program image",
                caption="Training and tournament travel",
                body="The season depends on more than one weekend — support keeps the full schedule moving.",
            ),
        ]

    def _support_areas(self) -> list[SupportArea]:
        return [
            SupportArea(
                amount=2500,
                title="Travel and tournament access",
                body="Support helps cover entry fees, weekend travel, lodging pressure, and the logistics that come with serious competition.",
                featured=True,
            ),
            SupportArea(
                amount=1800,
                title="Training and gym time",
                body="Funding supports practice access, development sessions, and the repetition needed to keep athletes improving across the season.",
            ),
            SupportArea(
                amount=1200,
                title="Shared team needs",
                body="Equipment, uniforms, media, recovery essentials, and other program-wide costs add up quickly and need clean, predictable support.",
            ),
        ]

    def _teams(self, goal: int) -> list[TeamSpotlight]:
        default_goal = goal or 10000
        default_raised = max(175, _non_negative_int(self.config.get("DEMO_TEAM_RAISED"), 175))

        return [
            TeamSpotlight(
                id="6g",
                name="6th Grade Gold",
                tier="Gold",
                meta="First AAU reps — fundamentals, spacing, and confidence.",
                goal=default_goal,
                raised=default_raised,
                featured=True,
                photo=_clean(
                    self.config.get("DEMO_TEAM_6G_PHOTO"), "/static/images/connect-atx-team.jpg"
                ),
                ask="Support helps cover tournament fees, gym time, and shared development costs for the full program while keeping this group moving forward.",
                label="Featured team",
            ),
            TeamSpotlight(
                id="7g",
                name="7th Grade Gold",
                tier="Gold",
                meta="Speed, pressure reps, and weekend competition growth.",
                goal=default_goal,
                raised=default_raised,
                featured=True,
                photo=_clean(self.config.get("DEMO_TEAM_7G_PHOTO"), "/static/images/7thGold.jpg"),
                ask="Support helps relieve travel and entry-fee pressure while giving the program more room to focus on training and competition.",
                label="Featured team",
            ),
            TeamSpotlight(
                id="7b",
                name="7th Grade Black",
                tier="Black",
                meta="Defense, physicality, and team habits that translate to game day.",
                goal=default_goal,
                raised=default_raised,
                needs=True,
                photo=_clean(self.config.get("DEMO_TEAM_7B_PHOTO"), "/static/images/7thBlack.png"),
                ask="Support helps cover uniforms, training, weekend logistics, and the program-wide essentials that keep this team prepared.",
                label="Program support",
            ),
            TeamSpotlight(
                id="8g",
                name="8th Grade Gold",
                tier="Gold",
                meta="Leadership, late-season discipline, and stronger finish-through-contact play.",
                goal=default_goal,
                raised=default_raised,
                photo=_clean(self.config.get("DEMO_TEAM_8G_PHOTO"), "/static/images/8thGold.jpg"),
                ask="Support helps fund gym rentals, competition costs, and the shared resources needed to finish the season well.",
                label="Program support",
            ),
        ]

    def _faq(self) -> list[FAQItem]:
        return [
            FAQItem(
                question="What does support for this campaign help cover?",
                answer="Support helps cover the real costs behind the season and the program, including travel, training, tournament fees, equipment, and shared team needs that keep opportunities open for families.",
            ),
            FAQItem(
                question="Can I contribute without creating an account?",
                answer="Yes. The giving experience is designed to be straightforward and low-friction, with a secure checkout path that does not require supporters to create a separate account first.",
            ),
            FAQItem(
                question="Is this page only for donations, or can businesses sponsor too?",
                answer="Both are supported. Individual supporters can give directly, and businesses can use the sponsor lane to review package options and submit interest through a cleaner, more structured process.",
            ),
            FAQItem(
                question="Does support go to one specific team or the broader program?",
                answer="The campaign is structured to support the broader organization and shared season costs. Team spotlights are shown to give context and visibility, but the fundraising surface is designed to support the program as a whole.",
            ),
            FAQItem(
                question="How do I ask a question about support, receipts, or sponsorship?",
                answer="Use the contact path provided on this page or reach out to the organizer/support email listed below. The goal is to make follow-up clear for donors, families, and sponsor contacts.",
            ),
        ]

    def _sponsor_tiers(self) -> list[SponsorTier]:
        return self._sponsors_service().get_sponsor_tiers()

    def _sponsor_wall(self) -> list[SponsorWallItem]:
        return self._sponsors_service().get_sponsor_wall()


def build_campaign_service(config: Mapping[str, Any]) -> CampaignService:
    return CampaignService(config=config)
