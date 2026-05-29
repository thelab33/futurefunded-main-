from __future__ import annotations

from dataclasses import asdict, dataclass, field
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


@dataclass(slots=True)
class OnboardingSubmission:
    organization_name: str = ""
    campaign_name: str = ""
    location: str = ""
    goal: int = 0
    operator_email: str = ""
    support_story: str = ""
    campaign_summary: str = ""
    primary_sponsor_package: str = ""
    payment_stack: str = ""
    logo_url: str = ""
    theme_color: str = "#f97316"
    theme_color_dark: str = "#0b0f17"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def missing_fields(self) -> list[str]:
        required = {
            "organization_name": self.organization_name,
            "campaign_name": self.campaign_name,
            "operator_email": self.operator_email,
            "campaign_summary": self.campaign_summary,
        }
        return [key for key, value in required.items() if not _clean(value)]

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields

    @property
    def summary(self) -> str:
        parts = [
            self.organization_name and f"Organization: {self.organization_name}",
            self.campaign_name and f"Campaign: {self.campaign_name}",
            self.location and f"Location: {self.location}",
            self.goal and f"Goal: ${self.goal:,.0f}",
            self.operator_email and f"Operator: {self.operator_email}",
            self.primary_sponsor_package and f"Sponsor package: {self.primary_sponsor_package}",
            self.payment_stack and f"Payments: {self.payment_stack}",
        ]
        return " • ".join(part for part in parts if part) or "No onboarding details yet."

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OnboardingSubmission:
        data = data or {}
        return cls(
            organization_name=_clean(data.get("organization_name")),
            campaign_name=_clean(data.get("campaign_name")),
            location=_clean(data.get("location")),
            goal=_int(data.get("goal"), 0),
            operator_email=_clean(data.get("operator_email")),
            support_story=_clean(data.get("support_story")),
            campaign_summary=_clean(data.get("campaign_summary")),
            primary_sponsor_package=_clean(data.get("primary_sponsor_package")),
            payment_stack=_clean(data.get("payment_stack")),
            logo_url=_clean(data.get("logo_url")),
            theme_color=_clean(data.get("theme_color"), "#f97316"),
            theme_color_dark=_clean(data.get("theme_color_dark"), "#0b0f17"),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
