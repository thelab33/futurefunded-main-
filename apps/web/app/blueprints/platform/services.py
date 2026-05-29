from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.web.app.domain.onboarding import OnboardingSubmission
from apps.web.app.domain.organization import Organization
from apps.web.app.viewmodels.onboarding_vm import OnboardingViewModel
from apps.web.app.viewmodels.platform_vm import PlatformViewModel


DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_SLUG
DEFAULT_CAMPAIGN_NAME = DEFAULT_TEAM_NAME
DEFAULT_SUPPORT_EMAIL = "support@getfuturefunded.com"


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


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


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _path(path: str) -> str:
    safe = _clean(path, "/")
    return safe if safe.startswith("/") else f"/{safe}"


@dataclass(slots=True)
class PlatformService:
    """Product-context service for FutureFunded platform surfaces.

    This intentionally stays framework-light:
    - no Flask request dependency
    - no database dependency
    - safe demo defaults
    - centralized URLs/context for templates and scripts
    """

    config: Mapping[str, Any]

    # ------------------------------------------------------------------
    # Environment / brand helpers
    # ------------------------------------------------------------------

    def _public_base_url(self) -> str:
        return _clean(self.config.get("PUBLIC_BASE_URL")).rstrip("/")

    def _api_base_url(self) -> str:
        return _clean(self.config.get("API_BASE_URL")).rstrip("/")

    def _support_email(self) -> str:
        return _clean(self.config.get("SUPPORT_EMAIL"), DEFAULT_SUPPORT_EMAIL)

    def _campaign_slug(self) -> str:
        return _clean(
            self.config.get("DEMO_CAMPAIGN_SLUG")
            or self.config.get("DEFAULT_CAMPAIGN_SLUG"),
            DEFAULT_CAMPAIGN_SLUG,
        )

    def _campaign_name(self) -> str:
        return _clean(
            self.config.get("DEMO_CAMPAIGN_NAME")
            or self.config.get("DEFAULT_CAMPAIGN_NAME"),
            DEFAULT_CAMPAIGN_NAME,
        )

    def _campaign_goal(self) -> int:
        return _positive_int(self.config.get("DEMO_GOAL"), 20000)

    def _campaign_raised(self) -> int:
        return _non_negative_int(self.config.get("DEMO_RAISED"), 11850)

    def _campaign_supporters(self) -> int:
        return _non_negative_int(self.config.get("DEMO_SUPPORTERS"), 143)

    def _campaign_urls(self) -> dict[str, str]:
        slug = self._campaign_slug()
        return {
            "campaign_url": _path(f"/c/{slug}"),
            "platform_home_url": _path("/platform/"),
            "onboarding_url": _path("/platform/onboarding"),
            "dashboard_url": _path("/platform/dashboard"),
            "ledger_url": _path(f"/c/{slug}/ledger/summary"),
            "events_url": _path(f"/c/{slug}/ledger/events"),
            "offline_url": _path(f"/c/{slug}/ledger/offline-donation"),
            "export_url": _path(f"/c/{slug}/ledger/export.csv"),
        }

    def _platform_routes(self) -> dict[str, str]:
        urls = self._campaign_urls()
        return {
            "home": urls["platform_home_url"],
            "onboarding": urls["onboarding_url"],
            "dashboard": urls["dashboard_url"],
            "campaign": urls["campaign_url"],
            "ledger": urls["ledger_url"],
            "events": urls["events_url"],
            "offline": urls["offline_url"],
            "export": urls["export_url"],
            "login": _path("/platform/login"),
            "logout": _path("/platform/logout"),
        }

    def _base_page_context(self, organization: Organization) -> dict[str, Any]:
        urls = self._campaign_urls()

        return {
            "brand_name": organization.display_name,
            "support_email": organization.support_email,
            "theme": organization.theme.theme,
            "density": organization.theme.density,
            "theme_color": organization.theme.theme_color,
            "theme_color_dark": organization.theme.theme_color_dark,
            "platform_logo": organization.theme.platform_logo,
            "public_base_url": self._public_base_url(),
            "api_base_url": self._api_base_url(),
            "campaign_slug": self._campaign_slug(),
            "campaign_name": self._campaign_name(),
            "platform_routes": self._platform_routes(),
            **urls,
        }

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    def get_organization(self) -> Organization:
        support_email = self._support_email()

        return Organization.from_dict(
            {
                "slug": "futurefunded",
                "name": _clean(self.config.get("BRAND_NAME"), "FutureFunded"),
                "support_email": support_email,
                "sponsor_contact_email": _clean(
                    self.config.get("SPONSOR_CONTACT_EMAIL"),
                    support_email,
                ),
                "logo_url": _clean(self.config.get("PLATFORM_LOGO")),
                "theme": {
                    "theme": _clean(self.config.get("DEFAULT_THEME"), "light"),
                    "density": _clean(self.config.get("DEFAULT_DENSITY"), "compact"),
                    "theme_color": _clean(self.config.get("THEME_COLOR"), "#f97316"),
                    "theme_color_dark": _clean(self.config.get("THEME_COLOR_DARK"), "#0b0f17"),
                    "platform_logo": _clean(self.config.get("PLATFORM_LOGO")),
                },
                "metadata": {
                    "public_base_url": self._public_base_url(),
                    "api_base_url": self._api_base_url(),
                    "campaign_slug": self._campaign_slug(),
                    "campaign_name": self._campaign_name(),
                },
            }
        )

    # ------------------------------------------------------------------
    # Platform homepage
    # ------------------------------------------------------------------

    def get_platform_context(self) -> dict[str, Any]:
        organization = self.get_organization()
        vm = PlatformViewModel.from_organization(organization)
        context = dict(vm.to_template_context())

        urls = self._campaign_urls()

        context.update(
            {
                "page_title": vm.page_title,
                "page_description": vm.page_description,
                "platform_launch_url": urls["onboarding_url"],
                "platform_dashboard_url": urls["dashboard_url"],
                "campaign_demo_url": urls["campaign_url"],
                **self._base_page_context(organization),
            }
        )

        return context

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    def get_onboarding_submission(
        self,
        payload: Mapping[str, Any] | None = None,
    ) -> OnboardingSubmission:
        safe_payload = dict(payload or self._default_onboarding_payload())
        return OnboardingSubmission.from_dict(safe_payload)

    def get_onboarding_context(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        organization = self.get_organization()
        submission = self.get_onboarding_submission(payload)
        vm = OnboardingViewModel.from_submission(
            submission=submission,
            organization=organization,
        )

        context = dict(vm.to_template_context())

        context.update(
            {
                "page_title": vm.page_title,
                "page_description": vm.page_description,
                "onboarding_defaults": self._default_onboarding_payload(),
                "campaign_preview_url": self._campaign_urls()["campaign_url"],
                **self._base_page_context(organization),
            }
        )

        return context

    def _default_onboarding_payload(self) -> dict[str, Any]:
        campaign_name = self._campaign_name()
        goal = self._campaign_goal()

        return {
            "organization_name": _clean(
                self.config.get("DEMO_ORGANIZATION_NAME"),
                DEFAULT_CAMPAIGN_NAME,
            ),
            "organization_type": _clean(
                self.config.get("DEMO_ORGANIZATION_TYPE"),
                "Youth team",
            ),
            "campaign_name": _clean(
                self.config.get("DEMO_CAMPAIGN_DISPLAY_NAME"),
                f"{campaign_name} Season Fund",
            ),
            "location": _clean(self.config.get("DEMO_LOCATION"), DEFAULT_LOCATION),
            "goal": goal,
            "launch_window": _clean(
                self.config.get("DEMO_LAUNCH_WINDOW"),
                "Before season launch",
            ),
            "primary_audience": _clean(
                self.config.get("DEMO_PRIMARY_AUDIENCE"),
                "Families, alumni, local businesses",
            ),
            "operator_email": _clean(
                self.config.get("DEMO_OPERATOR_EMAIL"),
                self._support_email(),
            ),
            "support_story": _clean(
                self.config.get("DEMO_SUPPORT_STORY"),
                "Travel, training, tournament fees, equipment, meals, scholarships, and shared program costs.",
            ),
            "campaign_summary": _clean(
                self.config.get("DEMO_CAMPAIGN_SUMMARY"),
                "A clear, sponsor-safe summary of the organization, campaign purpose, and why support matters now.",
            ),
            "primary_sponsor_package": _clean(
                self.config.get("DEMO_PRIMARY_SPONSOR_PACKAGE"),
                "Featured Sponsor · $1,500",
            ),
            "payment_stack": _clean(
                self.config.get("DEMO_PAYMENT_STACK"),
                "Stripe, PayPal, or both",
            ),
            "launch_notes": _clean(
                self.config.get("DEMO_LAUNCH_NOTES"),
                "Confirm campaign story, sponsor package, payment path, and campaign media before public launch.",
            ),
            "theme_color": _clean(self.config.get("THEME_COLOR"), "#f97316"),
            "theme_color_dark": _clean(self.config.get("THEME_COLOR_DARK"), "#0b0f17"),
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard_context(self) -> dict[str, Any]:
        organization = self.get_organization()

        raised = self._campaign_raised()
        goal = self._campaign_goal()
        supporters = self._campaign_supporters()
        sponsor_leads = _non_negative_int(self.config.get("DEMO_SPONSOR_LEADS"), 7)
        recent_events = _non_negative_int(self.config.get("DEMO_RECENT_EVENTS"), 12)

        remaining = max(0, goal - raised)
        average_gift = int(round(raised / supporters)) if supporters > 0 else 0
        progress_percent = _clamp(int((raised / goal) * 100) if goal > 0 else 0, 0, 100)

        metrics = {
            "raised": raised,
            "goal": goal,
            "supporters": supporters,
            "sponsor_leads": sponsor_leads,
            "remaining": remaining,
            "average_gift": average_gift,
            "progress_percent": progress_percent,
            "recent_events": recent_events,
        }

        context = {
            "page_title": f"{self._campaign_name()} Dashboard • FutureFunded",
            "page_description": "Operator view for campaign health, sponsor pipeline, payment confidence, and launch readiness.",
            **self._base_page_context(organization),
            "dashboard_metrics": metrics,
            "dashboard_launch_status": [
                {
                    "label": "Public page",
                    "status": "Live",
                    "detail": "campaign surface responding",
                },
                {
                    "label": "Checkout",
                    "status": "Ready",
                    "detail": "secure payment shell active",
                },
                {
                    "label": "Ledger",
                    "status": "Tracking",
                    "detail": "verified sessions reconciled",
                },
                {
                    "label": "Sponsors",
                    "status": "Review",
                    "detail": "package follow-up enabled",
                },
            ],
            "dashboard_workflow": [
                {
                    "step": "01",
                    "title": "Confirm gifts",
                    "detail": "review successful payments and any offline support",
                },
                {
                    "step": "02",
                    "title": "Follow up",
                    "detail": "turn sponsor interest into real placement conversations",
                },
                {
                    "step": "03",
                    "title": "Export records",
                    "detail": "keep reporting clean for coaches, admins, and families",
                },
                {
                    "step": "04",
                    "title": "Share page",
                    "detail": "send the public campaign link when the story is ready",
                },
            ],
            "dashboard_recommendations": [
                "publish one campaign update tied to a real funding need",
                "follow up with open sponsor leads while the page is active",
                "refresh one support area or story section with concrete details",
                "share the campaign again once the next visible milestone is reached",
            ],
            "dashboard_sponsor_snapshots": [
                "Featured sponsor inquiry from a local training facility",
                "Community partner interest from a family-owned restaurant",
                "Silver tier lead from a neighborhood service business",
                "One pending follow-up awaiting logo and billing confirmation",
            ],
        }

        return context


def build_platform_service(config: Mapping[str, Any]) -> PlatformService:
    return PlatformService(config=config)
