from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class BrandTheme:
    theme: str = "dark"
    density: str = "compact"
    theme_color: str = "#f97316"
    theme_color_dark: str = "#0b0f17"
    platform_logo: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BrandTheme:
        data = data or {}
        return cls(
            theme=_clean(data.get("theme"), "dark").lower(),
            density=_clean(data.get("density"), "compact").lower(),
            theme_color=_clean(data.get("theme_color"), "#f97316"),
            theme_color_dark=_clean(data.get("theme_color_dark"), "#0b0f17"),
            platform_logo=_clean(data.get("platform_logo")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Organization:
    slug: str
    name: str
    location: str = ""
    support_email: str = "support@getfuturefunded.com"
    sponsor_contact_email: str = ""
    organizer_label: str = ""
    description: str = ""
    logo_url: str = ""
    website_url: str = ""
    theme: BrandTheme = field(default_factory=BrandTheme)
    school_safe: bool = True
    institution_safe: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return self.name or self.slug.replace("-", " ").title()

    @property
    def primary_contact_email(self) -> str:
        return self.sponsor_contact_email or self.support_email

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Organization:
        data = data or {}
        return cls(
            slug=_clean(data.get("slug"), "organization"),
            name=_clean(data.get("name"), "Organization"),
            location=_clean(data.get("location")),
            support_email=_clean(data.get("support_email"), "support@getfuturefunded.com"),
            sponsor_contact_email=_clean(data.get("sponsor_contact_email")),
            organizer_label=_clean(data.get("organizer_label")),
            description=_clean(data.get("description")),
            logo_url=_clean(data.get("logo_url")),
            website_url=_clean(data.get("website_url")),
            theme=BrandTheme.from_dict(data.get("theme")),
            school_safe=_bool(data.get("school_safe"), True),
            institution_safe=_bool(data.get("institution_safe"), True),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["theme"] = self.theme.to_dict()
        return payload
