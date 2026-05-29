from __future__ import annotations

# FF_LIFECYCLE_IMPORTS_V1_START
try:
    from apps.web.app.services.ff_lifecycle_dispatch import (
        dispatch_donation_lifecycle as _ff_dispatch_donation_lifecycle,
        dispatch_sponsor_lifecycle as _ff_dispatch_sponsor_lifecycle,
    )
    from apps.web.app.services.ff_lifecycle_once import (
        dispatch_once as _ff_lifecycle_dispatch_once,
    )
except Exception:  # pragma: no cover - lifecycle messaging must never break boot
    _ff_dispatch_donation_lifecycle = None
    _ff_dispatch_sponsor_lifecycle = None
    _ff_lifecycle_dispatch_once = None
# FF_LIFECYCLE_IMPORTS_V1_END

from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import os
import stripe

import pathlib
import re
from typing import Any
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, g, jsonify, make_response, redirect, render_template, request, url_for

from .presenters import build_campaign_presenter
from .serializers import serialize_campaign_context
from apps.web.app.services.operator_notifications import record_operator_notification

campaign_bp = Blueprint("campaign", __name__)

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")
_ALLOWED_CHECKOUT_STATES = {"success", "cancelled"}
_ALLOWED_CHECKOUT_KINDS = {"donation", "sponsor"}


def _request_id() -> str | None:
    return getattr(g, "request_id", None)


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _normalize_slug_or_404(slug: str) -> str:
    normalized = _clean(slug).lower()
    if not normalized or len(normalized) > 120 or not _SLUG_RE.fullmatch(normalized):
        abort(404)
    return normalized


def _query_args_for_redirect() -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in request.args.keys():
        values = request.args.getlist(key)
        if not values:
            continue
        payload[key] = values if len(values) > 1 else values[0]
    return payload


def _maybe_redirect_to_canonical_slug(slug: str):
    normalized = _normalize_slug_or_404(slug)
    if slug == normalized:
        return None

    route_args = dict(request.view_args or {})
    route_args["slug"] = normalized
    route_args.update(_query_args_for_redirect())
    return redirect(url_for(request.endpoint, **route_args), code=301)


def _public_base_url() -> str:
    configured = _clean(current_app.config.get("PUBLIC_BASE_URL")).rstrip("/")
    if configured:
        return configured

    if request.url_root:
        return request.url_root.rstrip("/")

    return ""


def _campaign_path(slug: str) -> str:
    return url_for("campaign.campaign_page", slug=slug)


def _campaign_url(slug: str, *, external: bool = False) -> str:
    path = _campaign_path(slug)
    if not external:
        return path

    base = _public_base_url()
    if base:
        return f"{base}{path}"

    return url_for("campaign.campaign_page", slug=slug, _external=True)


def _redirect_with_checkout_state(slug: str, state: str, kind: str) -> str:
    path = _campaign_path(slug)
    query = urlencode({"checkout": state, "kind": kind})
    return f"{path}?{query}"


def _json_response(
    payload: dict[str, Any],
    *,
    status: int = 200,
    cache_control: str = "no-store, max-age=0",
    robots: str = "noindex, nofollow",
):
    response = jsonify(payload)
    response.status_code = status
    response.headers.setdefault("Cache-Control", cache_control)
    response.headers.setdefault("X-Robots-Tag", robots)
    request_id = _request_id()
    if request_id:
        response.headers.setdefault("X-Request-Id", request_id)
    return response


def _campaign_page_cache_control() -> str:
    checkout = _clean(request.args.get("checkout")).lower()
    kind = _clean(request.args.get("kind")).lower()

    if checkout or kind:
        return "no-store, max-age=0"

    return "public, max-age=60, stale-while-revalidate=300"


def _ff_campaign_media_urls(slug: str) -> list[str]:
    """Return uploaded campaign media URLs from the static upload manifest."""
    try:
        safe_slug = (
            "".join(ch for ch in str(slug or "") if ch.isalnum() or ch in "-_").strip("-_")
            or "campaign"
        )
        manifest = (
            pathlib._Path(current_app.root_path)
            / "static"
            / "uploads"
            / "campaigns"
            / safe_slug
            / "manifest.json"
        )
        if not manifest.exists():
            return []
        data = json.loads(manifest.read_text(encoding="utf-8"))
        urls = data.get("urls") if isinstance(data, dict) else []
        return [str(url) for url in urls if isinstance(url, str)][:6]
    except Exception:
        return []


@campaign_bp.get("/c/<slug>")
def campaign_page(slug: str):
    canonical_redirect = _maybe_redirect_to_canonical_slug(slug)
    if canonical_redirect is not None:
        return canonical_redirect

    normalized_slug = _normalize_slug_or_404(slug)
    presenter = build_campaign_presenter(current_app.config)
    context = presenter.page_context(normalized_slug)

    campaign_url = _campaign_url(normalized_slug, external=False)
    canonical_url = _campaign_url(normalized_slug, external=True)

    context.update(
        {
            "campaign_slug": normalized_slug,
            "campaign_url": campaign_url,
            "share_url": canonical_url,
            "canonical_url": canonical_url,
        }
    )

    payload = serialize_campaign_context(context)
    try:
        payload["payment_ledger"] = _ff_campaign_ledger_snapshot(slug)
    except Exception:
        current_app.logger.exception("FutureFunded ledger snapshot failed for campaign %s", slug)
        payload["payment_ledger"] = {
            "campaignSlug": slug,
            "totals": {
                "campaign_slug": slug,
                "raised_amount_cents": 0,
                "donation_count": 0,
                "sponsor_count": 0,
                "updated_at": None,
            },
            "recentDonations": [],
            "recentSponsors": [],
        }

    response = make_response(render_template("campaign_premium.html",
        checkout_url=os.getenv("FF_CONNECT_ATX_ELITE_CHECKOUT_URL") or os.getenv("FF_DEFAULT_CHECKOUT_URL") or "", **payload))
    response.headers.setdefault("Cache-Control", _campaign_page_cache_control())

    if _clean(request.args.get("checkout")) or _clean(request.args.get("kind")):
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")

    request_id = _request_id()
    if request_id:
        response.headers.setdefault("X-Request-Id", request_id)

    return response


@campaign_bp.get("/c/<slug>/thank-you")
def thank_you(slug: str):
    canonical_redirect = _maybe_redirect_to_canonical_slug(slug)
    if canonical_redirect is not None:
        return canonical_redirect

    normalized_slug = _normalize_slug_or_404(slug)
    kind = _clean(request.args.get("kind"), "donation").lower()
    if kind not in _ALLOWED_CHECKOUT_KINDS:
        kind = "donation"

    return _json_response(
        {
            "ok": True,
            "page": "thank-you",
            "slug": normalized_slug,
            "kind": kind,
            "message": "Support was completed successfully.",
            "campaign_url": _campaign_url(normalized_slug, external=False),
            "redirect_url": _redirect_with_checkout_state(normalized_slug, "success", kind),
            "request_id": _request_id(),
        }
    )


@campaign_bp.get("/c/<slug>/cancel")
def cancel(slug: str):
    canonical_redirect = _maybe_redirect_to_canonical_slug(slug)
    if canonical_redirect is not None:
        return canonical_redirect

    normalized_slug = _normalize_slug_or_404(slug)
    kind = _clean(request.args.get("kind"), "donation").lower()
    if kind not in _ALLOWED_CHECKOUT_KINDS:
        kind = "donation"

    return _json_response(
        {
            "ok": True,
            "page": "cancel",
            "slug": normalized_slug,
            "kind": kind,
            "message": "Checkout was cancelled before completion.",
            "campaign_url": _campaign_url(normalized_slug, external=False),
            "redirect_url": _redirect_with_checkout_state(normalized_slug, "cancelled", kind),
            "request_id": _request_id(),
        }
    )


@campaign_bp.get("/c/<slug>/share")
def share(slug: str):
    canonical_redirect = _maybe_redirect_to_canonical_slug(slug)
    if canonical_redirect is not None:
        return canonical_redirect

    normalized_slug = _normalize_slug_or_404(slug)
    presenter = build_campaign_presenter(current_app.config)
    context = presenter.page_context(normalized_slug)
    campaign = context.get("campaign") or {}

    org_name = _clean(context.get("org_name") or campaign.get("org_name"))
    campaign_name = _clean(context.get("campaign_name") or campaign.get("campaign_name"))
    fallback_title = normalized_slug.replace("-", " ").title()

    if org_name and campaign_name and campaign_name.lower() != org_name.lower():
        title = f"Support {org_name} • {campaign_name}"
    elif org_name:
        title = f"Support {org_name}"
    else:
        title = f"Support {fallback_title}"

    return _json_response(
        {
            "ok": True,
            "page": "share",
            "slug": normalized_slug,
            "share_url": _campaign_url(normalized_slug, external=True),
            "campaign_url": _campaign_url(normalized_slug, external=False),
            "canonical_url": _campaign_url(normalized_slug, external=True),
            "title": title,
            "request_path": request.path,
            "request_id": _request_id(),
        }
    )


# ---------------------------------------------------------------------------
# FutureFunded flagship payment endpoints
# Stripe Checkout + PayPal Orders scaffold for campaign/sponsor monetization.
# ---------------------------------------------------------------------------

import base64
import json
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def _ff_money_to_cents(value, *, minimum=1, maximum=50000):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid amount")

    if amount < Decimal(str(minimum)):
        raise ValueError(f"Amount must be at least ${minimum}")

    if amount > Decimal(str(maximum)):
        raise ValueError(f"Amount cannot exceed ${maximum:,}")

    return int(amount * 100)


def _ff_money_to_paypal_value(value):
    cents = _ff_money_to_cents(value)
    return f"{Decimal(cents) / Decimal(100):.2f}"


def _ff_public_base_url():
    configured = os.getenv("FF_PUBLIC_BASE_URL", "").rstrip("/")
    if configured:
        return configured
    return request.host_url.rstrip("/")


def _ff_campaign_success_url(slug):
    return f"{_ff_public_base_url()}/c/{slug}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"


def _ff_campaign_cancel_url(slug):
    return f"{_ff_public_base_url()}/c/{slug}?payment=cancelled"


def _ff_checkout_payload():
    """Normalize checkout payload from JSON or native form posts."""
    payload = {}

    if request.is_json:
        payload = request.get_json(silent=True) or {}

    if not payload and request.form:
        payload = request.form.to_dict(flat=True)

    amount_raw = (
        payload.get("amount")
        or payload.get("amount_dollars")
        or payload.get("donation_amount")
        or payload.get("value")
        or ""
    )

    try:
        cents = _ff_money_to_cents(amount_raw, minimum=1, maximum=50000)
    except ValueError:
        raise ValueError("Invalid amount") from None

    email = str(payload.get("email") or payload.get("donor_email") or "").strip()
    name = str(payload.get("name") or payload.get("donor_name") or "").strip()
    flow = str(payload.get("flow") or "donation").strip() or "donation"
    sponsor_tier = str(
        payload.get("sponsor_tier") or payload.get("tier") or payload.get("package") or ""
    ).strip()

    raw_label = (
        payload.get("label")
        or payload.get("checkout_label")
        or payload.get("product_label")
        or payload.get("description")
        or ""
    )

    label = str(raw_label).strip()

    if not label:
        label = "FutureFunded campaign donation"

    return {
        **payload,
        "label": label,
        "description": label,
        "flow": flow,
        "sponsor_tier": sponsor_tier,
        "amount_cents": cents,
        "amount": cents / 100,
        "email": email,
        "donor_email": email,
        "name": name,
        "donor_name": name,
    }


@campaign_bp.get("/c/<slug>/payments/config")
def ff_campaign_payment_config(slug):
    """Return public payment runtime config for the flagship campaign page."""
    stripe_pk = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_env = os.getenv("PAYPAL_ENV", "sandbox").lower()

    paypal_host = "www.paypal.com" if paypal_env == "live" else "www.sandbox.paypal.com"

    return jsonify(
        {
            "campaignSlug": slug,
            "currency": "usd",
            "stripe": {
                "enabled": bool(stripe_pk),
                "publishableKey": stripe_pk,
            },
            "paypal": {
                "enabled": bool(paypal_client_id),
                "clientId": paypal_client_id,
                "env": paypal_env,
                "sdkUrl": f"https://{paypal_host}/sdk/js?client-id={paypal_client_id}&currency=USD&components=buttons",
            },
            "endpoints": {
                "stripeCheckout": f"/c/{slug}/checkout/session",
                "paypalCreateOrder": f"/c/{slug}/paypal/orders",
                "paypalCaptureOrder": f"/c/{slug}/paypal/orders/{{order_id}}/capture",
            },
        }
    )





# FF_WAVE10B_SPONSOR_METADATA_REVIEW_QUEUE_START
def _ff_wave10b_str(value, *, limit=260):
    try:
        value = "" if value is None else str(value)
    except Exception:
        value = ""
    value = " ".join(value.strip().split())
    return value[:limit]


def _ff_wave10b_dict(value):
    if isinstance(value, dict):
        return value
    try:
        if hasattr(value, "to_dict_recursive"):
            return value.to_dict_recursive()
    except Exception:
        pass
    try:
        return dict(value or {})
    except Exception:
        return {}


def _ff_wave10b_sponsor_intake_from_payload(payload):
    """Normalize sponsor intake from checkout JSON/form payload.

    Accepts both:
    - sponsor_intake: { business_name, email, ... }
    - top-level sponsor_* / business_name fields
    """
    payload = _ff_wave10b_dict(payload)
    nested = _ff_wave10b_dict(payload.get("sponsor_intake"))

    def pick(*keys):
        for key in keys:
            if key in nested and _ff_wave10b_str(nested.get(key)):
                return _ff_wave10b_str(nested.get(key))
            if key in payload and _ff_wave10b_str(payload.get(key)):
                return _ff_wave10b_str(payload.get(key))
        return ""

    amount = pick("package_amount", "sponsor_amount", "amount", "data_amount")
    amount_cents = pick("package_amount_cents", "sponsor_amount_cents", "amount_cents", "data_amount_cents")

    # Normalize amount cents when only dollars are present.
    if not amount_cents and amount:
        try:
            amount_cents = str(int(round(float(str(amount).replace(",", "")) * 100)))
        except Exception:
            amount_cents = ""

    intake = {
        "sponsor_business_name": pick("business_name", "sponsor_business_name", "organization", "company"),
        "sponsor_contact_email": pick("email", "contact_email", "sponsor_email", "customer_email"),
        "sponsor_recognition_name": pick("recognition_name", "sponsor_recognition_name", "public_name"),
        "sponsor_website": pick("website", "url", "sponsor_website"),
        "sponsor_package": pick("package", "sponsor_package", "tier", "sponsor_tier"),
        "sponsor_package_label": pick("package_label", "sponsor_package_label", "label", "sponsor_label"),
        "sponsor_package_amount": amount,
        "sponsor_package_amount_cents": amount_cents,
        "sponsor_recognition_note": pick("recognition_note", "note", "message", "sponsor_note"),
    }

    return {k: v for k, v in intake.items() if v}


def _ff_wave10b_session_id(session):
    data = _ff_wave10b_dict(session)
    return _ff_wave10b_str(data.get("id") or getattr(session, "id", ""))


def _ff_wave10b_session_url(session):
    data = _ff_wave10b_dict(session)
    return _ff_wave10b_str(data.get("url") or getattr(session, "url", ""), limit=600)


def _ff_wave10b_session_metadata(session):
    data = _ff_wave10b_dict(session)
    return _ff_wave10b_dict(data.get("metadata"))


def _ff_wave10b_write_sponsor_review_queue(slug, session, payload=None, *, status="checkout_created"):
    """Create/update a local review-queue JSON artifact for sponsor recognition.

    This is intentionally file-backed for MVP/demo durability. It does not block checkout.
    """
    try:
        from pathlib import Path as _Path
        import json as _json
        from datetime import datetime as _datetime
        from flask import current_app as _current_app

        session_data = _ff_wave10b_dict(session)
        metadata = _ff_wave10b_session_metadata(session)
        intake = _ff_wave10b_sponsor_intake_from_payload(payload or {})
        merged = {**intake, **{k: _ff_wave10b_str(v) for k, v in metadata.items() if str(k).startswith("sponsor_")}}

        if not merged:
            return {"recorded": False, "reason": "no_sponsor_metadata"}

        session_id = _ff_wave10b_session_id(session) or _ff_wave10b_str(merged.get("stripe_session_id")) or "unknown-session"
        queue_dir = _Path(_current_app.instance_path) / "sponsor-review-queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "status": status,
            "campaign_slug": _ff_wave10b_str(slug),
            "session_id": session_id,
            "checkout_url": _ff_wave10b_session_url(session),
            "created_at": _datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "sponsor": {
                "business_name": merged.get("sponsor_business_name", ""),
                "contact_email": merged.get("sponsor_contact_email", ""),
                "recognition_name": merged.get("sponsor_recognition_name", ""),
                "website": merged.get("sponsor_website", ""),
                "package": merged.get("sponsor_package", ""),
                "package_label": merged.get("sponsor_package_label", ""),
                "package_amount": merged.get("sponsor_package_amount", ""),
                "package_amount_cents": merged.get("sponsor_package_amount_cents", ""),
                "recognition_note": merged.get("sponsor_recognition_note", ""),
            },
            "review": {
                "public_recognition_allowed": False,
                "review_required": True,
                "review_state": "pending_payment_or_review",
            },
        }

        path = queue_dir / f"{session_id}.json"
        path.write_text(_json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return {"recorded": True, "path": str(path), "session_id": session_id}
    except Exception:
        try:
            current_app.logger.exception("FutureFunded sponsor review queue write failed")
        except Exception:
            pass
        return {"recorded": False, "reason": "write_failed"}
# FF_WAVE10B_SPONSOR_METADATA_REVIEW_QUEUE_END

# FF_LIFECYCLE_HELPERS_V1_START
def _ff_lifecycle_get(obj, *keys, default=None):
    """Read safely from Stripe objects, dicts, nested dicts, and simple attrs."""
    for key in keys:
        if obj is None:
            continue

        value = None

        try:
            if isinstance(obj, dict):
                value = obj.get(key)
            else:
                value = getattr(obj, key, None)
        except Exception:
            value = None

        if value not in (None, ""):
            return value

    return default


def _ff_lifecycle_dict(obj):
    """Convert Stripe objects to plain-ish dictionaries when possible."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    try:
        if hasattr(obj, "to_dict_recursive"):
            return obj.to_dict_recursive()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
    except Exception:
        pass
    try:
        return dict(obj)
    except Exception:
        return {}


def _ff_lifecycle_slug(slug=None, session=None):
    """Infer campaign slug from route, metadata, or client_reference_id."""
    if slug:
        return str(slug).strip("/") or "connect-atx-elite"

    session_data = _ff_lifecycle_dict(session)
    metadata = _ff_lifecycle_dict(_ff_lifecycle_get(session_data, "metadata", default={}))
    meta_slug = (
        metadata.get("campaign_slug")
        or metadata.get("slug")
        or metadata.get("campaign")
    )
    if meta_slug:
        return str(meta_slug).strip("/") or "connect-atx-elite"

    ref = str(_ff_lifecycle_get(session_data, "client_reference_id", default="") or "")
    if ref and ":" in ref:
        return ref.split(":", 1)[0].strip("/") or "connect-atx-elite"

    return "connect-atx-elite"


def _ff_lifecycle_public_base_url():
    return (
        current_app.config.get("FF_PUBLIC_BASE_URL")
        or current_app.config.get("PUBLIC_BASE_URL")
        or os.getenv("FF_PUBLIC_BASE_URL")
        or os.getenv("PUBLIC_BASE_URL")
        or "https://getfuturefunded.com"
    )


def _ff_lifecycle_operator_email():
    return (
        current_app.config.get("FF_OPERATOR_EMAIL")
        or current_app.config.get("OPERATOR_EMAIL")
        or os.getenv("FF_OPERATOR_EMAIL")
        or os.getenv("OPERATOR_EMAIL")
        or os.getenv("FF_EMAIL_REPLY_TO")
        or "arodgps@gmail.com"
    )


def _ff_lifecycle_payload_from_session(slug=None, session=None, source="stripe"):
    """Build a lifecycle payload from a Stripe Checkout Session."""
    session_data = _ff_lifecycle_dict(session)
    metadata = _ff_lifecycle_dict(_ff_lifecycle_get(session_data, "metadata", default={}))
    customer_details = _ff_lifecycle_dict(_ff_lifecycle_get(session_data, "customer_details", default={}))

    campaign_slug = _ff_lifecycle_slug(slug, session_data)

    session_id = str(_ff_lifecycle_get(session_data, "id", default="") or "")
    payment_intent = str(_ff_lifecycle_get(session_data, "payment_intent", default="") or "")
    amount_cents = (
        _ff_lifecycle_get(session_data, "amount_total", default=None)
        or _ff_lifecycle_get(session_data, "amount_subtotal", default=None)
        or metadata.get("amount_cents")
        or metadata.get("total_cents")
        or 0
    )

    email = (
        customer_details.get("email")
        or _ff_lifecycle_get(session_data, "customer_email", default="")
        or metadata.get("donor_email")
        or metadata.get("supporter_email")
        or metadata.get("sponsor_email")
        or metadata.get("email")
        or ""
    )

    name = (
        customer_details.get("name")
        or metadata.get("donor_name")
        or metadata.get("supporter_name")
        or metadata.get("sponsor_name")
        or metadata.get("business_name")
        or ""
    )

    flow = str(metadata.get("flow") or metadata.get("kind") or "").strip().lower()
    sponsor_tier = str(metadata.get("sponsor_tier") or metadata.get("tier") or "").strip()

    if not flow:
        flow = "sponsor" if sponsor_tier and sponsor_tier.lower() not in {"none", "donation"} else "donation"

    payload = {
        "source": source,
        "public_base_url": _ff_lifecycle_public_base_url(),
        "campaign_slug": campaign_slug,
        "campaign_url": f"{_ff_lifecycle_public_base_url().rstrip('/')}/c/{campaign_slug}",
        "campaign_name": metadata.get("campaign_name") or "Spring Fundraiser",
        "team_name": metadata.get("team_name") or metadata.get("organization_name") or "Connect ATX Elite",
        "checkout_session_id": session_id,
        "session_id": session_id,
        "payment_intent": payment_intent,
        "flow": flow,
        "amount_cents": amount_cents,
        "supporter_name": name or "Friend",
        "donor_name": name or "Friend",
        "supporter_email": email,
        "donor_email": email,
        "email": email,
        "sponsor_name": metadata.get("sponsor_name") or metadata.get("business_name") or name or "Sponsor",
        "business_name": metadata.get("business_name") or metadata.get("sponsor_name") or name or "Sponsor",
        "sponsor_email": metadata.get("sponsor_email") or email,
        "sponsor_tier": sponsor_tier or "Community Partner",
        "operator_email": _ff_lifecycle_operator_email(),
        "reply_to": os.getenv("FF_EMAIL_REPLY_TO") or _ff_lifecycle_operator_email(),
    }

    return payload


def _ff_dispatch_checkout_lifecycle(slug=None, session=None, source="stripe"):
    """Dispatch donor/sponsor lifecycle safely after confirmed payment."""
    if not _ff_lifecycle_dispatch_once:
        return {
            "sent": False,
            "mode": "unavailable",
            "reason": "lifecycle_dispatcher_not_imported",
        }

    payload = _ff_lifecycle_payload_from_session(slug=slug, session=session, source=source)
    flow = str(payload.get("flow") or "donation").lower()
    external_id = (
        payload.get("checkout_session_id")
        or payload.get("session_id")
        or payload.get("payment_intent")
    )

    is_sponsor = flow == "sponsor" or (
        payload.get("sponsor_tier")
        and str(payload.get("sponsor_tier")).lower() not in {"none", "donation"}
    )

    dispatcher = _ff_dispatch_sponsor_lifecycle if is_sponsor else _ff_dispatch_donation_lifecycle
    kind = "sponsor" if is_sponsor else "donation"

    if not dispatcher:
        return {
            "sent": False,
            "mode": "unavailable",
            "reason": f"{kind}_dispatcher_not_imported",
        }

    result = _ff_lifecycle_dispatch_once(
        kind=kind,
        external_id=str(external_id or ""),
        payload=payload,
        dispatcher=dispatcher,
    )

    try:
        current_app.logger.info(
            "FutureFunded lifecycle dispatch | kind=%s source=%s mode=%s key=%s",
            kind,
            source,
            result.get("mode"),
            result.get("key"),
        )
    except Exception:
        pass

    return result
# FF_LIFECYCLE_HELPERS_V1_END


@campaign_bp.post("/c/<slug>/checkout/session")
def ff_create_campaign_checkout_session(slug):
    """Create a Stripe Checkout Session for a donation or sponsor package."""
    try:
        checkout = _ff_checkout_payload()

        flow = str(checkout.get("flow") or "donation").strip() or "donation"
        sponsor_tier = str(checkout.get("sponsor_tier") or "").strip()
        donor_email = str(checkout.get("email") or checkout.get("donor_email") or "").strip()
        amount_cents = int(checkout.get("amount_cents") or 0)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_secret:
        return (
            jsonify(
                {
                    "error": "Stripe is not configured. Set STRIPE_SECRET_KEY.",
                    "code": "stripe_not_configured",
                }
            ),
            503,
        )

    try:
        import stripe
    except Exception:
        return (
            jsonify(
                {
                    "error": "Stripe Python package is not installed.",
                    "code": "stripe_package_missing",
                }
            ),
            503,
        )

    stripe.api_key = stripe_secret

    product_name = (
        f"{sponsor_tier.title()} Sponsor Package"
        if flow == "sponsor" and sponsor_tier
        else "Campaign Donation"
    )

    description = f"{checkout.get('label') or 'FutureFunded campaign donation'} for campaign {slug}"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=donor_email or None,
            client_reference_id=f"{slug}:{flow}:{sponsor_tier or 'none'}",
            success_url=_ff_campaign_success_url(slug),
            cancel_url=_ff_campaign_cancel_url(slug),
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": product_name,
                            "description": description,
                        },
                    },
                }
            ],
            metadata={
                "campaign_slug": slug,
                "flow": checkout.get("flow") or "donation",
                "sponsor_tier": checkout.get("sponsor_tier") or "none",
                "donor_email": donor_email,
                "business_name": checkout.get("business_name", ""),
                "contact_name": checkout.get("contact_name", ""),
                "contact_email": checkout.get("contact_email", ""),
                "website_url": checkout.get("website_url", ""),
                "display_preference": checkout.get("display_preference", "public"),
            },
        )

        # FF_WAVE10B_PRIMARY_CHECKOUT_REVIEW_QUEUE_REPAIR_V2_START
        try:
            sponsor_intake = _ff_wave10b_sponsor_intake_from_payload(checkout)
            if sponsor_intake:
                _ff_wave10b_write_sponsor_review_queue(
                    slug,
                    session,
                    checkout,
                    status="checkout_created",
                )

                # Best-effort Stripe metadata sync. Never block checkout.
                try:
                    session_id_for_metadata = _ff_wave10b_session_id(session)
                    if session_id_for_metadata:
                        stripe.checkout.Session.modify(
                            session_id_for_metadata,
                            metadata=sponsor_intake,
                        )
                except Exception:
                    current_app.logger.exception(
                        "FutureFunded sponsor metadata Stripe session update failed"
                    )
        except Exception:
            current_app.logger.exception(
                "FutureFunded primary checkout sponsor review queue write failed"
            )
        # FF_WAVE10B_PRIMARY_CHECKOUT_REVIEW_QUEUE_REPAIR_V2_END

    except Exception as exc:
        current_app.logger.exception("Stripe Checkout session creation failed")
        return jsonify({"error": str(exc), "code": "stripe_checkout_failed"}), 502

    return jsonify(
        {
            "provider": "stripe",
            "id": session.id,
            "url": session.url,
        }
    )


def _ff_paypal_base_url():
    env = os.getenv("PAYPAL_ENV", "sandbox").lower()
    return "https://api-m.paypal.com" if env == "live" else "https://api-m.sandbox.paypal.com"


def _ff_paypal_access_token():
    client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise RuntimeError(
            "PayPal is not configured. Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET."
        )

    token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    req = urllib.request.Request(
        f"{_ff_paypal_base_url()}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["access_token"]


def _ff_paypal_request(path, payload):
    token = _ff_paypal_access_token()
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        f"{_ff_paypal_base_url()}{path}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


@campaign_bp.post("/c/<slug>/paypal/orders")
def ff_create_paypal_order(slug):
    """Create a PayPal Orders v2 order."""
    try:
        checkout = _ff_checkout_payload()
        amount_cents = int(checkout.get("amount_cents") or 0)
        amount_dollars = checkout.get("amount") or (amount_cents / 100)
        flow = str(checkout.get("flow") or "donation")
        sponsor_tier = str(checkout.get("sponsor_tier") or "").strip()
        value = _ff_money_to_paypal_value(amount_dollars)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    description = (
        f"{sponsor_tier.title()} sponsor package for {slug}"
        if flow == "sponsor" and sponsor_tier
        else f"Donation for {slug}"
    )

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "custom_id": f"{slug}:{flow}:{sponsor_tier or 'none'}",
                "description": description[:127],
                "amount": {
                    "currency_code": "USD",
                    "value": value,
                },
            }
        ],
        "application_context": {
            "brand_name": "FutureFunded",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "PAY_NOW",
            "return_url": f"{_ff_public_base_url()}/c/{slug}?payment=paypal-success",
            "cancel_url": f"{_ff_public_base_url()}/c/{slug}?payment=paypal-cancelled",
        },
    }

    try:
        order = _ff_paypal_request("/v2/checkout/orders", payload)
    except Exception as exc:
        current_app.logger.exception("PayPal order creation failed")
        return jsonify({"error": str(exc), "code": "paypal_create_order_failed"}), 502

    return jsonify(order)


@campaign_bp.post("/c/<slug>/paypal/orders/<order_id>/capture")
def ff_capture_paypal_order(slug, order_id):
    """Capture an approved PayPal Orders v2 order."""
    try:
        result = _ff_paypal_request(f"/v2/checkout/orders/{order_id}/capture", {})
    except Exception as exc:
        current_app.logger.exception("PayPal order capture failed")
        return jsonify({"error": str(exc), "code": "paypal_capture_failed"}), 502

    return jsonify(result)


# ---------------------------------------------------------------------------
# FutureFunded payment ledger + Stripe webhook
# Durable MVP ledger:
# - ff_payment_events: provider webhook audit/idempotency
# - ff_donations: completed donation payments
# - ff_sponsor_orders: completed sponsor payments pending fulfillment
# - ff_campaign_totals: campaign aggregate raised total
# ---------------------------------------------------------------------------

from datetime import UTC, datetime

from sqlalchemy import text as _ff_sql_text


def _ff_utcnow_iso():
    return datetime.now(UTC).isoformat()


class _FFLedgerDbAdapter:
    def __init__(self, session):
        self.session = session


def _ff_db():
    """Return the app SQLAlchemy db/session, or a durable local ledger fallback.

    Some FutureFunded app surfaces do not register Flask-SQLAlchemy on the web
    app process. The payment ledger still needs durable storage for local/demo
    checkout + webhook flows, so we fall back to a small SQLAlchemy-managed
    SQLite database in instance/ when no app db extension is available.
    """
    db = current_app.extensions.get("sqlalchemy")
    if db is not None and hasattr(db, "session"):
        return db

    # Common project extension locations.
    for module_name in (
        "apps.web.app.extensions",
        "apps.web.app",
        "app.extensions",
        "app",
    ):
        try:
            module = __import__(module_name, fromlist=["db"])
            candidate = getattr(module, "db", None)
        except Exception:
            candidate = None

        if candidate is not None and hasattr(candidate, "session"):
            return candidate

    adapter = current_app.extensions.get("ff_payment_ledger_db")
    if adapter is not None:
        return adapter

    from pathlib import Path as _Path

    from sqlalchemy import create_engine as _ff_create_engine
    from sqlalchemy.orm import scoped_session as _ff_scoped_session
    from sqlalchemy.orm import sessionmaker as _ff_sessionmaker

    database_uri = (
        current_app.config.get("FF_PAYMENT_LEDGER_DATABASE_URI")
        or current_app.config.get("SQLALCHEMY_DATABASE_URI")
        or os.getenv("FF_PAYMENT_LEDGER_DATABASE_URI", "").strip()
    )

    if not database_uri:
        instance_path = _Path(current_app.instance_path)
        instance_path.mkdir(parents=True, exist_ok=True)
        database_uri = f"sqlite:///{instance_path / 'ff_payment_ledger.sqlite3'}"

    engine = _ff_create_engine(database_uri, future=True)
    session = _ff_scoped_session(
        _ff_sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    )

    adapter = _FFLedgerDbAdapter(session)
    current_app.extensions["ff_payment_ledger_db"] = adapter
    return adapter


def _ff_ensure_payment_tables():
    db = _ff_db()

    statements = [
        """
        CREATE TABLE IF NOT EXISTS ff_payment_events (
            provider_event_id VARCHAR(255) PRIMARY KEY,
            provider VARCHAR(32) NOT NULL,
            event_type VARCHAR(128) NOT NULL,
            status VARCHAR(32) NOT NULL,
            payload_json TEXT NOT NULL,
            processed_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ff_donations (
            provider_session_id VARCHAR(255) PRIMARY KEY,
            campaign_slug VARCHAR(255) NOT NULL,
            provider VARCHAR(32) NOT NULL,
            provider_payment_intent_id VARCHAR(255),
            amount_cents INTEGER NOT NULL,
            currency VARCHAR(12) NOT NULL,
            donor_email VARCHAR(255),
            donor_name VARCHAR(255),
            message TEXT,
            status VARCHAR(32) NOT NULL,
            created_at TEXT NOT NULL,
            raw_json TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ff_sponsor_orders (
            provider_session_id VARCHAR(255) PRIMARY KEY,
            campaign_slug VARCHAR(255) NOT NULL,
            provider VARCHAR(32) NOT NULL,
            provider_payment_intent_id VARCHAR(255),
            sponsor_tier VARCHAR(80),
            business_name VARCHAR(255),
            contact_name VARCHAR(255),
            contact_email VARCHAR(255),
            website_url VARCHAR(500),
            logo_url VARCHAR(500),
            display_preference VARCHAR(80),
            amount_cents INTEGER NOT NULL,
            currency VARCHAR(12) NOT NULL,
            status VARCHAR(32) NOT NULL,
            fulfillment_status VARCHAR(32) NOT NULL,
            created_at TEXT NOT NULL,
            raw_json TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ff_campaign_totals (
            campaign_slug VARCHAR(255) PRIMARY KEY,
            raised_amount_cents INTEGER NOT NULL,
            donation_count INTEGER NOT NULL,
            sponsor_count INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
    ]

    for statement in statements:
        db.session.execute(_ff_sql_text(statement))


def _ff_row_exists(query, params):
    db = _ff_db()
    return db.session.execute(_ff_sql_text(query), params).first() is not None


def _ff_upsert_campaign_total(campaign_slug, amount_cents, flow):
    db = _ff_db()
    now = _ff_utcnow_iso()

    row = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT raised_amount_cents, donation_count, sponsor_count
            FROM ff_campaign_totals
            WHERE campaign_slug = :campaign_slug
            """
            ),
            {"campaign_slug": campaign_slug},
        )
        .mappings()
        .first()
    )

    donation_increment = 1 if flow != "sponsor" else 0
    sponsor_increment = 1 if flow == "sponsor" else 0

    if row:
        db.session.execute(
            _ff_sql_text(
                """
                UPDATE ff_campaign_totals
                SET raised_amount_cents = :raised_amount_cents,
                    donation_count = :donation_count,
                    sponsor_count = :sponsor_count,
                    updated_at = :updated_at
                WHERE campaign_slug = :campaign_slug
                """
            ),
            {
                "campaign_slug": campaign_slug,
                "raised_amount_cents": int(row["raised_amount_cents"]) + int(amount_cents),
                "donation_count": int(row["donation_count"]) + donation_increment,
                "sponsor_count": int(row["sponsor_count"]) + sponsor_increment,
                "updated_at": now,
            },
        )
    else:
        db.session.execute(
            _ff_sql_text(
                """
                INSERT INTO ff_campaign_totals (
                    campaign_slug,
                    raised_amount_cents,
                    donation_count,
                    sponsor_count,
                    updated_at
                )
                VALUES (
                    :campaign_slug,
                    :raised_amount_cents,
                    :donation_count,
                    :sponsor_count,
                    :updated_at
                )
                """
            ),
            {
                "campaign_slug": campaign_slug,
                "raised_amount_cents": int(amount_cents),
                "donation_count": donation_increment,
                "sponsor_count": sponsor_increment,
                "updated_at": now,
            },
        )


def _ff_checkout_session_to_ledger(session):
    db = _ff_db()

    session_id = session.get("id", "")
    metadata = session.get("metadata") or {}
    client_reference_id = session.get("client_reference_id") or ""

    campaign_slug = (
        metadata.get("campaign_slug")
        or metadata.get("campaign")
        or (client_reference_id.split(":")[0] if client_reference_id else "")
        or "unknown"
    )

    flow = metadata.get("flow") or "donation"
    sponsor_tier = metadata.get("sponsor_tier") or ""
    amount_cents = int(session.get("amount_total") or session.get("amount_subtotal") or 0)
    currency = (session.get("currency") or "usd").lower()
    payment_intent = session.get("payment_intent") or ""
    if isinstance(payment_intent, dict):
        payment_intent = payment_intent.get("id", "")

    customer_details = session.get("customer_details") or {}
    donor_email = (
        metadata.get("donor_email")
        or customer_details.get("email")
        or session.get("customer_email")
        or ""
    )

    donor_name = customer_details.get("name") or metadata.get("donor_name") or ""
    status = (
        "succeeded"
        if session.get("payment_status") == "paid"
        else (session.get("payment_status") or "completed")
    )
    raw_json = json.dumps(session, default=str)
    now = _ff_utcnow_iso()

    if not session_id or amount_cents <= 0:
        return {"recorded": False, "reason": "missing_session_or_amount"}

    existing_donation = (
        db.session.execute(
            _ff_sql_text(
                """
                SELECT provider_session_id, campaign_slug, amount_cents
                FROM ff_donations
                WHERE provider_session_id = :session_id
                """
            ),
            {"session_id": session_id},
        )
        .mappings()
        .first()
    )

    existing_sponsor = (
        db.session.execute(
            _ff_sql_text(
                """
                SELECT provider_session_id, campaign_slug, amount_cents
                FROM ff_sponsor_orders
                WHERE provider_session_id = :session_id
                """
            ),
            {"session_id": session_id},
        )
        .mappings()
        .first()
    )

    existing_row = existing_donation or existing_sponsor

    if existing_row:
        existing_campaign = str(existing_row.get("campaign_slug") or "").strip()

        if existing_campaign in {"", "unknown"} and campaign_slug and campaign_slug != "unknown":
            table_name = "ff_donations" if existing_donation else "ff_sponsor_orders"

            db.session.execute(
                _ff_sql_text(
                    f"""
                    UPDATE {table_name}
                    SET campaign_slug = :campaign_slug
                    WHERE provider_session_id = :session_id
                    """
                ),
                {
                    "campaign_slug": campaign_slug,
                    "session_id": session_id,
                },
            )

            _ff_upsert_campaign_total(campaign_slug, amount_cents, flow)

            donation_decrement = 1 if flow != "sponsor" else 0
            sponsor_decrement = 1 if flow == "sponsor" else 0

            db.session.execute(
                _ff_sql_text(
                    """
                    UPDATE ff_campaign_totals
                    SET raised_amount_cents = CASE
                            WHEN raised_amount_cents >= :amount_cents
                            THEN raised_amount_cents - :amount_cents
                            ELSE 0
                        END,
                        donation_count = CASE
                            WHEN donation_count >= :donation_decrement
                            THEN donation_count - :donation_decrement
                            ELSE 0
                        END,
                        sponsor_count = CASE
                            WHEN sponsor_count >= :sponsor_decrement
                            THEN sponsor_count - :sponsor_decrement
                            ELSE 0
                        END,
                        updated_at = :updated_at
                    WHERE campaign_slug = 'unknown'
                    """
                ),
                {
                    "amount_cents": amount_cents,
                    "donation_decrement": donation_decrement,
                    "sponsor_decrement": sponsor_decrement,
                    "updated_at": now,
                },
            )

            current_app.logger.info(
                "FutureFunded payment reconciled | old_campaign=%s new_campaign=%s session=%s",
                existing_campaign,
                campaign_slug,
                session_id,
            )

            return {
                "recorded": True,
                "reconciled": True,
                "campaign_slug": campaign_slug,
                "flow": flow,
                "amount_cents": amount_cents,
                "session_id": session_id,
            }

        return {
            "recorded": False,
            "duplicate": True,
            "campaign_slug": existing_campaign or campaign_slug,
            "session_id": session_id,
        }

    if flow == "sponsor":
        db.session.execute(
            _ff_sql_text(
                """
                INSERT INTO ff_sponsor_orders (
                    provider_session_id,
                    campaign_slug,
                    provider,
                    provider_payment_intent_id,
                    sponsor_tier,
                    business_name,
                    contact_name,
                    contact_email,
                    website_url,
                    logo_url,
                    display_preference,
                    amount_cents,
                    currency,
                    status,
                    fulfillment_status,
                    created_at,
                    raw_json
                )
                VALUES (
                    :provider_session_id,
                    :campaign_slug,
                    'stripe',
                    :provider_payment_intent_id,
                    :sponsor_tier,
                    :business_name,
                    :contact_name,
                    :contact_email,
                    :website_url,
                    :logo_url,
                    :display_preference,
                    :amount_cents,
                    :currency,
                    :status,
                    'pending_review',
                    :created_at,
                    :raw_json
                )
                """
            ),
            {
                "provider_session_id": session_id,
                "campaign_slug": campaign_slug,
                "provider_payment_intent_id": payment_intent,
                "sponsor_tier": sponsor_tier,
                "business_name": metadata.get("business_name", ""),
                "contact_name": metadata.get("contact_name", ""),
                "contact_email": metadata.get("contact_email") or donor_email,
                "website_url": metadata.get("website_url", ""),
                "logo_url": "",
                "display_preference": metadata.get("display_preference", "public"),
                "amount_cents": amount_cents,
                "currency": currency,
                "status": status,
                "created_at": now,
                "raw_json": raw_json,
            },
        )
    else:
        db.session.execute(
            _ff_sql_text(
                """
                INSERT INTO ff_donations (
                    provider_session_id,
                    campaign_slug,
                    provider,
                    provider_payment_intent_id,
                    amount_cents,
                    currency,
                    donor_email,
                    donor_name,
                    message,
                    status,
                    created_at,
                    raw_json
                )
                VALUES (
                    :provider_session_id,
                    :campaign_slug,
                    'stripe',
                    :provider_payment_intent_id,
                    :amount_cents,
                    :currency,
                    :donor_email,
                    :donor_name,
                    :message,
                    :status,
                    :created_at,
                    :raw_json
                )
                """
            ),
            {
                "provider_session_id": session_id,
                "campaign_slug": campaign_slug,
                "provider_payment_intent_id": payment_intent,
                "amount_cents": amount_cents,
                "currency": currency,
                "donor_email": donor_email,
                "donor_name": donor_name,
                "message": metadata.get("message", ""),
                "status": status,
                "created_at": now,
                "raw_json": raw_json,
            },
        )

    _ff_upsert_campaign_total(campaign_slug, amount_cents, flow)

    current_app.logger.info(
        "FutureFunded payment recorded | campaign=%s flow=%s amount_cents=%s session=%s",
        campaign_slug,
        flow,
        amount_cents,
        session_id,
    )

    return {
        "recorded": True,
        "campaign_slug": campaign_slug,
        "flow": flow,
        "amount_cents": amount_cents,
        "session_id": session_id,
    }


@campaign_bp.post("/c/stripe/webhook")
def ff_stripe_webhook():
    """Verified Stripe webhook intake for payment ledger fulfillment."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

    try:
        import stripe
    except Exception:
        return (
            jsonify(
                {
                    "error": "Stripe Python package is not installed.",
                    "code": "stripe_package_missing",
                }
            ),
            503,
        )

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as exc:
            return jsonify({"error": str(exc), "code": "stripe_signature_invalid"}), 400
    elif os.getenv("FF_ALLOW_UNSIGNED_STRIPE_WEBHOOKS", "").strip() == "1":
        try:
            event = json.loads(payload.decode("utf-8") or "{}")
        except Exception:
            return jsonify({"error": "Invalid webhook JSON.", "code": "invalid_json"}), 400
    else:
        return (
            jsonify(
                {
                    "error": "Stripe webhook secret is not configured.",
                    "code": "stripe_webhook_not_configured",
                }
            ),
            503,
        )

    event_id = event.get("id", "")
    event_type = event.get("type", "")

    if not event_id:
        return jsonify({"error": "Missing Stripe event id.", "code": "missing_event_id"}), 400

    db = _ff_db()
    _ff_ensure_payment_tables()

    if _ff_row_exists(
        "SELECT provider_event_id FROM ff_payment_events WHERE provider_event_id = :event_id",
        {"event_id": event_id},
    ):
        return jsonify({"received": True, "duplicate": True, "event_id": event_id})

    now = _ff_utcnow_iso()

    db.session.execute(
        _ff_sql_text(
            """
            INSERT INTO ff_payment_events (
                provider_event_id,
                provider,
                event_type,
                status,
                payload_json,
                processed_at
            )
            VALUES (
                :provider_event_id,
                'stripe',
                :event_type,
                'processing',
                :payload_json,
                :processed_at
            )
            """
        ),
        {
            "provider_event_id": event_id,
            "event_type": event_type,
            "payload_json": json.dumps(event, default=str),
            "processed_at": now,
        },
    )

    result = {"ignored": True}

    try:
        if event_type == "checkout.session.completed":
            session = (event.get("data") or {}).get("object") or {}
            result = _ff_checkout_session_to_ledger(session)

            # FF_LIFECYCLE_WEBHOOK_DISPATCH_V1_START
            lifecycle_result = _ff_dispatch_checkout_lifecycle(
                slug=None,
                session=session,
                source="stripe_webhook",
            )
            if isinstance(result, dict):
                result["lifecycle"] = lifecycle_result
            # FF_LIFECYCLE_WEBHOOK_DISPATCH_V1_END

        db.session.execute(
            _ff_sql_text(
                """
                UPDATE ff_payment_events
                SET status = 'processed',
                    processed_at = :processed_at
                WHERE provider_event_id = :provider_event_id
                """
            ),
            {"provider_event_id": event_id, "processed_at": _ff_utcnow_iso()},
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("FutureFunded webhook processing failed")
        return (
            jsonify({"error": "Webhook processing failed.", "code": "webhook_processing_failed"}),
            500,
        )

    return jsonify(
        {
            "received": True,
            "event_id": event_id,
            "event_type": event_type,
            "result": result,
        }
    )


def _ff_campaign_ledger_snapshot(slug):
    """Return campaign ledger totals/recent activity as a plain dict."""
    db = _ff_db()
    _ff_ensure_payment_tables()
    db.session.commit()

    total = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT campaign_slug, raised_amount_cents, donation_count, sponsor_count, updated_at
            FROM ff_campaign_totals
            WHERE campaign_slug = :slug
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .first()
    )

    donations = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT provider_session_id, amount_cents, currency, donor_email, status, created_at
            FROM ff_donations
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            LIMIT 10
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    sponsors = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT provider_session_id, sponsor_tier, business_name, contact_email,
                   amount_cents, currency, status, fulfillment_status, created_at
            FROM ff_sponsor_orders
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            LIMIT 10
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    return {
        "campaignSlug": slug,
        "totals": (
            dict(total)
            if total
            else {
                "campaign_slug": slug,
                "raised_amount_cents": 0,
                "donation_count": 0,
                "sponsor_count": 0,
                "updated_at": None,
            }
        ),
        "recentDonations": [dict(row) for row in donations],
        "recentSponsors": [dict(row) for row in sponsors],
    }


@campaign_bp.get("/c/<slug>/ledger/summary")
def ff_campaign_ledger_summary(slug):
    """Read-only campaign ledger summary for admin/debug surfaces."""
    db = _ff_db()
    _ff_ensure_payment_tables()
    db.session.commit()

    total = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT campaign_slug, raised_amount_cents, donation_count, sponsor_count, updated_at
            FROM ff_campaign_totals
            WHERE campaign_slug = :slug
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .first()
    )

    donations = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT provider_session_id, amount_cents, currency, donor_email, status, created_at
            FROM ff_donations
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            LIMIT 10
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    sponsors = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT provider_session_id, sponsor_tier, business_name, contact_email,
                   amount_cents, currency, status, fulfillment_status, created_at
            FROM ff_sponsor_orders
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            LIMIT 10
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    return jsonify(
        {
            "campaignSlug": slug,
            "totals": (
                dict(total)
                if total
                else {
                    "campaign_slug": slug,
                    "raised_amount_cents": 0,
                    "donation_count": 0,
                    "sponsor_count": 0,
                    "updated_at": None,
                }
            ),
            "recentDonations": [dict(row) for row in donations],
            "recentSponsors": [dict(row) for row in sponsors],
        }
    )


# ---------------------------------------------------------------------------
# FutureFunded operator access guard
# Production posture:
# - authenticated admin/operator users are allowed when Flask-Login exists
# - FF_OPERATOR_ACCESS_TOKEN protects operator endpoints when configured
# - local debug fallback is allowed only when no operator token is configured
# ---------------------------------------------------------------------------


def _ff_request_operator_token():
    """
    Return the operator token from request-safe locations.

    This helper protects GET routes such as ledger export. It must never call
    checkout/donation payload parsing because those helpers validate donation
    amounts and can raise on non-payment requests.
    """
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            return token

    candidates = [
        request.headers.get("X-FF-Operator-Token", ""),
        request.headers.get("X-Operator-Token", ""),
        request.args.get("operator_token", ""),
        request.args.get("access_token", ""),
        request.args.get("token", ""),
    ]

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        try:
            candidates.extend(
                [
                    request.form.get("operator_token", ""),
                    request.form.get("operatorToken", ""),
                    request.form.get("access_token", ""),
                    request.form.get("token", ""),
                ]
            )
        except Exception:
            pass

        try:
            payload = request.get_json(silent=True) or {}
            if isinstance(payload, dict):
                candidates.extend(
                    [
                        payload.get("operator_token", ""),
                        payload.get("operatorToken", ""),
                        payload.get("access_token", ""),
                        payload.get("token", ""),
                    ]
                )
        except Exception:
            pass

    for value in candidates:
        token = str(value or "").strip()
        if token:
            return token

    return ""


def _ff_current_user_can_operate_campaign(_slug=None):
    try:
        from flask import session as flask_session

        if flask_session.get("ff_operator_user_id"):
            return True
    except Exception:
        pass

    try:
        from flask_login import current_user
    except Exception:
        return False

    try:
        if not getattr(current_user, "is_authenticated", False):
            return False

        for attr in (
            "is_admin",
            "is_staff",
            "is_operator",
            "is_campaign_manager",
            "can_manage_campaigns",
        ):
            value = getattr(current_user, attr, False)
            if callable(value):
                value = value()
            if bool(value):
                return True

        roles = getattr(current_user, "roles", None) or getattr(current_user, "role", None) or []
        if isinstance(roles, str):
            roles = [roles]

        allowed_roles = {"admin", "owner", "operator", "organizer", "campaign_manager"}
        return any(str(role).lower() in allowed_roles for role in roles)
    except Exception:
        return False


def _ff_operator_access_allowed(slug=None):
    required_token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    if _ff_current_user_can_operate_campaign(slug):
        return True

    provided_token = _ff_request_operator_token()

    if required_token:
        return bool(provided_token and provided_token == required_token)

    return False


def _ff_operator_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        slug = kwargs.get("slug")
        if _ff_operator_access_allowed(slug):
            return view(*args, **kwargs)

        return (
            jsonify(
                {
                    "error": "Operator access required.",
                    "code": "operator_access_required",
                }
            ),
            403,
        )

    return wrapped


# ---------------------------------------------------------------------------
# FutureFunded operator ledger endpoints
# Dashboard support:
# - recent payment events
# - manual/offline donation entry
# - CSV export foundation
# ---------------------------------------------------------------------------


@campaign_bp.get("/c/<slug>/ledger/events")
@_ff_operator_required
def ff_campaign_ledger_events(slug):
    """Recent provider/payment events for operator visibility."""
    db = _ff_db()
    _ff_ensure_payment_tables()
    db.session.commit()

    events = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT provider_event_id, provider, event_type, status, processed_at
            FROM ff_payment_events
            ORDER BY processed_at DESC
            LIMIT 25
            """
            )
        )
        .mappings()
        .all()
    )

    return jsonify(
        {
            "campaignSlug": slug,
            "events": [dict(row) for row in events],
        }
    )


@campaign_bp.post("/c/<slug>/ledger/offline-donation")
@_ff_operator_required
def ff_create_offline_donation(slug):
    """Record a cash/check/offline donation into the campaign ledger."""
    import uuid

    payload = _ff_checkout_payload()

    try:
        amount_cents = _ff_money_to_cents(payload.get("amount"), minimum=1, maximum=50000)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "invalid_amount"}), 400

    donor_name = (payload.get("donor_name") or payload.get("donorName") or "").strip()
    donor_email = (payload.get("donor_email") or payload.get("donorEmail") or "").strip()
    message = (payload.get("message") or "").strip()
    note = (payload.get("note") or "").strip()
    now = _ff_utcnow_iso()
    provider_session_id = f"manual_{uuid.uuid4().hex}"

    db = _ff_db()
    _ff_ensure_payment_tables()

    db.session.execute(
        _ff_sql_text(
            """
            INSERT INTO ff_donations (
                provider_session_id,
                campaign_slug,
                provider,
                provider_payment_intent_id,
                amount_cents,
                currency,
                donor_email,
                donor_name,
                message,
                status,
                created_at,
                raw_json
            )
            VALUES (
                :provider_session_id,
                :campaign_slug,
                'manual',
                '',
                :amount_cents,
                'usd',
                :donor_email,
                :donor_name,
                :message,
                'succeeded',
                :created_at,
                :raw_json
            )
            """
        ),
        {
            "provider_session_id": provider_session_id,
            "campaign_slug": slug,
            "amount_cents": amount_cents,
            "donor_email": donor_email,
            "donor_name": donor_name,
            "message": message or note,
            "created_at": now,
            "raw_json": json.dumps(
                {
                    "source": "operator_dashboard",
                    "note": note,
                    "message": message,
                }
            ),
        },
    )

    _ff_upsert_campaign_total(slug, amount_cents, "donation")
    db.session.commit()

    notification = None
    try:
        notification = record_operator_notification(
            event_type="offline_donation_recorded",
            event_id=f"offline_donation_recorded:{provider_session_id}",
            subject="Offline support recorded",
            body=(
                f"Offline support was recorded for campaign {slug}. "
                f"Amount: ${amount_cents / 100:,.2f}. "
                f"Donor: {donor_name or donor_email or 'Anonymous/supporter'}."
            ),
            metadata={
                "campaign_slug": slug,
                "provider_session_id": provider_session_id,
                "amount_cents": amount_cents,
                "amount_display": f"${amount_cents / 100:,.2f}",
                "donor_name": donor_name,
                "donor_email": donor_email,
                "message": message,
                "note": note,
                "source": "operator_offline_donation",
            },
        )
    except Exception:
        current_app.logger.exception("FutureFunded offline donation notification failed")
        notification = {"ok": False, "error": "notification_failed"}

    current_app.logger.info(
        "FutureFunded offline donation recorded | campaign=%s amount_cents=%s session=%s",
        slug,
        amount_cents,
        provider_session_id,
    )

    return (
        jsonify(
            {
                "ok": True,
                "campaignSlug": slug,
                "provider_session_id": provider_session_id,
                "amount_cents": amount_cents,
                "notification": notification,
            }
        ),
        201,
    )


@campaign_bp.get("/c/<slug>/ledger/export.csv")
@_ff_operator_required
def ff_campaign_ledger_export_csv(slug):
    """CSV export for donations and sponsor orders."""
    import csv
    import io

    from flask import Response

    db = _ff_db()
    _ff_ensure_payment_tables()
    db.session.commit()

    donations = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT 'donation' AS record_type,
                   provider_session_id,
                   provider,
                   amount_cents,
                   currency,
                   donor_name AS name,
                   donor_email AS email,
                   '' AS sponsor_tier,
                   status,
                   created_at
            FROM ff_donations
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    sponsors = (
        db.session.execute(
            _ff_sql_text(
                """
            SELECT 'sponsor' AS record_type,
                   provider_session_id,
                   provider,
                   amount_cents,
                   currency,
                   business_name AS name,
                   contact_email AS email,
                   sponsor_tier,
                   status,
                   created_at
            FROM ff_sponsor_orders
            WHERE campaign_slug = :slug
            ORDER BY created_at DESC
            """
            ),
            {"slug": slug},
        )
        .mappings()
        .all()
    )

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "record_type",
            "provider_session_id",
            "provider",
            "amount_cents",
            "currency",
            "name",
            "email",
            "sponsor_tier",
            "status",
            "created_at",
        ],
    )
    writer.writeheader()

    for row in list(donations) + list(sponsors):
        writer.writerow(dict(row))

    filename = f"futurefunded-{slug}-ledger.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# FutureFunded embedded Stripe Checkout
# ---------------------------------------------------------------------------

def _ff_env_value(name: str, default: str = "") -> str:
    return str(current_app.config.get(name) or os.getenv(name) or default).strip()


def _ff_public_base_url_for_checkout() -> str:
    configured = (
        _ff_env_value("FF_PUBLIC_BASE_URL")
        or _ff_env_value("PUBLIC_BASE_URL")
        or _ff_env_value("CANONICAL_BASE_URL")
        or request.url_root
        or "https://getfuturefunded.com/"
    )
    return configured.rstrip("/")


def _ff_int_cents(value, fallback: int = 5000) -> int:
    try:
        raw = str(value or "").strip().replace("$", "").replace(",", "")
        if not raw:
            return fallback
        # If callers pass amount_cents, keep cents. If callers pass amount, convert dollars.
        amount = float(raw)
        return int(round(amount * 100))
    except Exception:
        return fallback


def _ff_build_embedded_checkout_session(slug: str):
    payload = request.get_json(silent=True) or request.form.to_dict() or {}

    secret_key = _ff_env_value("STRIPE_SECRET_KEY")
    publishable_key = _ff_env_value("STRIPE_PUBLISHABLE_KEY")

    if not secret_key or not secret_key.startswith(("sk_test_", "sk_live_")):
        return jsonify({"ok": False, "error": "Stripe secret key is not configured."}), 503

    if not publishable_key or not publishable_key.startswith(("pk_test_", "pk_live_")):
        return jsonify({"ok": False, "error": "Stripe publishable key is not configured."}), 503

    amount_cents = payload.get("amount_cents")
    if amount_cents:
        try:
            amount_cents = int(amount_cents)
        except Exception:
            amount_cents = 5000
    else:
        amount_cents = _ff_int_cents(payload.get("amount"), fallback=5000)

    min_cents = 100
    max_cents = 500000

    if amount_cents < min_cents:
        return jsonify({"ok": False, "error": "Donation amount is below the minimum."}), 400

    if amount_cents > max_cents:
        return jsonify({"ok": False, "error": "Donation amount is above the maximum."}), 400

    donor_email = str(payload.get("email") or payload.get("donor_email") or "").strip()
    donor_name = str(payload.get("name") or payload.get("donor_name") or "").strip()

    stripe.api_key = secret_key

    return_url = (
        _ff_public_base_url_for_checkout()
        + f"/c/{slug}?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    )

    params = {
        "mode": "payment",
        "ui_mode": "embedded",
        "return_url": return_url,
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": DEFAULT_CAMPAIGN_NAME,
                        "description": "Support travel, tournament fees, gym time, gear, meals, and player development.",
                    },
                },
            }
        ],
        "metadata": {
            "campaign": slug,
            "platform": "futurefunded",
            "donor_name": donor_name,
            "donor_email": donor_email,
        },
    }

    # FF_EMBEDDED_CHECKOUT_METADATA_V2
    params["client_reference_id"] = f"{slug}:donation:none"
    params["metadata"]["campaign_slug"] = slug
    params["metadata"]["flow"] = "donation"
    params["metadata"].setdefault("sponsor_tier", "none")
    params["payment_intent_data"] = {"metadata": dict(params["metadata"])}

    if donor_email:
        params["customer_email"] = donor_email

    # FF_WAVE10B_SPONSOR_METADATA_PARAMS_START
    sponsor_intake = _ff_wave10b_sponsor_intake_from_payload(payload)
    if sponsor_intake:
        params.setdefault("metadata", {})
        try:
            params["metadata"].update(sponsor_intake)
        except Exception:
            params["metadata"] = {**dict(params.get("metadata") or {}), **sponsor_intake}
    # FF_WAVE10B_SPONSOR_METADATA_PARAMS_END

    try:
        session = stripe.checkout.Session.create(**params)
        _ff_wave10b_write_sponsor_review_queue(slug, session, payload, status="checkout_created")
    except Exception as exc:
        # Compatibility fallback for Stripe API versions/accounts that expose embedded_page.
        message = str(exc)
        if "ui_mode" in message or "embedded" in message:
            params["ui_mode"] = "embedded_page"
            session = stripe.checkout.Session.create(**params)
            _ff_wave10b_write_sponsor_review_queue(slug, session, payload, status="checkout_created")
        else:
            current_app.logger.exception("Embedded Stripe Checkout session failed")
            return jsonify({"ok": False, "error": "Stripe embedded checkout session failed."}), 503

    client_secret = getattr(session, "client_secret", None) or session.get("client_secret")

    if not client_secret:
        return jsonify({"ok": False, "error": "Stripe did not return a client secret."}), 503

    return jsonify({
        "ok": True,
        "clientSecret": client_secret,
        "sessionId": getattr(session, "id", None) or session.get("id"),
        "publishableKey": publishable_key,
    })


@campaign_bp.post("/<slug>/checkout/embedded-session")
@campaign_bp.post("/c/<slug>/checkout/embedded-session")
def _ff_embedded_checkout_session_v1(slug: str):
    return _ff_build_embedded_checkout_session(slug)

@campaign_bp.get("/c/<slug>/checkout/session-status")
@campaign_bp.get("/<slug>/checkout/session-status")
def ff_embedded_checkout_session_status(**route_args):
    """Verify a returned Stripe Checkout Session for post-payment thank-you UX."""
    session_id = (request.args.get("session_id") or "").strip()

    if not session_id:
        return jsonify({
            "ok": False,
            "verified": False,
            "paid": False,
            "error": "Missing session_id.",
        }), 400

    if not session_id.startswith("cs_"):
        return jsonify({
            "ok": False,
            "verified": False,
            "paid": False,
            "error": "Invalid session_id.",
        }), 400

    secret_key = (
        os.getenv("STRIPE_SECRET_KEY")
        or current_app.config.get("STRIPE_SECRET_KEY")
        or current_app.config.get("STRIPE_API_KEY")
    )

    if not secret_key:
        return jsonify({
            "ok": False,
            "verified": False,
            "paid": False,
            "error": "Stripe verification is not configured.",
        }), 503

    stripe.api_key = secret_key

    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["payment_intent"],
        )

        payment_status = str(getattr(session, "payment_status", "") or "")
        checkout_status = str(getattr(session, "status", "") or "")
        paid = payment_status == "paid" or checkout_status == "complete"

        ledger_result = None
        lifecycle_result = None
        if paid:
            try:
                _ff_ensure_payment_tables()
                session_payload = (
                    session.to_dict_recursive()
                    if hasattr(session, "to_dict_recursive")
                    else dict(session)
                )
                ledger_result = _ff_checkout_session_to_ledger(session_payload)
                _ff_db().session.commit()

                # FF_LIFECYCLE_SESSION_STATUS_DISPATCH_V1_START
                lifecycle_slug = (
                    route_args.get("slug")
                    or (request.view_args or {}).get("slug")
                    or "connect-atx-elite"
                )
                lifecycle_result = _ff_dispatch_checkout_lifecycle(
                    slug=lifecycle_slug,
                    session=session_payload,
                    source="session_status",
                )
                # FF_LIFECYCLE_SESSION_STATUS_DISPATCH_V1_END

                try:
                    paid_metadata = dict(session_payload.get("metadata") or {})
                    paid_session_id = str(session_payload.get("id") or session_id)
                    paid_amount = session_payload.get("amount_total")
                    paid_customer_details = session_payload.get("customer_details") or {}
                    paid_email = (
                        paid_customer_details.get("email")
                        or session_payload.get("customer_email")
                        or paid_metadata.get("donor_email")
                        or paid_metadata.get("contact_email")
                        or ""
                    )

                    record_operator_notification(
                        event_type="payment_verified",
                        event_id=f"payment_verified:{paid_session_id}",
                        subject="FutureFunded payment verified",
                        body=(
                            f"A payment was verified for campaign "
                            f"{paid_metadata.get('campaign_slug') or paid_metadata.get('campaign') or route_args.get('slug') or ''}. "
                            f"Amount: ${int(paid_amount or 0) / 100:,.2f}. "
                            f"Email: {paid_email or 'not provided'}."
                        ),
                        metadata={
                            "stripe_session_id": paid_session_id,
                            "amount_total": paid_amount,
                            "amount_display": f"${int(paid_amount or 0) / 100:,.2f}",
                            "currency": session_payload.get("currency"),
                            "customer_email": paid_email,
                            "campaign_slug": (
                                paid_metadata.get("campaign_slug")
                                or paid_metadata.get("campaign")
                                or route_args.get("slug")
                                or ""
                            ),
                            "flow": paid_metadata.get("flow") or "donation",
                            "ledger": ledger_result,
            "lifecycle": lifecycle_result,
                            "source": "stripe_session_status",
                        },
                    )
                except Exception:
                    current_app.logger.exception("FutureFunded payment notification failed")
            except Exception:
                try:
                    _ff_db().session.rollback()
                except Exception:
                    pass
                current_app.logger.exception("FutureFunded session-status ledger reconcile failed")
                ledger_result = {"recorded": False, "error": "ledger_reconcile_failed"}

        customer_details = getattr(session, "customer_details", None)
        customer_email = (
            getattr(customer_details, "email", None)
            if customer_details is not None
            else None
        ) or getattr(session, "customer_email", None)

        metadata = dict(getattr(session, "metadata", None) or {})
        amount_total = getattr(session, "amount_total", None)
        currency = getattr(session, "currency", None)

        return jsonify({
            "ok": True,
            "verified": True,
            "paid": bool(paid),
            "status": checkout_status,
            "payment_status": payment_status,
            "sessionId": getattr(session, "id", session_id),
            "amount_total": amount_total,
            "amount_display": (
                f"${amount_total / 100:,.2f}"
                if isinstance(amount_total, int)
                else None
            ),
            "currency": currency,
            "customer_email": customer_email,
            "campaign_slug": (
                metadata.get("campaign_slug")
                or metadata.get("campaign")
                or route_args.get("campaign_slug")
                or route_args.get("slug")
                or ""
            ),
            "flow": metadata.get("flow") or "donation",
            "ledger": ledger_result,
        })

    except Exception as exc:
        current_app.logger.exception("FutureFunded session-status verification failed")
        return jsonify({
            "ok": False,
            "verified": False,
            "paid": False,
            "error": str(exc),
        }), 502

# FutureFunded payment readiness preflight guard
# Prevents predictable invalid payment/webhook inputs from reaching fragile internals.
try:
    _ff_payment_readiness_bp = campaign_bp
except NameError:  # pragma: no cover
    _ff_payment_readiness_bp = bp  # type: ignore[name-defined]


@_ff_payment_readiness_bp.before_app_request
def _ff_payment_readiness_preflight_guard():
    from flask import jsonify, request

    method = (request.method or "").upper()
    path = (request.path or "").rstrip("/")

    if method == "POST" and path == "/c/stripe/webhook":
        signature = (request.headers.get("Stripe-Signature") or "").strip()

        if not signature:
            return jsonify(
                {
                    "ok": False,
                    "error": "missing_stripe_signature",
                    "message": "Stripe webhook requests must include a Stripe-Signature header.",
                }
            ), 400

    if method == "POST" and path.endswith("/checkout/session"):
        payload = request.get_json(silent=True)

        if payload is None:
            return jsonify(
                {
                    "ok": False,
                    "error": "invalid_json",
                    "message": "Checkout session requests must send a JSON body.",
                }
            ), 400

        if not isinstance(payload, dict):
            return jsonify(
                {
                    "ok": False,
                    "error": "invalid_payload",
                    "message": "Checkout session payload must be a JSON object.",
                }
            ), 422

        amount = payload.get("amount")
        amount_cents = payload.get("amount_cents")

        if amount_cents in (None, "") and amount not in (None, ""):
            return jsonify(
                {
                    "ok": False,
                    "error": "amount_cents_required",
                    "message": "Use amount_cents for checkout session creation.",
                }
            ), 422

        if amount_cents not in (None, ""):
            try:
                normalized_amount_cents = int(float(str(amount_cents).strip()))
            except (TypeError, ValueError):
                return jsonify(
                    {
                        "ok": False,
                        "error": "invalid_amount_cents",
                        "message": "amount_cents must be a positive integer.",
                    }
                ), 422

            if normalized_amount_cents <= 0:
                return jsonify(
                    {
                        "ok": False,
                        "error": "invalid_amount_cents",
                        "message": "amount_cents must be greater than zero.",
                    }
                ), 422
