from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OnboardingIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    organization_name: str = ""
    campaign_name: str = ""
    location: str = ""
    goal: int = Field(default=0, ge=0)
    operator_email: EmailStr | None = None
    support_story: str = ""
    campaign_summary: str = ""
    primary_sponsor_package: str = ""
    payment_stack: str = ""


class OnboardingValidationOut(BaseModel):
    ok: bool
    missing_fields: list[str] = Field(default_factory=list)
    message: str


class OnboardingSaveOut(BaseModel):
    ok: bool
    missing_fields: list[str] = Field(default_factory=list)
    summary: str
    submission: dict[str, Any] = Field(default_factory=dict)
