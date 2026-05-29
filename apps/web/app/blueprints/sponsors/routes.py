from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Any

from flask import Blueprint, current_app, g, jsonify, request

from .services import build_sponsors_service

sponsors_bp = Blueprint("sponsors", __name__, url_prefix="/sponsors")

_ALLOWED_FIELDS = {
    "business_name",
    "contact_name",
    "contact_email",
    "contact_phone",
    "sponsor_tier",
    "message",
    "campaign_slug",
    "status",
    "created_at",
    "website",  # honeypot
}

_FIELD_LIMITS = {
    "business_name": 120,
    "contact_name": 120,
    "contact_email": 254,
    "contact_phone": 32,
    "sponsor_tier": 80,
    "message": 2000,
    "campaign_slug": 120,
    "status": 32,
    "created_at": 64,
    "website": 255,
}

_BUCKET_LOCK = Lock()
_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_BUCKET_WINDOW_SECONDS = 60.0
_MAX_SPONSOR_PAYLOAD_BYTES = 32 * 1024


def _json_response(payload: dict[str, Any], status: int = 200):
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    request_id = _request_id()
    if request_id:
        response.headers["X-Request-Id"] = request_id
    return response


def _request_id() -> str | None:
    return getattr(g, "request_id", None)


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int) -> str:
    return _clean(value)[:limit]


def _client_ip() -> str:
    remote_addr = _clean(request.remote_addr)
    if remote_addr:
        return remote_addr

    forwarded_for = _clean(request.headers.get("X-Forwarded-For"))
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "unknown"

    return "unknown"


def _rate_limited(limit: int) -> bool:
    if limit <= 0:
        return False

    now = monotonic()
    key = _client_ip()

    with _BUCKET_LOCK:
        bucket = _BUCKETS[key]

        while bucket and (now - bucket[0]) > _BUCKET_WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= limit:
            return True

        bucket.append(now)
        return False


def _payload() -> dict[str, str]:
    raw: dict[str, Any]
    if request.is_json:
        raw = dict(request.get_json(silent=True) or {})
    else:
        raw = request.form.to_dict(flat=True)

    normalized: dict[str, str] = {}
    for key in _ALLOWED_FIELDS:
        if key in raw:
            normalized[key] = _truncate(raw.get(key), _FIELD_LIMITS.get(key, 255))

    return normalized


def _payload_too_large() -> bool:
    length = request.content_length
    return bool(length and length > _MAX_SPONSOR_PAYLOAD_BYTES)


def _honeypot_triggered(payload: dict[str, str]) -> bool:
    return bool(payload.get("website"))


@sponsors_bp.get("")
@sponsors_bp.get("/")
def sponsors_index():
    service = build_sponsors_service(current_app.config)
    return _json_response(
        {
            "ok": True,
            "resource": "sponsors",
            "contact_email": service.get_sponsor_contact_email(),
            "tiers": [tier.to_dict() for tier in service.get_sponsor_tiers()],
            "wall": [item.to_dict() for item in service.get_sponsor_wall()],
        }
    )


@sponsors_bp.post("/lead")
@sponsors_bp.post("/lead/")
def sponsor_lead():

    # FutureFunded: validate untrusted sponsor package form metadata at the route boundary.
    try:
        from apps.web.app.services.sponsor_package_metadata import resolve_sponsor_package_metadata

        _ff_campaign_slug = (
            request.form.get('campaign_slug')
            or request.form.get('slug')
            or request.args.get('campaign_slug')
            or request.args.get('slug')
            or DEFAULT_CAMPAIGN_SLUG
        )
        request.environ['futurefunded.sponsor_package_metadata'] = resolve_sponsor_package_metadata(
            request.form,
            campaign_slug=_ff_campaign_slug,
        )
    except Exception:
        request.environ['futurefunded.sponsor_package_metadata'] = {}

    # FutureFunded: prepare operator-facing sponsor notification payload.
    try:
        from apps.web.app.services.sponsor_operator_payload import build_sponsor_operator_payload

        _ff_operator_campaign_slug = (
            request.form.get('campaign_slug')
            or request.form.get('slug')
            or request.args.get('campaign_slug')
            or request.args.get('slug')
            or DEFAULT_CAMPAIGN_SLUG
        )
        request.environ['futurefunded.sponsor_operator_payload'] = build_sponsor_operator_payload(
            request.form,
            package_metadata=request.environ.get('futurefunded.sponsor_package_metadata', {}),
            campaign_slug=_ff_operator_campaign_slug,
        )
    except Exception:
        request.environ['futurefunded.sponsor_operator_payload'] = {}

    # FutureFunded: safely dispatch/queue operator sponsor notification.
    try:
        from apps.web.app.services.sponsor_operator_notifications import dispatch_sponsor_operator_notification

        request.environ['futurefunded.sponsor_operator_notification'] = dispatch_sponsor_operator_notification(
            request.environ.get('futurefunded.sponsor_operator_payload', {}),
        )
    except Exception:
        request.environ['futurefunded.sponsor_operator_notification'] = {
            'status': 'failed',
            'reason': 'dispatch_exception',
        }

    # FutureFunded: prepare sponsor-facing confirmation payload.
    try:
        from apps.web.app.services.campaign_profile import resolve_campaign_profile
        from apps.web.app.services.sponsor_confirmation_payload import build_sponsor_confirmation_payload

        _ff_confirmation_campaign_slug = (
            request.form.get('campaign_slug')
            or request.form.get('slug')
            or request.args.get('campaign_slug')
            or request.args.get('slug')
            or DEFAULT_CAMPAIGN_SLUG
        )
        _ff_confirmation_profile = resolve_campaign_profile(_ff_confirmation_campaign_slug)
        request.environ['futurefunded.sponsor_confirmation_payload'] = build_sponsor_confirmation_payload(
            request.form,
            package_metadata=request.environ.get('futurefunded.sponsor_package_metadata', {}),
            campaign_name=_ff_confirmation_profile.get('campaign_name') or 'Campaign',
            team_name=_ff_confirmation_profile.get('team_name') or 'Campaign',
            campaign_url=_ff_confirmation_profile.get('campaign_url') or '/',
        )
    except Exception:
        request.environ['futurefunded.sponsor_confirmation_payload'] = {}

    # FutureFunded: safely dispatch/queue sponsor confirmation notification.
    try:
        from apps.web.app.services.sponsor_confirmation_notifications import dispatch_sponsor_confirmation_notification

        request.environ['futurefunded.sponsor_confirmation_notification'] = dispatch_sponsor_confirmation_notification(
            request.environ.get('futurefunded.sponsor_confirmation_payload', {}),
        )
    except Exception:
        request.environ['futurefunded.sponsor_confirmation_notification'] = {
            'status': 'failed',
            'reason': 'dispatch_exception',
        }
    service = build_sponsors_service(current_app.config)
    request_id = _request_id()
    rate_limit = int(current_app.config.get("RATE_LIMIT_SPONSOR_PER_MINUTE", 10) or 10)

    if _payload_too_large():
        return _json_response(
            {
                "ok": False,
                "message": "Sponsor lead payload is too large.",
                "request_id": request_id,
            },
            status=413,
        )

    if _rate_limited(rate_limit):
        current_app.logger.warning(
            "Sponsor lead rate limited | ip=%s | request_id=%s",
            _client_ip(),
            request_id,
        )
        return _json_response(
            {
                "ok": False,
                "message": "Too many sponsor submissions. Please wait a minute and try again.",
                "request_id": request_id,
            },
            status=429,
        )

    payload = _payload()

    if _honeypot_triggered(payload):
        current_app.logger.info(
            "Sponsor lead honeypot triggered | ip=%s | request_id=%s",
            _client_ip(),
            request_id,
        )
        return _json_response(
            {
                "ok": True,
                "message": "Sponsor lead accepted.",
                "notify_email": service.get_sponsor_contact_email(),
                "lead": {},
                "request_id": request_id,
            }
        )

    try:
        result = service.create_lead_response(payload)
        result["request_id"] = request_id

        if result.get("ok"):
            # FutureFunded: persist accepted sponsor lead for dashboard queue.
            try:
                from apps.web.app.services.sponsor_lead_repository import record_sponsor_lead

                _ff_repo_campaign_slug = (
                    request.form.get('campaign_slug')
                    or request.form.get('slug')
                    or request.args.get('campaign_slug')
                    or request.args.get('slug')
                    or DEFAULT_CAMPAIGN_SLUG
                )
                request.environ['futurefunded.sponsor_lead_record'] = record_sponsor_lead(
                    request.form,
                    package_metadata=request.environ.get('futurefunded.sponsor_package_metadata', {}),
                    operator_payload=request.environ.get('futurefunded.sponsor_operator_payload', {}),
                    confirmation_payload=request.environ.get('futurefunded.sponsor_confirmation_payload', {}),
                    operator_notification=request.environ.get('futurefunded.sponsor_operator_notification', {}),
                    confirmation_notification=request.environ.get('futurefunded.sponsor_confirmation_notification', {}),
                    campaign_slug=_ff_repo_campaign_slug,
                )
            except Exception:
                current_app.logger.exception('Sponsor lead repository write failed')
                request.environ['futurefunded.sponsor_lead_record'] = {}

            current_app.logger.info(
                "Sponsor lead accepted | business=%s | campaign=%s | request_id=%s",
                payload.get("business_name", ""),
                payload.get("campaign_slug", ""),
                request_id,
            )
            return _json_response(result, status=200)

        current_app.logger.info(
            "Sponsor lead validation failed | campaign=%s | request_id=%s",
            payload.get("campaign_slug", ""),
            request_id,
        )
        return _json_response(result, status=400)
    except Exception:
        current_app.logger.exception(
            "Sponsor lead submission failed | campaign=%s | request_id=%s",
            payload.get("campaign_slug", ""),
            request_id,
        )
        return _json_response(
            {
                "ok": False,
                "message": "Sponsor lead submission failed.",
                "request_id": request_id,
            },
            status=500,
        )


@sponsors_bp.post("/lead/<lead_id>/stage")
@sponsors_bp.post("/lead/<lead_id>/stage/")
def sponsor_lead_stage_update(lead_id: str):
    """Update sponsor lead stage from dashboard operator controls."""

    import os

    from flask import jsonify, redirect, request

    expected_token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    auth_header = request.headers.get("Authorization", "").strip()
    bearer_token = ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()

    supplied_token = (
        request.form.get("token")
        or request.args.get("token")
        or request.args.get("operator_token")
        or request.headers.get("X-Operator-Token")
        or bearer_token
        or ""
    ).strip()

    if not expected_token or supplied_token != expected_token:
        return jsonify({"ok": False, "error": "Unauthorized sponsor queue update."}), 403

    stage = request.form.get("stage") or ""
    campaign_slug = (
        request.form.get("campaign_slug")
        or request.args.get("campaign_slug")
        or request.args.get("slug")
        or DEFAULT_CAMPAIGN_SLUG
    )

    try:
        from apps.web.app.services.sponsor_lead_repository import update_sponsor_lead_stage

        updated = update_sponsor_lead_stage(
            lead_id,
            stage,
            campaign_slug=campaign_slug,
        )
    except Exception:
        current_app.logger.exception("Sponsor lead stage update failed")
        updated = None

    if not updated:
        return jsonify({"ok": False, "error": "Sponsor lead not found."}), 404

    current_app.logger.info(
        "Sponsor lead stage updated | id=%s | stage=%s | campaign=%s",
        lead_id,
        updated.get("stage"),
        campaign_slug,
    )

    next_url = request.form.get("next") or request.referrer
    if next_url and "text/html" in request.headers.get("Accept", ""):
        return redirect(next_url)

    return jsonify({"ok": True, "lead": updated}), 200
