from __future__ import annotations

import inspect
import json
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.schemas.payments import (
    PaymentConfigOut,
    PaymentProviderPublicConfig,
    PayPalCaptureIn,
    PayPalCaptureOut,
    PayPalOrderIn,
    PayPalOrderOut,
    StripeIntentIn,
    StripeIntentOut,
    WebhookEventOut,
)
from app.services.paypal_service import PayPalService
from app.services.stripe_service import StripeService

router = APIRouter()

_MAX_WEBHOOK_BYTES = 256 * 1024


def _stripe_service() -> StripeService:
    return StripeService(
        publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip(),
        secret_key=os.getenv("STRIPE_SECRET_KEY", "").strip(),
        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "").strip(),
        default_currency=os.getenv("STRIPE_CURRENCY", "USD").strip().upper(),
    )


def _paypal_service() -> PayPalService:
    return PayPalService(
        client_id=os.getenv("PAYPAL_CLIENT_ID", "").strip(),
        client_secret=os.getenv("PAYPAL_CLIENT_SECRET", "").strip(),
        webhook_id=os.getenv("PAYPAL_WEBHOOK_ID", "").strip(),
        environment=os.getenv("PAYPAL_ENV", "sandbox").strip().lower(),
        default_currency=os.getenv("PAYPAL_CURRENCY", "USD").strip().upper(),
    )


def _set_response_headers(
    response: Response,
    *,
    cache_control: str,
    request_id: str | None = None,
    robots: str = "noindex, nofollow",
) -> None:
    response.headers.setdefault("Cache-Control", cache_control)
    response.headers.setdefault("X-Robots-Tag", robots)
    if request_id:
        response.headers.setdefault("X-Request-Id", request_id)


async def _read_limited_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _MAX_WEBHOOK_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Webhook payload too large.",
                )
        except ValueError:
            pass

    raw = await request.body()
    if len(raw) > _MAX_WEBHOOK_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload too large.",
        )
    return raw


def _safe_json_from_bytes(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}

    try:
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _call_normalizer(method: Any, **kwargs: Any) -> dict[str, Any]:
    parameters = inspect.signature(method).parameters
    supported_kwargs = {key: value for key, value in kwargs.items() if key in parameters}
    normalized = method(**supported_kwargs)
    return normalized if isinstance(normalized, dict) else {}


def _payment_config_payload() -> dict[str, Any]:
    stripe = _stripe_service()
    paypal = _paypal_service()

    stripe_public = stripe.public_config()
    paypal_public = paypal.public_config()

    return {
        "ok": True,
        "providers": {
            "stripe": PaymentProviderPublicConfig(**stripe_public),
            "paypal": PaymentProviderPublicConfig(**paypal_public),
        },
    }


@router.get("/config", response_model=PaymentConfigOut)
async def payment_config(
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> PaymentConfigOut:
    _set_response_headers(
        response,
        cache_control="public, max-age=300, stale-while-revalidate=600",
        request_id=x_request_id,
    )
    return PaymentConfigOut(**_payment_config_payload())


@router.post("/stripe/intent", response_model=StripeIntentOut)
async def create_stripe_intent(
    payload: StripeIntentIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> StripeIntentOut:
    _set_response_headers(response, cache_control="no-store, max-age=0", request_id=x_request_id)
    result = _stripe_service().create_intent_response(payload.model_dump())
    return StripeIntentOut(**result)


@router.post("/paypal/order", response_model=PayPalOrderOut)
async def create_paypal_order(
    payload: PayPalOrderIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> PayPalOrderOut:
    _set_response_headers(response, cache_control="no-store, max-age=0", request_id=x_request_id)
    result = _paypal_service().create_order_response(payload.model_dump())
    return PayPalOrderOut(**result)


@router.post("/paypal/capture", response_model=PayPalCaptureOut)
async def capture_paypal_order(
    payload: PayPalCaptureIn,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> PayPalCaptureOut:
    _set_response_headers(response, cache_control="no-store, max-age=0", request_id=x_request_id)
    result = _paypal_service().capture_order_response(payload.order_id)
    return PayPalCaptureOut(**result)


@router.post("/webhooks/stripe", response_model=WebhookEventOut)
async def stripe_webhook(
    request: Request,
    response: Response,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> WebhookEventOut:
    _set_response_headers(response, cache_control="no-store, max-age=0", request_id=x_request_id)

    raw = await _read_limited_body(request)
    body = _safe_json_from_bytes(raw)
    event_type = str(body.get("type") or "unknown")

    service = _stripe_service()
    normalized = _call_normalizer(
        service.normalize_webhook_event,
        event_type=event_type,
        payload=body,
        signature=stripe_signature,
        raw_body=raw,
        headers=dict(request.headers),
    )

    return WebhookEventOut(
        ok=True,
        received=True,
        event=normalized,
    )


@router.post("/webhooks/paypal", response_model=WebhookEventOut)
async def paypal_webhook(
    request: Request,
    response: Response,
    paypal_transmission_id: str | None = Header(default=None, alias="paypal-transmission-id"),
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> WebhookEventOut:
    _set_response_headers(response, cache_control="no-store, max-age=0", request_id=x_request_id)

    raw = await _read_limited_body(request)
    body = _safe_json_from_bytes(raw)
    event_type = str(body.get("event_type") or "unknown")

    service = _paypal_service()
    normalized = _call_normalizer(
        service.normalize_webhook_event,
        event_type=event_type,
        payload=body,
        transmission_id=paypal_transmission_id,
        raw_body=raw,
        headers=dict(request.headers),
    )

    return WebhookEventOut(
        ok=True,
        received=True,
        event=normalized,
    )
