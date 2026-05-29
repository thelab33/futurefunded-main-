from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class SponsorTier:
    id: str
    name: str
    amount: int
    label: str = ""
    featured: bool = False
    description: str = ""
    includes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SponsorTier:
        data = data or {}
        return cls(
            id=_clean(data.get("id"), "tier"),
            name=_clean(data.get("name"), "Sponsor Tier"),
            amount=_int(data.get("amount"), 0),
            label=_clean(data.get("label")),
            featured=_bool(data.get("featured")),
            description=_clean(data.get("description")),
            includes=[_clean(item) for item in list(data.get("includes") or []) if _clean(item)],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SponsorWallItem:
    name: str
    tier: str
    description: str = ""
    logo_url: str = ""
    website_url: str = ""
    featured: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SponsorWallItem:
        data = data or {}
        return cls(
            name=_clean(data.get("name"), "Sponsor"),
            tier=_clean(data.get("tier"), "Sponsor"),
            description=_clean(data.get("description")),
            logo_url=_clean(data.get("logo_url")),
            website_url=_clean(data.get("website_url")),
            featured=_bool(data.get("featured")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SponsorLead:
    business_name: str
    contact_name: str
    contact_email: str
    contact_phone: str = ""
    sponsor_tier: str = ""
    message: str = ""
    status: str = "new"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SponsorLead:
        data = data or {}
        return cls(
            business_name=_clean(data.get("business_name"), "Sponsor"),
            contact_name=_clean(data.get("contact_name"), "Primary Contact"),
            contact_email=_clean(data.get("contact_email")),
            contact_phone=_clean(data.get("contact_phone")),
            sponsor_tier=_clean(data.get("sponsor_tier")),
            message=_clean(data.get("message")),
            status=_clean(data.get("status"), "new").lower(),
            created_at=_clean(data.get("created_at")) or datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
