from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

try:
    import stripe as stripe_sdk  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    stripe_sdk = None


_ZERO_DECIMAL_CURRENCIES = {
    "BIF",
    "CLP",
    "DJF",
    "GNF",
    "JPY",
    "KMF",
    "KRW",
    "MGA",
    "PYG",
    "RWF",
    "UGX",
    "VND",
    "VUV",
    "XAF",
    "XOF",
    "XPF",
}

_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor", "membership"}
_CURRENCY_FALLBACK = "USD"


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: str, limit: int) -> str:
    return value[:limit].strip()


def _normalize_currency(value: Any, default: str = _CURRENCY_FALLBACK) -> str:
    currency = _clean(value, default).upper()
    if len(currency) != 3 or not currency.isalpha():
        return default
    return currency


def _parse_amount_major(value: Any, currency: str) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (AttributeError, InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Stripe amount must be a valid number.") from exc

    quantizer = Decimal("1") if currency in _ZERO_DECIMAL_CURRENCIES else Decimal("0.01")
    normalized = amount.quantize(quantizer, rounding=ROUND_HALF_UP)

    if normalized <= 0:
        raise ValueError("Stripe amount must be greater than zero.")

    return normalized


def _amount_to_minor_units(amount_major: Decimal, currency: str) -> int:
    if currency in _ZERO_DECIMAL_CURRENCIES:
        return max(0, int(amount_major))

    return max(0, int((amount_major * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)))


def _display_amount_major(amount_major: Decimal, currency: str) -> str:
    if currency in _ZERO_DECIMAL_CURRENCIES:
        return str(int(amount_major))
    return format(amount_major.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _safe_provider_message(exc: Exception) -> str:
    # Do not leak raw provider internals to clients.
    user_message = _clean(getattr(exc, "user_message", None))
    if user_message:
        return _truncate(user_message, 240)
    return "Stripe could not create a payment intent right now."


def _extract_error_code(exc: Exception) -> str | None:
    code = _clean(getattr(exc, "code", None))
    return code or None


def _safe_metadata(payload: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in payload.items() if value}


def _extract_event_object(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    obj = data.get("object")
    return obj if isinstance(obj, dict) else {}


@dataclass(slots=True)
class StripeService:
    publishable_key: str = ""
    secret_key: str = ""
    webhook_secret: str = ""
    default_currency: str = "USD"

    @property
    def sdk_available(self) -> bool:
        return stripe_sdk is not None

    @property
    def enabled(self) -> bool:
        return bool(self.publishable_key and self.secret_key and self.sdk_available)

    def public_config(self) -> dict[str, Any]:
        currency = _normalize_currency(self.default_currency)
        return {
            "provider": "stripe",
            "enabled": self.enabled,
            "sdk_available": self.sdk_available,
            "publishable_key": self.publishable_key or None,
            "currency": currency,
        }

    def build_intent_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        currency = _normalize_currency(
            payload.get("currency"), _normalize_currency(self.default_currency)
        )
        amount_major = _parse_amount_major(payload.get("amount"), currency)
        amount_minor = _amount_to_minor_units(amount_major, currency)

        if amount_minor <= 0:
            raise ValueError("Stripe amount must resolve to a positive charge amount.")

        campaign_slug = _truncate(_clean(payload.get("campaign_slug"), "campaign"), 120)
        donor_email = _truncate(_clean(payload.get("donor_email")), 254)
        donor_name = _truncate(_clean(payload.get("donor_name")), 120)
        donor_message = _truncate(_clean(payload.get("donor_message")), 500)
        team_id = _truncate(_clean(payload.get("team_id")), 120)

        checkout_kind = _clean(payload.get("checkout_kind"), "donation").lower()
        if checkout_kind not in _ALLOWED_CHECKOUT_KINDS:
            checkout_kind = "donation"

        metadata = _safe_metadata(
            {
                "campaign_slug": _truncate(campaign_slug, 500),
                "checkout_kind": _truncate(checkout_kind, 100),
                "donor_email": _truncate(donor_email, 500),
                "donor_name": _truncate(donor_name, 500),
                "team_id": _truncate(team_id, 500),
                "donor_message": _truncate(donor_message, 500),
                "display_amount_major": _display_amount_major(amount_major, currency),
                "display_currency": currency,
            }
        )

        description_slug = campaign_slug or "campaign"

        return {
            "amount": amount_minor,
            "currency": currency.lower(),
            "automatic_payment_methods": {"enabled": True},
            "metadata": metadata,
            "receipt_email": donor_email or None,
            "description": _truncate(f"FutureFunded support for {description_slug}", 500),
        }

    def create_intent_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            intent_payload = self.build_intent_payload(payload)
        except ValueError as exc:
            return {
                "ok": False,
                "provider": "stripe",
                "status": "invalid_request",
                "message": str(exc),
                "intent_payload": {},
            }

        if not self.publishable_key or not self.secret_key:
            return {
                "ok": False,
                "provider": "stripe",
                "status": "not_configured",
                "message": "Stripe is not configured yet.",
                "intent_payload": intent_payload,
            }

        if not self.sdk_available:
            return {
                "ok": False,
                "provider": "stripe",
                "status": "sdk_missing",
                "message": "Stripe SDK is not installed yet.",
                "intent_payload": intent_payload,
            }

        try:
            stripe_sdk.api_key = self.secret_key
            intent = stripe_sdk.PaymentIntent.create(**intent_payload)

            return {
                "ok": True,
                "provider": "stripe",
                "status": getattr(intent, "status", "requires_payment_method"),
                "intent_id": getattr(intent, "id", None),
                "client_secret": getattr(intent, "client_secret", None),
                "intent_payload": intent_payload,
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "stripe",
                "status": "provider_error",
                "message": _safe_provider_message(exc),
                "error_code": _extract_error_code(exc),
                "intent_payload": intent_payload,
            }

    def normalize_webhook_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: str | None = None,
        raw_body: bytes | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_payload = payload if isinstance(payload, dict) else {}
        normalized_type = _clean(event_type) or _clean(safe_payload.get("type"), "unknown")
        object_payload = _extract_event_object(safe_payload)

        base = {
            "provider": "stripe",
            "event_type": normalized_type,
            "event_id": _clean(safe_payload.get("id")),
            "signature_present": bool(signature),
            "webhook_secret_present": bool(self.webhook_secret),
            "verified": False,
            "verification_status": "skipped",
            "livemode": bool(safe_payload.get("livemode")),
            "object_id": _clean(object_payload.get("id")),
            "payload": safe_payload,
        }

        can_verify = bool(self.sdk_available and self.webhook_secret and signature and raw_body)

        if not can_verify:
            if signature and self.webhook_secret and not self.sdk_available:
                base["verification_status"] = "sdk_missing"
            elif signature and not self.webhook_secret:
                base["verification_status"] = "secret_missing"
            elif signature and self.webhook_secret and not raw_body:
                base["verification_status"] = "raw_body_missing"
            else:
                base["verification_status"] = "skipped"
            return base

        try:
            verified_event = stripe_sdk.Webhook.construct_event(
                payload=raw_body,
                sig_header=signature,
                secret=self.webhook_secret,
            )

            verified_payload = dict(verified_event)
            verified_object = _extract_event_object(verified_payload)

            return {
                "provider": "stripe",
                "event_type": _clean(verified_payload.get("type"), normalized_type),
                "event_id": _clean(verified_payload.get("id")),
                "signature_present": True,
                "webhook_secret_present": True,
                "verified": True,
                "verification_status": "verified",
                "livemode": bool(verified_payload.get("livemode")),
                "object_id": _clean(verified_object.get("id")),
                "payload": verified_payload,
            }
        except Exception:
            base["verification_status"] = "failed"
            return base
