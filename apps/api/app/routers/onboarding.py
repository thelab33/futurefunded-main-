from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

router = APIRouter()


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


class OnboardingIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    organization_name: str = Field(default="", max_length=120)
    campaign_name: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    goal: int = Field(default=0, ge=0, le=1_000_000_000)
    operator_email: EmailStr | None = None
    support_story: str = Field(default="", max_length=4000)
    campaign_summary: str = Field(default="", max_length=600)
    primary_sponsor_package: str = Field(default="", max_length=200)
    payment_stack: str = Field(default="", max_length=120)

    @field_validator(
        "organization_name",
        "campaign_name",
        "location",
        "support_story",
        "campaign_summary",
        "primary_sponsor_package",
        "payment_stack",
    )
    @classmethod
    def trim_text(cls, value: str) -> str:
        return _clean(value)

    @field_validator("operator_email", mode="before")
    @classmethod
    def normalize_operator_email(cls, value: Any) -> Any:
        cleaned = _clean(value)
        return cleaned or None

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, value: Any) -> Any:
        cleaned = _clean(value)
        return 0 if cleaned == "" else value


def _set_response_headers(
    response: Response,
    *,
    request_id: str | None = None,
    cache_control: str = "no-store, max-age=0",
    robots: str = "noindex, nofollow",
) -> None:
    response.headers.setdefault("Cache-Control", cache_control)
    response.headers.setdefault("X-Robots-Tag", robots)
    if request_id:
        response.headers.setdefault("X-Request-Id", request_id)


def _summary(payload: OnboardingIn) -> str:
    parts = [
        payload.organization_name and f"Organization: {payload.organization_name}",
        payload.campaign_name and f"Campaign: {payload.campaign_name}",
        payload.location and f"Location: {payload.location}",
        payload.goal and f"Goal: ${payload.goal:,.0f}",
        payload.operator_email and f"Operator email: {payload.operator_email}",
        payload.primary_sponsor_package and f"Sponsor package: {payload.primary_sponsor_package}",
        payload.payment_stack and f"Payments: {payload.payment_stack}",
    ]
    return " • ".join(part for part in parts if part) or "No onboarding details yet."


def _missing_fields(payload: OnboardingIn) -> list[str]:
    missing: list[str] = []
    if not payload.organization_name:
        missing.append("organization_name")
    if not payload.campaign_name:
        missing.append("campaign_name")
    if not payload.operator_email:
        missing.append("operator_email")
    if not payload.campaign_summary:
        missing.append("campaign_summary")
    return missing


def _completion_ratio(payload: OnboardingIn) -> int:
    required_total = 4
    complete = required_total - len(_missing_fields(payload))
    return int(round((complete / required_total) * 100))


def _submission(payload: OnboardingIn) -> dict[str, Any]:
    data = payload.model_dump(mode="json")
    if data.get("operator_email") is None:
        data["operator_email"] = ""
    return data


def _ready_for_launch(payload: OnboardingIn) -> bool:
    return not _missing_fields(payload) and payload.goal > 0 and bool(payload.payment_stack)


@router.post("/save")
@router.post("/save/")
async def save_onboarding(
    payload: OnboardingIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, Any]:
    _set_response_headers(response, request_id=x_request_id)

    missing = _missing_fields(payload)
    return {
        "ok": len(missing) == 0,
        "missing_fields": missing,
        "summary": _summary(payload),
        "submission": _submission(payload),
        "completion_ratio": _completion_ratio(payload),
        "ready_for_launch": _ready_for_launch(payload),
        "request_id": x_request_id,
    }


@router.post("/validate")
@router.post("/validate/")
async def validate_onboarding(
    payload: OnboardingIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> dict[str, Any]:
    _set_response_headers(response, request_id=x_request_id)

    missing = _missing_fields(payload)
    return {
        "ok": len(missing) == 0,
        "missing_fields": missing,
        "message": (
            "Onboarding payload is valid." if not missing else "Onboarding payload is incomplete."
        ),
        "completion_ratio": _completion_ratio(payload),
        "ready_for_launch": _ready_for_launch(payload),
        "request_id": x_request_id,
    }
