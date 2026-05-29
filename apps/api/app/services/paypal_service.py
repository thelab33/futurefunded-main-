from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import httpx

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


def _decimal_amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("PayPal amount must be a valid number.") from exc

    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount <= Decimal("0.00"):
        raise ValueError("PayPal amount must be greater than zero.")
    return amount


def _safe_provider_message(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                details = parsed.get("details")
                if isinstance(details, list) and details:
                    first = details[0]
                    if isinstance(first, dict):
                        issue = _clean(first.get("issue"))
                        description = _clean(first.get("description"))
                        if description:
                            return _truncate(description, 240)
                        if issue:
                            return _truncate(issue.replace("_", " ").capitalize(), 240)

                message = _clean(parsed.get("message"))
                if message:
                    return _truncate(message, 240)

                error_description = _clean(parsed.get("error_description"))
                if error_description:
                    return _truncate(error_description, 240)
        except Exception:
            pass

    return "PayPal could not process the request right now."


def _extract_error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                code = _clean(parsed.get("name") or parsed.get("error"))
                return code or None
        except Exception:
            pass
    return None


def _resource_id(payload: dict[str, Any]) -> str:
    resource = payload.get("resource")
    if isinstance(resource, dict):
        rid = _clean(resource.get("id"))
        if rid:
            return rid
    return ""


@dataclass(slots=True)
class PayPalService:
    client_id: str = ""
    client_secret: str = ""
    webhook_id: str = ""
    environment: str = "sandbox"
    default_currency: str = "USD"
    timeout_seconds: float = 20.0

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def normalized_environment(self) -> str:
        env = _clean(self.environment, "sandbox").lower()
        if env in {"live", "production", "prod"}:
            return "live"
        return "sandbox"

    @property
    def base_url(self) -> str:
        if self.normalized_environment == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    def public_config(self) -> dict[str, Any]:
        return {
            "provider": "paypal",
            "enabled": self.enabled,
            "client_id": self.client_id or None,
            "environment": self.normalized_environment,
            "currency": _normalize_currency(self.default_currency),
        }

    def build_order_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        amount_major = _decimal_amount(payload.get("amount"))
        currency = _normalize_currency(
            payload.get("currency"), _normalize_currency(self.default_currency)
        )
        campaign_slug = _truncate(_clean(payload.get("campaign_slug"), "campaign"), 120)

        checkout_kind = _clean(payload.get("checkout_kind"), "donation").lower()
        if checkout_kind not in _ALLOWED_CHECKOUT_KINDS:
            checkout_kind = "donation"

        donor_name = _truncate(_clean(payload.get("donor_name")), 120)
        donor_email = _truncate(_clean(payload.get("donor_email")), 254)
        donor_message = _truncate(_clean(payload.get("donor_message")), 255)
        team_id = _truncate(_clean(payload.get("team_id")), 120)

        description = _truncate(f"FutureFunded support for {campaign_slug or 'campaign'}", 127)

        custom_fields = [
            f"campaign:{campaign_slug or 'campaign'}",
            f"kind:{checkout_kind}",
        ]
        if team_id:
            custom_fields.append(f"team:{team_id}")
        if donor_email:
            custom_fields.append(f"email:{donor_email}")
        custom_id = _truncate("|".join(custom_fields), 255)

        purchase_unit: dict[str, Any] = {
            "reference_id": _truncate(campaign_slug or "campaign", 256),
            "description": description,
            "custom_id": custom_id,
            "soft_descriptor": _truncate("FUTUREFUNDED", 22),
            "amount": {
                "currency_code": currency,
                "value": f"{amount_major:.2f}",
            },
        }

        note_parts: list[str] = []
        if donor_name:
            note_parts.append(f"Donor: {donor_name}")
        if donor_email:
            note_parts.append(f"Email: {donor_email}")
        if donor_message:
            note_parts.append(f"Message: {donor_message}")
        if note_parts:
            purchase_unit["note_to_payee"] = _truncate(" | ".join(note_parts), 255)

        return {
            "intent": "CAPTURE",
            "purchase_units": [purchase_unit],
            "application_context": {
                "shipping_preference": "NO_SHIPPING",
                "user_action": "PAY_NOW",
            },
        }

    def _basic_auth(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode()
        return base64.b64encode(raw).decode("ascii")

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        request_headers = {
            "User-Agent": "FutureFunded/1.0",
        }
        if headers:
            request_headers.update(headers)

        timeout = httpx.Timeout(self.timeout_seconds)
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                json=json_body,
            )
            response.raise_for_status()

            if not response.text:
                return {}

            parsed = response.json()
            return parsed if isinstance(parsed, dict) else {}

    def get_access_token(self) -> str:
        if not self.enabled:
            raise ValueError("PayPal is not configured yet.")

        response = self._request(
            "POST",
            "/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {self._basic_auth()}",
                "Accept": "application/json",
                "Accept-Language": "en_US",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )

        token = _clean(response.get("access_token"))
        if not token:
            raise ValueError("PayPal access token could not be obtained.")

        return token

    def create_order_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            order_payload = self.build_order_payload(payload)
        except ValueError as exc:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "invalid_request",
                "message": str(exc),
                "order_payload": {},
            }

        if not self.enabled:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "not_configured",
                "message": "PayPal is not configured yet.",
                "order_payload": order_payload,
            }

        try:
            access_token = self.get_access_token()
            order = self._request(
                "POST",
                "/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Prefer": "return=representation",
                },
                json_body=order_payload,
            )

            return {
                "ok": True,
                "provider": "paypal",
                "status": _clean(order.get("status"), "created").lower(),
                "message": None,
                "order_id": _clean(order.get("id")) or None,
                "order_payload": order_payload,
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "provider_error",
                "message": _safe_provider_message(exc),
                "error_code": _extract_error_code(exc),
                "order_payload": order_payload,
            }

    def capture_order_response(self, order_id: str) -> dict[str, Any]:
        safe_order_id = _clean(order_id)
        if not safe_order_id:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "invalid_request",
                "message": "PayPal order_id is required for capture.",
                "order_id": None,
                "capture_id": None,
            }

        if not self.enabled:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "not_configured",
                "message": "PayPal is not configured yet.",
                "order_id": safe_order_id,
                "capture_id": None,
            }

        try:
            access_token = self.get_access_token()
            capture = self._request(
                "POST",
                f"/v2/checkout/orders/{safe_order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Prefer": "return=representation",
                },
                json_body={},
            )

            capture_id = None
            purchase_units = capture.get("purchase_units") or []
            if purchase_units and isinstance(purchase_units, list):
                payments = (purchase_units[0] or {}).get("payments") or {}
                captures = payments.get("captures") or []
                if captures and isinstance(captures, list):
                    capture_id = _clean((captures[0] or {}).get("id")) or None

            return {
                "ok": True,
                "provider": "paypal",
                "status": _clean(capture.get("status"), "completed").lower(),
                "message": None,
                "order_id": safe_order_id,
                "capture_id": capture_id,
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "paypal",
                "status": "provider_error",
                "message": _safe_provider_message(exc),
                "error_code": _extract_error_code(exc),
                "order_id": safe_order_id,
                "capture_id": None,
            }

    def normalize_webhook_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        transmission_id: str | None = None,
        raw_body: bytes | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_payload = payload if isinstance(payload, dict) else {}
        safe_headers = {str(k).lower(): str(v) for k, v in (headers or {}).items()}

        normalized_type = _clean(event_type) or _clean(safe_payload.get("event_type"), "unknown")
        resource_id = _resource_id(safe_payload)

        base = {
            "provider": "paypal",
            "event_type": normalized_type,
            "event_id": _clean(safe_payload.get("id")),
            "resource_id": resource_id,
            "transmission_present": bool(transmission_id),
            "webhook_id_present": bool(self.webhook_id),
            "verified": False,
            "verification_status": "skipped",
            "payload": safe_payload,
        }

        transmission_time = _clean(safe_headers.get("paypal-transmission-time"))
        transmission_sig = _clean(safe_headers.get("paypal-transmission-sig"))
        cert_url = _clean(safe_headers.get("paypal-cert-url"))
        auth_algo = _clean(safe_headers.get("paypal-auth-algo"))

        can_verify = bool(
            self.enabled
            and self.webhook_id
            and transmission_id
            and transmission_time
            and transmission_sig
            and cert_url
            and auth_algo
            and raw_body
        )

        if not can_verify:
            if not self.enabled:
                base["verification_status"] = "not_configured"
            elif not self.webhook_id:
                base["verification_status"] = "webhook_id_missing"
            elif transmission_id and raw_body:
                base["verification_status"] = "headers_missing"
            else:
                base["verification_status"] = "skipped"
            return base

        try:
            access_token = self.get_access_token()
            verify_payload = {
                "transmission_id": transmission_id,
                "transmission_time": transmission_time,
                "cert_url": cert_url,
                "auth_algo": auth_algo,
                "transmission_sig": transmission_sig,
                "webhook_id": self.webhook_id,
                "webhook_event": safe_payload,
            }

            verification = self._request(
                "POST",
                "/v1/notifications/verify-webhook-signature",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json_body=verify_payload,
            )

            status_value = _clean(verification.get("verification_status")).upper()
            if status_value == "SUCCESS":
                base["verified"] = True
                base["verification_status"] = "verified"
            else:
                base["verification_status"] = "failed"

            return base
        except Exception:
            base["verification_status"] = "failed"
            return base
