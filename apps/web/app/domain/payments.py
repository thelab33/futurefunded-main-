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


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class PaymentProviderConfig:
    provider: str
    enabled: bool = False
    publishable_key: str = ""
    currency: str = "USD"
    mode: str = "preview"
    intent_endpoint: str = ""
    create_endpoint: str = ""
    capture_endpoint: str = ""
    webhook_endpoint: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PaymentProviderConfig:
        data = data or {}
        return cls(
            provider=_clean(data.get("provider"), "provider").lower(),
            enabled=_bool(data.get("enabled"), False),
            publishable_key=_clean(data.get("publishable_key")),
            currency=_clean(data.get("currency"), "USD").upper(),
            mode=_clean(data.get("mode"), "preview").lower(),
            intent_endpoint=_clean(data.get("intent_endpoint")),
            create_endpoint=_clean(data.get("create_endpoint")),
            capture_endpoint=_clean(data.get("capture_endpoint")),
            webhook_endpoint=_clean(data.get("webhook_endpoint")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaymentIntentRequest:
    campaign_slug: str
    amount: int
    currency: str = "USD"
    donor_name: str = ""
    donor_email: str = ""
    donor_message: str = ""
    team_id: str = ""
    cover_fees: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PaymentIntentRequest:
        data = data or {}
        return cls(
            campaign_slug=_clean(data.get("campaign_slug"), "campaign"),
            amount=_int(data.get("amount"), 0),
            currency=_clean(data.get("currency"), "USD").upper(),
            donor_name=_clean(data.get("donor_name")),
            donor_email=_clean(data.get("donor_email")),
            donor_message=_clean(data.get("donor_message")),
            team_id=_clean(data.get("team_id")),
            cover_fees=_bool(data.get("cover_fees"), False),
            metadata=dict(data.get("metadata") or {}),
        )

    @property
    def is_valid(self) -> bool:
        return bool(self.campaign_slug and self.amount > 0 and self.currency)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaymentSummary:
    amount: int
    currency: str = "USD"
    provider: str = ""
    status: str = "pending"
    checkout_kind: str = "donation"
    receipt_email: str = ""
    campaign_slug: str = ""
    supporter_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def formatted_amount(self) -> str:
        return f"${self.amount:,.0f}"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PaymentSummary:
        data = data or {}
        return cls(
            amount=_int(data.get("amount"), 0),
            currency=_clean(data.get("currency"), "USD").upper(),
            provider=_clean(data.get("provider")),
            status=_clean(data.get("status"), "pending").lower(),
            checkout_kind=_clean(data.get("checkout_kind"), "donation").lower(),
            receipt_email=_clean(data.get("receipt_email")),
            campaign_slug=_clean(data.get("campaign_slug")),
            supporter_name=_clean(data.get("supporter_name")),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["formatted_amount"] = self.formatted_amount
        return payload
