from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")

_ALLOWED_TIERS = {
    "Featured Sponsor": {"featured": True},
    "Community Sponsor": {"featured": False},
    "Supporting Sponsor": {"featured": False},
}


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int, default: str = "") -> str:
    return _clean(value, default)[:limit].strip()


def _normalize_email(value: Any) -> str:
    return _truncate(value, 254).lower()


def _normalize_slug(value: Any, default: str = "campaign") -> str:
    return _truncate(value, 120, default).lower() or default


def _normalize_tier(value: Any) -> str:
    raw = _truncate(value, 80)
    if not raw:
        return ""

    lowered = raw.lower()
    aliases = {
        "featured": "Featured Sponsor",
        "featured sponsor": "Featured Sponsor",
        "community": "Community Sponsor",
        "community sponsor": "Community Sponsor",
        "supporting": "Supporting Sponsor",
        "supporting sponsor": "Supporting Sponsor",
    }
    return aliases.get(lowered, raw)


def _looks_like_email(value: str) -> bool:
    return bool(value and _EMAIL_RE.fullmatch(value))


@dataclass(slots=True)
class SponsorService:
    notify_email: str = "support@getfuturefunded.com"

    def normalize_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        campaign_slug = _normalize_slug(payload.get("campaign_slug"))
        sponsor_tier = _normalize_tier(payload.get("sponsor_tier"))

        return {
            "lead_id": _truncate(payload.get("lead_id"), 64, f"lead_{uuid4().hex[:18]}"),
            "business_name": _truncate(payload.get("business_name"), 120, "Sponsor"),
            "contact_name": _truncate(payload.get("contact_name"), 120, "Primary Contact"),
            "contact_email": _normalize_email(payload.get("contact_email")),
            "contact_phone": _truncate(payload.get("contact_phone"), 32),
            "sponsor_tier": sponsor_tier,
            "message": _truncate(payload.get("message"), 2000),
            "campaign_slug": campaign_slug,
            "status": _truncate(payload.get("status"), 32, "new").lower() or "new",
            "created_at": _truncate(payload.get("created_at"), 64, datetime.now(UTC).isoformat()),
        }

    def validate_lead(self, normalized: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not normalized["business_name"]:
            errors.append("business_name is required")

        if not normalized["contact_email"]:
            errors.append("contact_email is required")
        elif not _looks_like_email(normalized["contact_email"]):
            errors.append("contact_email must be a valid email")

        if not normalized["campaign_slug"]:
            errors.append("campaign_slug is required")
        elif not _SLUG_RE.fullmatch(normalized["campaign_slug"]):
            errors.append("campaign_slug must be a valid slug")

        if normalized["sponsor_tier"] and normalized["sponsor_tier"] not in _ALLOWED_TIERS:
            errors.append("sponsor_tier must match an available sponsor package")

        return errors

    def create_lead_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalize_lead(payload)
        errors = self.validate_lead(normalized)

        if errors:
            return {
                "ok": False,
                "message": "Sponsor lead validation failed.",
                "errors": errors,
                "lead": normalized,
            }

        return {
            "ok": True,
            "message": "Sponsor lead accepted.",
            "notify_email": _truncate(self.notify_email, 254, "support@getfuturefunded.com"),
            "lead": normalized,
        }

    def sponsor_wall_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalize_lead(payload)
        tier = normalized["sponsor_tier"] or "Sponsor"
        tier_meta = _ALLOWED_TIERS.get(tier, {"featured": False})

        return {
            "name": normalized["business_name"],
            "tier": tier,
            "description": f'{tier} supporting {normalized["campaign_slug"]}',
            "featured": bool(tier_meta["featured"]),
        }
