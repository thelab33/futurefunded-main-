from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor", "membership"}


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


class _PaymentBaseIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    campaign_slug: str = Field(..., min_length=1, max_length=120)
    amount: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    donor_name: str = Field(default="", max_length=120)
    donor_email: EmailStr | None = None
    donor_message: str = Field(default="", max_length=500)
    team_id: str = Field(default="", max_length=120)
    checkout_kind: Literal["donation", "sponsor", "membership"] = "donation"

    @field_validator("campaign_slug")
    @classmethod
    def normalize_campaign_slug(cls, value: str) -> str:
        cleaned = _clean(value).lower()
        if not cleaned:
            raise ValueError("campaign_slug is required.")
        return cleaned

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: Any) -> Any:
        if value is None or _clean(value) == "":
            raise ValueError("amount is required.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        cleaned = _clean(value).upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("currency must be a 3-letter ISO code.")
        return cleaned

    @field_validator("donor_name", "donor_message", "team_id")
    @classmethod
    def trim_optional_text(cls, value: str) -> str:
        return _clean(value)

    @field_validator("checkout_kind")
    @classmethod
    def normalize_checkout_kind(cls, value: str) -> str:
        cleaned = _clean(value).lower()
        if cleaned not in _ALLOWED_CHECKOUT_KINDS:
            raise ValueError("checkout_kind is invalid.")
        return cleaned


class StripeIntentIn(_PaymentBaseIn):
    pass


class PayPalOrderIn(_PaymentBaseIn):
    pass


class PayPalCaptureIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("order_id")
    @classmethod
    def normalize_order_id(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("order_id is required.")
        return cleaned


class PaymentProviderPublicConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: Literal["stripe", "paypal"]
    enabled: bool = False
    currency: str = "USD"
    publishable_key: str | None = None
    client_id: str | None = None
    environment: str | None = None
    sdk_available: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        cleaned = _clean(value).upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("currency must be a 3-letter ISO code.")
        return cleaned

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = _clean(value).lower()
        return cleaned or None


class PaymentConfigOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    providers: dict[str, PaymentProviderPublicConfig]


class StripeIntentOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    provider: Literal["stripe"] = "stripe"
    status: str
    message: str | None = None
    error_code: str | None = None
    intent_id: str | None = None
    client_secret: str | None = None
    intent_payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class PayPalOrderOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    provider: Literal["paypal"] = "paypal"
    status: str
    message: str | None = None
    error_code: str | None = None
    order_id: str | None = None
    order_payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class PayPalCaptureOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool
    provider: Literal["paypal"] = "paypal"
    status: str
    message: str | None = None
    error_code: str | None = None
    order_id: str | None = None
    capture_id: str | None = None
    request_id: str | None = None


class WebhookEventOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    received: bool = True
    event: dict[str, Any] = Field(default_factory=dict)
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
