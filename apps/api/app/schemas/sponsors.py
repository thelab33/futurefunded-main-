from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


class SponsorLeadIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    business_name: str = Field(..., min_length=1, max_length=120)
    contact_name: str = Field(default="", max_length=120)
    contact_email: EmailStr
    contact_phone: str = Field(default="", max_length=32)
    sponsor_tier: str = Field(default="", max_length=80)
    message: str = Field(default="", max_length=2000)
    campaign_slug: str = Field(default="campaign", min_length=1, max_length=120)

    @field_validator("business_name", "contact_name", "contact_phone", "sponsor_tier", "message")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return _clean(value)

    @field_validator("campaign_slug")
    @classmethod
    def normalize_campaign_slug(cls, value: str) -> str:
        cleaned = _clean(value).lower()
        if not cleaned:
            raise ValueError("campaign_slug is required.")
        if not _SLUG_RE.fullmatch(cleaned):
            raise ValueError("campaign_slug must be a valid slug.")
        return cleaned


class SponsorLeadRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lead_id: str = Field(..., min_length=1, max_length=64)
    business_name: str = Field(..., min_length=1, max_length=120)
    contact_name: str = Field(default="", max_length=120)
    contact_email: str = Field(..., min_length=1, max_length=254)
    contact_phone: str = Field(default="", max_length=32)
    sponsor_tier: str = Field(default="", max_length=80)
    message: str = Field(default="", max_length=2000)
    campaign_slug: str = Field(..., min_length=1, max_length=120)
    status: str = Field(default="new", max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator(
        "lead_id",
        "business_name",
        "contact_name",
        "contact_email",
        "contact_phone",
        "sponsor_tier",
        "message",
        "status",
        mode="before",
    )
    @classmethod
    def trim_record_text(cls, value: Any) -> str:
        return _clean(value)

    @field_validator("campaign_slug", mode="before")
    @classmethod
    def normalize_record_campaign_slug(cls, value: Any) -> str:
        cleaned = _clean(value).lower()
        if not cleaned:
            raise ValueError("campaign_slug is required.")
        if not _SLUG_RE.fullmatch(cleaned):
            raise ValueError("campaign_slug must be a valid slug.")
        return cleaned


class SponsorLeadOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    message: str
    notify_email: str | None = None
    errors: list[str] = Field(default_factory=list)
    lead: SponsorLeadRecord
    request_id: str | None = None


class SponsorWallItemRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=120)
    tier: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=255)
    featured: bool = False

    @field_validator("name", "tier", "description", mode="before")
    @classmethod
    def trim_wall_item_text(cls, value: Any) -> str:
        return _clean(value)


class SponsorWallItemOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    item: SponsorWallItemRecord
    request_id: str | None = None
