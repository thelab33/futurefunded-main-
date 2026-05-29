from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.web.app.domain.sponsor import SponsorLead, SponsorTier, SponsorWallItem

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int, default: str = "") -> str:
    return _clean(value, default)[:limit].strip()


def _normalize_slug(value: Any, default: str = "campaign") -> str:
    slug = _truncate(value, 120, default).lower()
    return slug or default


def _looks_like_email(value: str) -> bool:
    return bool(value and _EMAIL_RE.fullmatch(value))


@dataclass(slots=True)
class SponsorsService:
    config: Mapping[str, Any]

    def get_sponsor_contact_email(self) -> str:
        return _clean(
            self.config.get("SPONSOR_CONTACT_EMAIL"),
            _clean(self.config.get("SUPPORT_EMAIL"), "support@getfuturefunded.com"),
        )

    def get_sponsor_tiers(self) -> list[SponsorTier]:
        return [
            SponsorTier(
                id="featured",
                name="Featured Sponsor",
                amount=1500,
                label="Most visible",
                featured=True,
                description="High-visibility placement for a business that wants to be clearly associated with the program and the campaign.",
                includes=[
                    "Featured placement on the campaign page",
                    "Priority sponsor acknowledgment",
                    "Clean lead follow-up and logo collection",
                ],
            ),
            SponsorTier(
                id="community",
                name="Community Sponsor",
                amount=750,
                label="Balanced visibility",
                featured=False,
                description="A strong option for local businesses that want meaningful community visibility without overcomplication.",
                includes=[
                    "Visible sponsor placement",
                    "Included in sponsor recognition",
                    "Simple intake and confirmation path",
                ],
            ),
            SponsorTier(
                id="supporting",
                name="Supporting Sponsor",
                amount=300,
                label="Accessible entry",
                featured=False,
                description="A lighter entry point for partners who want to support the organization and be represented appropriately.",
                includes=[
                    "Sponsor listing on the page",
                    "Community-support acknowledgment",
                    "Clean sponsor intake option",
                ],
            ),
        ]

    def get_sponsor_wall(self) -> list[SponsorWallItem]:
        return [
            SponsorWallItem(
                name="Local Training Facility",
                tier="Featured Sponsor",
                description="Visible community support for the campaign and the broader program.",
                featured=True,
            ),
            SponsorWallItem(
                name="Family-Owned Restaurant",
                tier="Community Sponsor",
                description="Helping support travel, training, and team development.",
                featured=False,
            ),
        ]

    def sponsor_lane_context(self) -> dict[str, Any]:
        return {
            "sponsor_contact_email": self.get_sponsor_contact_email(),
            "sponsor_tiers": [tier.to_dict() for tier in self.get_sponsor_tiers()],
            "sponsor_wall": [item.to_dict() for item in self.get_sponsor_wall()],
            "sponsor_points": [
                "Clear package structure instead of improvised sponsor asks.",
                "Business-safe placement on a calmer, more credible public page.",
                "A cleaner follow-up path for logos, confirmations, and next steps.",
            ],
            "sponsor_benefits": [
                {
                    "title": "Visible community support",
                    "body": "Sponsors can be shown in a way that feels professional to families, alumni, boosters, and local supporters.",
                },
                {
                    "title": "Simple review path",
                    "body": "Businesses should be able to choose a package without reading through cluttered or vague sponsorship language.",
                },
                {
                    "title": "Cleaner public presentation",
                    "body": "The sponsor lane is integrated into the campaign surface instead of feeling bolted on after the fact.",
                },
            ],
        }

    def allowed_tier_names(self) -> set[str]:
        return {tier.name for tier in self.get_sponsor_tiers()}

    def build_lead(self, payload: Mapping[str, Any]) -> SponsorLead:
        source = {
            "business_name": _truncate(payload.get("business_name"), 120),
            "contact_name": _truncate(payload.get("contact_name"), 120, "Primary Contact"),
            "contact_email": _truncate(payload.get("contact_email"), 254).lower(),
            "contact_phone": _truncate(payload.get("contact_phone"), 32),
            "sponsor_tier": _truncate(payload.get("sponsor_tier"), 80),
            "message": _truncate(payload.get("message"), 2000),
            "status": _truncate(payload.get("status"), 32, "new").lower() or "new",
            "campaign_slug": _normalize_slug(payload.get("campaign_slug")),
        }
        return SponsorLead.from_dict(source)

    def normalize_lead(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        lead = self.build_lead(payload)
        normalized = lead.to_dict()

        normalized["business_name"] = _truncate(normalized.get("business_name"), 120)
        normalized["contact_name"] = _truncate(
            normalized.get("contact_name"), 120, "Primary Contact"
        )
        normalized["contact_email"] = _truncate(normalized.get("contact_email"), 254).lower()
        normalized["contact_phone"] = _truncate(normalized.get("contact_phone"), 32)
        normalized["sponsor_tier"] = _truncate(normalized.get("sponsor_tier"), 80)
        normalized["message"] = _truncate(normalized.get("message"), 2000)
        normalized["status"] = _truncate(normalized.get("status"), 32, "new").lower() or "new"
        normalized["campaign_slug"] = _normalize_slug(normalized.get("campaign_slug"))

        return normalized

    def validate_lead(self, lead: Mapping[str, Any]) -> list[str]:
        errors: list[str] = []

        business_name = _clean(lead.get("business_name"))
        contact_email = _clean(lead.get("contact_email")).lower()
        campaign_slug = _clean(lead.get("campaign_slug")).lower()
        sponsor_tier = _clean(lead.get("sponsor_tier"))

        if not business_name:
            errors.append("business_name is required")

        if not contact_email:
            errors.append("contact_email is required")
        elif not _looks_like_email(contact_email):
            errors.append("contact_email must be a valid email")

        if not campaign_slug:
            errors.append("campaign_slug is required")
        elif not _SLUG_RE.fullmatch(campaign_slug):
            errors.append("campaign_slug must be a valid slug")

        if sponsor_tier and sponsor_tier not in self.allowed_tier_names():
            errors.append("sponsor_tier must match an available sponsor package")

        return errors

    def create_lead_response(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        lead = self.normalize_lead(payload)
        errors = self.validate_lead(lead)

        if errors:
            return {
                "ok": False,
                "message": "Sponsor lead validation failed.",
                "errors": errors,
                "lead": lead,
            }

        return {
            "ok": True,
            "message": "Sponsor lead accepted.",
            "notify_email": self.get_sponsor_contact_email(),
            "lead": lead,
        }


def build_sponsors_service(config: Mapping[str, Any]) -> SponsorsService:
    return SponsorsService(config=config)
