from __future__ import annotations

import os
import re
from typing import Any

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.sponsor_service import SponsorService

router = APIRouter()

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


def _notify_email() -> str:
    return (
        _clean(os.getenv("SPONSOR_CONTACT_EMAIL"))
        or _clean(os.getenv("SUPPORT_EMAIL"))
        or "support@getfuturefunded.com"
    )


def _service() -> SponsorService:
    return SponsorService(notify_email=_notify_email())


def _set_response_headers(
    response: Response,
    *,
    request_id: str | None = None,
    cache_control: str = "no-store, max-age=0",
    robots: str = "noindex, nofollow",
) -> None:
    response.headers["Cache-Control"] = cache_control
    response.headers["X-Robots-Tag"] = robots
    if request_id:
        response.headers["X-Request-Id"] = request_id


@router.post("/lead")
@router.post("/lead/")
async def create_sponsor_lead(
    payload: SponsorLeadIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, Any]:
    _set_response_headers(response, request_id=x_request_id)

    result = _service().create_lead_response(payload.model_dump(mode="json"))
    if x_request_id and isinstance(result, dict):
        result.setdefault("request_id", x_request_id)
    return result


@router.post("/wall-item")
@router.post("/wall-item/")
async def sponsor_wall_item(
    payload: SponsorLeadIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, Any]:
    _set_response_headers(response, request_id=x_request_id)

    item = _service().sponsor_wall_item(payload.model_dump(mode="json"))
    result = {
        "ok": True,
        "item": item,
    }
    if x_request_id:
        result["request_id"] = x_request_id
    return result
