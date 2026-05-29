from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_EVENT_TYPE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]{0,78}[a-z0-9])?$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _normalize_event_type(value: Any) -> str:
    cleaned = _clean(value).lower()
    if not cleaned:
        raise ValueError("event_type is required.")
    if not _EVENT_TYPE_RE.fullmatch(cleaned):
        raise ValueError("event_type must be a valid event key.")
    return cleaned


def _normalize_slug(value: Any) -> str | None:
    cleaned = _clean(value).lower()
    if not cleaned:
        return None
    if not _SLUG_RE.fullmatch(cleaned):
        raise ValueError("campaign_slug must be a valid slug.")
    return cleaned


def _normalize_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_path(value: Any) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return cleaned if cleaned.startswith("/") else f"/{cleaned.lstrip('/')}"


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: str = Field(..., min_length=1, max_length=80)
    event_source: str = Field(..., min_length=1, max_length=32)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = Field(default=None, max_length=128)
    campaign_slug: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, value: Any) -> str:
        return _normalize_event_type(value)

    @field_validator("event_source", mode="before")
    @classmethod
    def trim_event_source(cls, value: Any) -> str:
        cleaned = _clean(value).lower()
        if not cleaned:
            raise ValueError("event_source is required.")
        return cleaned

    @field_validator("request_id", mode="before")
    @classmethod
    def trim_request_id(cls, value: Any) -> str | None:
        cleaned = _clean(value)
        return cleaned or None

    @field_validator("campaign_slug", mode="before")
    @classmethod
    def normalize_campaign_slug(cls, value: Any) -> str | None:
        return _normalize_slug(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: Any) -> dict[str, Any]:
        return _normalize_dict(value)


class AnalyticsEventIn(EventEnvelope):
    event_source: Literal["web", "api", "admin", "system"] = "web"
    path: str | None = Field(default=None, max_length=512)
    session_id: str | None = Field(default=None, max_length=120)
    user_agent: str | None = Field(default=None, max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_source", mode="before")
    @classmethod
    def normalize_analytics_event_source(cls, value: Any) -> str:
        cleaned = _clean(value, "web").lower()
        return cleaned or "web"

    @field_validator("path", mode="before")
    @classmethod
    def normalize_path(cls, value: Any) -> str | None:
        return _normalize_path(value)

    @field_validator("session_id", "user_agent", "referrer", mode="before")
    @classmethod
    def trim_optional_text(cls, value: Any) -> str | None:
        cleaned = _clean(value)
        return cleaned or None

    @field_validator("properties", mode="before")
    @classmethod
    def normalize_properties(cls, value: Any) -> dict[str, Any]:
        return _normalize_dict(value)


class PaymentWebhookEvent(EventEnvelope):
    event_source: Literal["stripe", "paypal"] = "stripe"
    provider_event_id: str | None = Field(default=None, max_length=120)
    checkout_kind: Literal["donation", "sponsor", "membership"] = "donation"
    amount: Decimal | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    provider_status: str | None = Field(default=None, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_source", mode="before")
    @classmethod
    def normalize_payment_event_source(cls, value: Any) -> str:
        cleaned = _clean(value, "stripe").lower()
        return cleaned or "stripe"

    @field_validator("provider_event_id", "provider_status", mode="before")
    @classmethod
    def trim_payment_text(cls, value: Any) -> str | None:
        cleaned = _clean(value)
        return cleaned or None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> str:
        cleaned = _clean(value, "USD").upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("currency must be a 3-letter ISO code.")
        return cleaned

    @field_validator("payload", mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> dict[str, Any]:
        return _normalize_dict(value)


class SponsorLeadEvent(EventEnvelope):
    event_source: Literal["web", "api", "system"] = "web"
    sponsor_tier: str | None = Field(default=None, max_length=80)
    business_name: str | None = Field(default=None, max_length=120)
    contact_email: EmailStr | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_source", mode="before")
    @classmethod
    def normalize_sponsor_event_source(cls, value: Any) -> str:
        cleaned = _clean(value, "web").lower()
        return cleaned or "web"

    @field_validator("sponsor_tier", "business_name", mode="before")
    @classmethod
    def trim_sponsor_text(cls, value: Any) -> str | None:
        cleaned = _clean(value)
        return cleaned or None

    @field_validator("payload", mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> dict[str, Any]:
        return _normalize_dict(value)


class EventAccepted(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    event_type: str
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str = "Event accepted for processing."
    request_id: str | None = None

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, value: Any) -> str:
        return _normalize_event_type(value)

    @field_validator("request_id", mode="before")
    @classmethod
    def trim_request_id(cls, value: Any) -> str | None:
        cleaned = _clean(value)
        return cleaned or None
