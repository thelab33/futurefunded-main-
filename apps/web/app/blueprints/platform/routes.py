from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from .presenters import build_platform_presenter
from apps.web.app.services.operator_notifications import record_operator_notification
from .setup_repository import (
    SETUP_STATUS_LABELS,
    CampaignSetupRepository,
    campaign_setup_to_form_payload,
    normalize_onboarding_payload,
    normalize_setup_status,
)

platform_bp = Blueprint("platform", __name__)

DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_SLUG
DEFAULT_PLATFORM_ASSET_V = "platform-ops-single-css-v3"
DEFAULT_LOGIN_ASSET_V = "platform-login-single-css-v2"


# ---------------------------------------------------------------------------
# Shared response/context helpers
# ---------------------------------------------------------------------------


def _request_id() -> str | None:
    return getattr(g, "request_id", None)


def _html_response(
    template_name: str,
    context: dict[str, Any],
    *,
    cache_control: str,
    robots: str | None = None,
):
    response = make_response(render_template(template_name, **context))
    response.headers["Cache-Control"] = cache_control

    if robots:
        response.headers["X-Robots-Tag"] = robots

    request_id = _request_id()
    if request_id:
        response.headers["X-Request-Id"] = request_id

    return response


def _presenter():
    return build_platform_presenter(current_app.config)


def _platform_asset_version(default: str = DEFAULT_PLATFORM_ASSET_V) -> str:
    """Return platform asset version, honoring ?css_v= for local/demo cache busting."""
    requested = (request.args.get("css_v") or "").strip()
    if requested:
        return requested

    configured = (
        current_app.config.get("FF_PLATFORM_CSS_REV")
        or current_app.config.get("ASSET_V")
        or default
    )
    return str(configured or default).strip() or default


def _with_platform_asset_context(
    context: dict[str, Any] | None = None,
    *,
    default: str = DEFAULT_PLATFORM_ASSET_V,
) -> dict[str, Any]:
    next_context = dict(context or {})
    asset_v = _platform_asset_version(default)
    next_context["asset_v"] = asset_v
    next_context["platform_css_rev"] = asset_v
    return next_context


def _safe_next_url(default: str = "/platform/dashboard") -> str:
    """Keep redirects local and predictable."""
    candidate = (request.args.get("next") or request.form.get("next") or "").strip()
    if not candidate:
      return default

    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate

    return default


def _operator_query_from_token(token: str | None = None) -> str:
    safe_token = (token or _ff_platform_operator_token() or "").strip()
    if not safe_token:
        return ""

    from urllib.parse import urlencode

    return "?" + urlencode({"operator_token": safe_token})


# ---------------------------------------------------------------------------
# FutureFunded organizer account auth
# Lightweight first-party organizer login for platform/dashboard access.
# Token guard remains available for staging/internal fallback.
# ---------------------------------------------------------------------------


def _ff_operator_auth_db_path() -> Path:
    configured = current_app.config.get("FF_OPERATOR_AUTH_DATABASE_PATH") or os.getenv(
        "FF_OPERATOR_AUTH_DATABASE_PATH",
        "",
    )

    if configured:
        return Path(configured)

    instance_path = Path(current_app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "ff_operator_auth.sqlite3"


def _ff_operator_auth_conn() -> sqlite3.Connection:
    db_path = _ff_operator_auth_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ff_operator_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'organizer',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        )
        """
    )

    conn.commit()
    return conn


def _ff_operator_session_user() -> dict[str, Any] | None:
    user_id = session.get("ff_operator_user_id")
    if not user_id:
        return None

    conn = _ff_operator_auth_conn()
    try:
        row = conn.execute(
            """
            SELECT id, email, name, role, is_active
            FROM ff_operator_users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _ff_operator_login_user(user: dict[str, Any]) -> None:
    session["ff_operator_user_id"] = int(user["id"])
    session["ff_operator_email"] = user["email"]
    session["ff_operator_role"] = user.get("role") or "organizer"
    session.permanent = True


def _ff_operator_logout_user() -> None:
    session.pop("ff_operator_user_id", None)
    session.pop("ff_operator_email", None)
    session.pop("ff_operator_role", None)


def _ff_platform_operator_token() -> str:
    """Return an operator access token supplied by query param or header.

    This is intentionally narrow: it only reads explicit operator-token
    channels and does not infer access from unrelated headers/cookies.
    """
    for key in ("operator_token", "token", "access_token", "ff_operator_token"):
        value = (request.args.get(key) or "").strip()
        if value:
            return value

    for key in (
        "X-Operator-Token",
        "X-FF-Operator-Token",
        "X-FutureFunded-Operator-Token",
    ):
        value = (request.headers.get(key) or "").strip()
        if value:
            return value

    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return ""


def _required_operator_token() -> str:
    return (
        current_app.config.get("FF_OPERATOR_ACCESS_TOKEN")
        or os.getenv("FF_OPERATOR_ACCESS_TOKEN", "")
        or ""
    ).strip()


def _ff_platform_current_user_can_operate() -> bool:
    if _ff_operator_session_user():
        return True

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


def _ff_platform_operator_access_allowed() -> bool:
    if _ff_platform_current_user_can_operate():
        return True

    required_token = _required_operator_token()
    provided_token = _ff_platform_operator_token()

    if required_token:
        return bool(provided_token and provided_token == required_token)

    return False


def _require_operator_access():
    if _ff_platform_operator_access_allowed():
        return None

    if _required_operator_token():
        abort(403)

    return redirect(url_for("platform.platform_operator_login_form", next=request.path))


@platform_bp.before_request
def _ff_platform_operator_dashboard_guard():
    """Protect operator dashboard aliases before route execution."""
    path = request.path.rstrip("/") or "/"
    protected_paths = {"/platform/dashboard", "/dashboard"}

    if path not in protected_paths:
        return None

    return _require_operator_access()


# ---------------------------------------------------------------------------
# Platform public/product surfaces
# ---------------------------------------------------------------------------


@platform_bp.get("/platform")
@platform_bp.get("/platform/")
def index():
    context = _presenter().index_context()
    return _html_response(
        "platform/index.html",
        context,
        cache_control="public, max-age=60, stale-while-revalidate=300",
    )


@platform_bp.get("/platform/onboarding")
@platform_bp.get("/platform/onboarding/")
def onboarding():
    context = _presenter().onboarding_context()
    context = _with_platform_asset_context(context)

    token = _ff_platform_operator_token()
    if token:
        context["operator_token"] = token

    campaign_slug = str(context.get("campaign_slug") or DEFAULT_CAMPAIGN_SLUG).strip() or DEFAULT_CAMPAIGN_SLUG
    setup_id = (request.args.get("setup_id") or "").strip()

    loaded_setup = None
    setup_records: list[dict[str, Any]] = []

    try:
        repo = CampaignSetupRepository()
        setup_records = repo.list_for_campaign(campaign_slug, limit=8)

        if setup_id:
            loaded_setup = repo.get(setup_id)
        elif request.args.get("latest") == "1":
            loaded_setup = repo.latest_for_campaign(campaign_slug)
    except Exception:
        current_app.logger.exception("FutureFunded onboarding setup lookup failed")

    loaded_payload = campaign_setup_to_form_payload(loaded_setup)

    context.update(
        {
            "loaded_campaign_setup": loaded_setup,
            "loaded_setup_payload": loaded_payload,
            "loaded_setup_id": (loaded_setup or {}).get("setup_id", ""),
            "setup_records": setup_records,
            "setup_records_count": len(setup_records),
        }
    )

    return _html_response(
        "platform/onboarding.html",
        context,
        cache_control="no-store, max-age=0",
        robots="noindex, nofollow",
    )



@platform_bp.post("/platform/onboarding")
@platform_bp.post("/platform/onboarding/")
def onboarding_submit():
    """Persist a FutureFunded campaign onboarding/setup submission."""
    raw_payload = request.get_json(silent=True)

    if not isinstance(raw_payload, dict):
        raw_payload = request.form.to_dict(flat=True)

    payload = normalize_onboarding_payload(
        dict(raw_payload or {}),
        default_campaign_slug=DEFAULT_CAMPAIGN_SLUG,
    )

    errors = _onboarding_payload_errors(payload)
    if errors:
        return (
            jsonify(
                {
                    "ok": False,
                    "errors": errors,
                    "message": errors[0],
                }
            ),
            422,
        )

    repo = CampaignSetupRepository()

    try:
        setup = repo.save(payload)
    except Exception as exc:
        current_app.logger.exception("FutureFunded onboarding setup save failed")
        try:
            from apps.web.app.extensions import get_db_session
            get_db_session().rollback()
        except Exception:
            pass

        body = {
            "ok": False,
            "message": "Could not save onboarding setup.",
        }

        if current_app.debug:
            body["debug_error"] = str(exc)
            body["debug_type"] = exc.__class__.__name__

        return jsonify(body), 500

    dashboard_url = "/platform/dashboard" + _operator_query_from_token()
    onboarding_url = f"/platform/onboarding?setup_id={setup['setup_id']}"

    return jsonify(
        {
            "ok": True,
            "message": "Campaign setup saved.",
            "setup": setup,
            "setup_id": setup["setup_id"],
            "campaign_slug": setup["campaign_slug"],
            "dashboard_url": dashboard_url,
            "onboarding_url": onboarding_url,
        }
    )


@platform_bp.post("/platform/setup/<setup_id>/status")
def campaign_setup_status_update(setup_id: str):
    """Update a saved campaign setup workflow status."""
    access_result = _require_operator_access()
    if access_result is not None:
        return access_result

    raw_payload = request.get_json(silent=True)

    if not isinstance(raw_payload, dict):
        raw_payload = request.form.to_dict(flat=True)

    requested_status = normalize_setup_status(raw_payload.get("status"), default="")
    if requested_status not in SETUP_STATUS_LABELS:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Choose a valid setup status.",
                    "allowed_statuses": list(SETUP_STATUS_LABELS.keys()),
                }
            ),
            422,
        )

    try:
        setup = CampaignSetupRepository().update_status(setup_id, requested_status)
    except Exception:
        current_app.logger.exception("FutureFunded setup status update failed")
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Could not update setup status.",
                }
            ),
            500,
        )

    if not setup:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": "Setup record was not found.",
                }
            ),
            404,
        )

    notification = None
    if requested_status in {"review_needed", "launch_ready", "launched", "archived"}:
        try:
            notification = record_operator_notification(
                event_type="setup_status_changed",
                event_id=f"setup_status_changed:{setup['setup_id']}:{requested_status}",
                subject=f"Campaign setup moved to {SETUP_STATUS_LABELS[requested_status]}",
                body=(
                    f"Campaign setup {setup['setup_id']} for "
                    f"{setup.get('campaign_name') or setup.get('campaign_slug')} "
                    f"was moved to {SETUP_STATUS_LABELS[requested_status]}."
                ),
                metadata={
                    "setup_id": setup["setup_id"],
                    "campaign_slug": setup.get("campaign_slug"),
                    "campaign_name": setup.get("campaign_name"),
                    "status": requested_status,
                    "status_label": SETUP_STATUS_LABELS[requested_status],
                    "readiness_score": setup.get("readiness_score"),
                    "source": "platform_setup_status_update",
                },
            )
        except Exception:
            current_app.logger.exception("FutureFunded setup status notification failed")
            notification = {"ok": False, "error": "notification_failed"}

    return jsonify(
        {
            "ok": True,
            "message": f"Setup moved to {SETUP_STATUS_LABELS[requested_status]}.",
            "setup_id": setup["setup_id"],
            "status": requested_status,
            "label": SETUP_STATUS_LABELS[requested_status],
            "setup": setup,
            "notification": notification,
        }
    )

def _dashboard_context() -> dict[str, Any]:
    presenter = _presenter()
    context = presenter.dashboard_context()

    operator_token = _ff_platform_operator_token()
    operator_user = _ff_operator_session_user()

    campaign_slug = str(context.get("campaign_slug") or DEFAULT_CAMPAIGN_SLUG).strip() or DEFAULT_CAMPAIGN_SLUG

    latest_setup = None
    setup_records: list[dict[str, Any]] = []

    try:
        repo = CampaignSetupRepository()
        latest_setup = repo.latest_for_campaign(campaign_slug)
        setup_records = repo.list_for_campaign(campaign_slug, limit=8)
    except Exception:
        current_app.logger.exception("FutureFunded dashboard setup lookup failed")

    context.update(
        {
            "operator_token": operator_token,
            "operator_user": operator_user,
            "latest_campaign_setup": latest_setup,
            "has_campaign_setup": bool(latest_setup),
            "latest_setup_id": (latest_setup or {}).get("setup_id", ""),
            "latest_setup_readiness": int((latest_setup or {}).get("readiness_score") or 0),
            "latest_setup_status": (latest_setup or {}).get("status", ""),
            "latest_setup_onboarding_url": (
                f"/platform/onboarding?setup_id={(latest_setup or {}).get('setup_id')}"
                if latest_setup
                else "/platform/onboarding"
            ),
            "setup_records": setup_records,
            "setup_records_count": len(setup_records),
        }
    )

    return _with_platform_asset_context(context)


@platform_bp.get("/platform/dashboard")
@platform_bp.get("/platform/dashboard/")
def dashboard():
    """Canonical FutureFunded operator dashboard route."""
    access_result = _require_operator_access()
    if access_result is not None:
        return access_result

    return _html_response(
        "platform/dashboard.html",
        _dashboard_context(),
        cache_control="no-store, max-age=0",
        robots="noindex, nofollow",
    )


@platform_bp.get("/dashboard")
def platform_operator_dashboard():
    """Legacy/convenience dashboard alias."""
    access_result = _require_operator_access()
    if access_result is not None:
        return access_result

    return _html_response(
        "platform/dashboard.html",
        _dashboard_context(),
        cache_control="no-store, max-age=0",
        robots="noindex, nofollow",
    )


# ---------------------------------------------------------------------------
# Login/logout
# ---------------------------------------------------------------------------


def _login_context(**overrides: Any) -> dict[str, Any]:
    context = {
        "email": "",
        "error": "",
        "next_url": _safe_next_url(),
    }
    context.update(overrides)
    return _with_platform_asset_context(context, default=DEFAULT_LOGIN_ASSET_V)


@platform_bp.get("/platform/login")
@platform_bp.get("/login")
def platform_operator_login_form():
    """Render organizer login."""
    if _ff_platform_current_user_can_operate():
        return redirect(_safe_next_url("/platform/dashboard"))

    return _html_response(
        "platform/login.html",
        _login_context(),
        cache_control="no-store, max-age=0",
        robots="noindex, nofollow",
    )


@platform_bp.post("/platform/login")
@platform_bp.post("/login")
def platform_operator_login_submit():
    """Authenticate an organizer account."""
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        return (
            _html_response(
                "platform/login.html",
                _login_context(error="Enter your email and password.", email=email),
                cache_control="no-store, max-age=0",
                robots="noindex, nofollow",
            ),
            400,
        )

    conn = _ff_operator_auth_conn()

    try:
        row = conn.execute(
            """
            SELECT id, email, name, password_hash, role, is_active
            FROM ff_operator_users
            WHERE lower(email) = lower(?)
            """,
            (email,),
        ).fetchone()

        if (
            not row
            or not row["is_active"]
            or not check_password_hash(row["password_hash"], password)
        ):
            return (
                _html_response(
                    "platform/login.html",
                    _login_context(error="Invalid email or password.", email=email),
                    cache_control="no-store, max-age=0",
                    robots="noindex, nofollow",
                ),
                401,
            )

        conn.execute(
            "UPDATE ff_operator_users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        conn.commit()

        _ff_operator_login_user(dict(row))
        return redirect(_safe_next_url("/platform/dashboard"))
    finally:
        conn.close()


@platform_bp.route("/platform/logout", methods=["GET", "POST"])
@platform_bp.route("/logout", methods=["GET", "POST"])
def platform_operator_logout():
    """End organizer session."""
    _ff_operator_logout_user()
    return redirect(url_for("platform.platform_operator_login_form"))


# ---------------------------------------------------------------------------
# Campaign media upload
# ---------------------------------------------------------------------------
# Public campaign pages DISPLAY team media.
# Protected platform/operator surfaces UPLOAD and manage media.


def _ff_media_upload_allowed() -> bool:
    """Allow an authenticated/session operator, a valid operator token, or local dev."""
    if _ff_platform_operator_access_allowed():
        return True

    return bool(current_app.debug or current_app.config.get("ENV") != "production")



def _onboarding_payload_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not payload.get("organization_name"):
        errors.append("Organization name is required.")

    if not payload.get("campaign_name"):
        errors.append("Campaign name is required.")

    if int(payload.get("goal_cents") or 0) <= 0:
        errors.append("Fundraising goal must be greater than $0.")

    email = str(payload.get("operator_email") or "").strip()
    if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
        errors.append("Operator email must be valid.")

    return errors

def _safe_campaign_slug(raw_slug: str | None) -> str:
    slug = (raw_slug or DEFAULT_CAMPAIGN_SLUG).strip()
    safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "-_").strip("-_")
    return safe_slug or DEFAULT_CAMPAIGN_SLUG


@platform_bp.post("/platform/media/upload")
def platform_media_upload():
    """Upload campaign team/program photos for the public campaign proof gallery."""
    if not _ff_media_upload_allowed():
        return jsonify({"ok": False, "error": "Operator access required."}), 403

    safe_slug = _safe_campaign_slug(request.form.get("campaign_slug"))

    files = request.files.getlist("team_photos")
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp"}

    if not files:
        return jsonify({"ok": False, "error": "No team_photos files were provided."}), 400

    upload_dir = Path(current_app.root_path) / "static" / "uploads" / "campaigns" / safe_slug
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_urls: list[str] = []
    rejected: list[str] = []

    for item in files[:8]:
        original = item.filename or ""
        filename = secure_filename(original)
        suffix = Path(filename).suffix.lower()

        if not filename or suffix not in allowed_suffixes:
            rejected.append(original or "unnamed")
            continue

        target_file = upload_dir / filename
        stem = target_file.stem
        counter = 1

        while target_file.exists():
            target_file = upload_dir / f"{stem}-{counter}{suffix}"
            counter += 1

        item.save(target_file)

        uploaded_urls.append(
            url_for(
                "static",
                filename=f"uploads/campaigns/{safe_slug}/{target_file.name}",
            )
        )

    manifest = upload_dir / "manifest.json"
    existing_urls: list[str] = []

    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("urls"), list):
                existing_urls = [str(url) for url in data["urls"]]
        except Exception:
            existing_urls = []

    merged_urls: list[str] = []
    for url in [*uploaded_urls, *existing_urls]:
        if url and url not in merged_urls:
            merged_urls.append(url)

    manifest.write_text(
        json.dumps({"slug": safe_slug, "urls": merged_urls[:12]}, indent=2),
        encoding="utf-8",
    )

    return jsonify(
        {
            "ok": True,
            "slug": safe_slug,
            "uploaded": uploaded_urls,
            "rejected": rejected,
            "campaign_url": f"/c/{safe_slug}",
        }
    )
