from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
from typing import Any

from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, has_request_context, jsonify, redirect, request, url_for

from .config import Config
from .extensions import init_extensions


def _ff_strip_loopback_from_csp_header(csp_value: str | None) -> str | None:
    """Remove localhost/loopback origins from CSP in production responses."""
    if not csp_value:
        return csp_value

    import re as _re

    cleaned_directives: list[str] = []
    loopback = _re.compile(r"^https?://(?:127\.0\.0\.1|localhost)(?::\d+)?/?$", _re.I)

    for raw_directive in csp_value.split(";"):
        directive = raw_directive.strip()
        if not directive:
            continue

        parts = directive.split()
        name = parts[0].lower()

        if name in {
            "connect-src",
            "script-src",
            "frame-src",
            "form-action",
            "img-src",
            "style-src",
            "font-src",
        }:
            kept = [parts[0]] + [part for part in parts[1:] if not loopback.match(part)]
            if len(kept) == 1 and name == "connect-src":
                kept.append("'self'")
            directive = " ".join(kept)

        cleaned_directives.append(directive)

    return "; ".join(cleaned_directives) + ";"


def create_app(config_object: type[Config] | str | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="static",
        template_folder="templates",
    )

    # Trust Cloudflare/cloudflared proxy headers for external URL generation.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    app.config.setdefault("PREFERRED_URL_SCHEME", "https")
    try:
        from apps.web.app.services.platform_context import register_platform_identity_context

        register_platform_identity_context(app)
    except Exception:
        pass

    # FutureFunded launch hardening: never expose localhost origins in public CSP.
    @app.after_request
    def _ff_prod_csp_no_loopback(response):
        from flask import request as _ff_request

        _ff_host = (_ff_request.host or "").lower()
        _ff_is_public = "getfuturefunded.com" in _ff_host or not app.debug

        if _ff_is_public:
            _ff_csp = response.headers.get("Content-Security-Policy")
            if _ff_csp:
                response.headers["Content-Security-Policy"] = _ff_strip_loopback_from_csp_header(
                    _ff_csp
                )

        return response

    _ensure_instance_path(app)
    resolved_config = _load_config(app, config_object)
    _validate_runtime(resolved_config)
    _configure_logging(app)
    _configure_runtime_defaults(app)
    _register_context_processors(app)
    init_extensions(app)
    _register_blueprints(app)
    _register_core_routes(app)
    _register_error_handlers(app)
    _log_startup_banner(app)

    # Jinja helper: safe CSP nonce attribute for inline/script/style tags.
    # Templates may call {{ nonce_attr() }}. If Flask-Talisman or another CSP
    # integration provides csp_nonce(), this emits nonce="..."; otherwise it
    # safely emits an empty string instead of crashing the campaign page.
    from markupsafe import Markup, escape

    def _ff_nonce_attr() -> Markup:
        csp_nonce = app.jinja_env.globals.get("csp_nonce")
        if callable(csp_nonce):
            try:
                nonce = csp_nonce()
                if nonce:
                    return Markup(f'nonce="{escape(nonce)}"')
            except Exception:
                pass
        return Markup("")

    app.jinja_env.globals.setdefault("nonce_attr", _ff_nonce_attr)

    # FutureFunded launch safety:
    # Verify Stripe signature, then ACK non-revenue lifecycle events before ledger logic.
    @app.before_request
    def _ff_ack_only_stripe_webhook_events():
        from flask import current_app, jsonify, request

        if request.path != "/c/stripe/webhook" or request.method != "POST":
            return None

        secret = (
            current_app.config.get("STRIPE_WEBHOOK_SECRET")
            or current_app.config.get("FF_STRIPE_WEBHOOK_SECRET")
            or current_app.config.get("STRIPE_WEBHOOK_SIGNING_SECRET")
            or os.getenv("STRIPE_WEBHOOK_SECRET")
            or os.getenv("FF_STRIPE_WEBHOOK_SECRET")
            or os.getenv("STRIPE_WEBHOOK_SIGNING_SECRET")
        )

        if not secret:
            return None

        sig_header = request.headers.get("Stripe-Signature", "")
        if not sig_header:
            return None

        try:
            import stripe

            payload = request.get_data(cache=True)
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        except Exception:
            return None

        event_type = (
            event.get("type", "") if isinstance(event, dict) else getattr(event, "type", "")
        )

        if event_type in {"checkout.session.expired", "payment_intent.created", "charge.updated"}:
            current_app.logger.info(
                "FutureFunded Stripe ACK-only event | type=%s",
                event_type,
            )
            return (
                jsonify(
                    {
                        "ok": True,
                        "received": True,
                        "ignored": True,
                        "type": event_type,
                    }
                ),
                200,
            )

        return None




    # FutureFunded asset cache authority.
    # Keeps clean URLs using fresh static fingerprints.
    try:
        from .ff_asset_versioning import register_ff_asset_versioning
        register_ff_asset_versioning(app)
    except Exception as exc:
        app.logger.warning("FutureFunded asset versioning was not registered: %s", exc)


    # FF_WAVE3_DASHBOARD_LOCKED_STATE_V1_START
    @app.errorhandler(403)
    def _ff_dashboard_locked_state(error):
        from flask import render_template, request

        if request.path.rstrip("/") == "/platform/dashboard":

            # FF_WAVE10C_DASHBOARD_SPONSOR_REVIEW_QUEUE_START
            def _ff_dashboard_sponsor_review_queue(limit=8):
                try:
                    from pathlib import Path as _Path
                    import json as _json

                    queue_dir = _Path(app.instance_path) / "sponsor-review-queue"
                    if not queue_dir.exists():
                        return []

                    items = []
                    paths = sorted(
                        queue_dir.glob("*.json"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )

                    for path in paths[:limit]:
                        try:
                            data = _json.loads(path.read_text(encoding="utf-8"))
                        except Exception:
                            continue

                        sponsor = data.get("sponsor") or {}
                        review = data.get("review") or {}

                        items.append({
                            "session_id": data.get("session_id", path.stem),
                            "campaign_slug": data.get("campaign_slug", "connect-atx-elite"),
                            "status": data.get("status", "checkout_created"),
                            "created_at": data.get("created_at", ""),
                            "sponsor": {
                                "business_name": sponsor.get("business_name", ""),
                                "contact_email": sponsor.get("contact_email", ""),
                                "recognition_name": sponsor.get("recognition_name", ""),
                                "website": sponsor.get("website", ""),
                                "package": sponsor.get("package", ""),
                                "package_label": sponsor.get("package_label", ""),
                                "package_amount": sponsor.get("package_amount", ""),
                                "package_amount_cents": sponsor.get("package_amount_cents", ""),
                                "recognition_note": sponsor.get("recognition_note", ""),
                            },
                            "review": {
                                "review_required": bool(review.get("review_required", True)),
                                "public_recognition_allowed": bool(review.get("public_recognition_allowed", False)),
                                "review_state": review.get("review_state", "pending_payment_or_review"),
                            },
                        })

                    return items
                except Exception:
                    try:
                        app.logger.exception("FutureFunded dashboard sponsor review queue load failed")
                    except Exception:
                        pass
                    return []
            # FF_WAVE10C_DASHBOARD_SPONSOR_REVIEW_QUEUE_END
            return render_template(
                "platform/dashboard_locked.html",
                asset_v=app.config.get("ASSET_V", "wave3-dashboard-locked"),
                sponsor_review_queue=_ff_dashboard_sponsor_review_queue(),
            ), 403

        return "Forbidden", 403
    # FF_WAVE3_DASHBOARD_LOCKED_STATE_V1_END



    # FF_WAVE10C_DASHBOARD_REVIEW_QUEUE_CONTEXT_V2_START
    def _ff_wave10c_load_sponsor_review_queue(limit=8):
        try:
            from pathlib import Path as _Path
            import json as _json

            queue_dir = _Path(app.instance_path) / "sponsor-review-queue"
            if not queue_dir.exists():
                return []

            items = []
            paths = sorted(
                queue_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for path in paths[:limit]:
                try:
                    data = _json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue

                sponsor = data.get("sponsor") or {}
                review = data.get("review") or {}

                items.append({
                    "session_id": data.get("session_id", path.stem),
                    "campaign_slug": data.get("campaign_slug", "connect-atx-elite"),
                    "status": data.get("status", "checkout_created"),
                    "created_at": data.get("created_at", ""),
                    "sponsor": {
                        "business_name": sponsor.get("business_name", ""),
                        "contact_email": sponsor.get("contact_email", ""),
                        "recognition_name": sponsor.get("recognition_name", ""),
                        "website": sponsor.get("website", ""),
                        "package": sponsor.get("package", ""),
                        "package_label": sponsor.get("package_label", ""),
                        "package_amount": sponsor.get("package_amount", ""),
                        "package_amount_cents": sponsor.get("package_amount_cents", ""),
                        "recognition_note": sponsor.get("recognition_note", ""),
                    },
                    "review": {
                        "review_required": bool(review.get("review_required", True)),
                        "public_recognition_allowed": bool(review.get("public_recognition_allowed", False)),
                        "review_state": review.get("review_state", "pending_payment_or_review"),
                    },
                })

            return items
        except Exception:
            try:
                app.logger.exception("FutureFunded sponsor review queue context load failed")
            except Exception:
                pass
            return []

    @app.context_processor
    def _ff_wave10c_dashboard_review_queue_context():
        return {
            "ff_sponsor_review_queue": _ff_wave10c_load_sponsor_review_queue(),
        }
    # FF_WAVE10C_DASHBOARD_REVIEW_QUEUE_CONTEXT_V2_END


    # FF_WAVE10C_DASHBOARD_REVIEW_QUEUE_CONTEXT_V3_START
    @app.context_processor
    def _ff_wave10c_global_dashboard_review_queue_context():
        try:
            from pathlib import Path as _Path
            import json as _json

            queue_dir = _Path(app.instance_path) / "sponsor-review-queue"
            items = []
            if queue_dir.exists():
                paths = sorted(queue_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                for path in paths[:8]:
                    try:
                        data = _json.loads(path.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    items.append(data)
            return {"ff_sponsor_review_queue_raw": items}
        except Exception:
            return {"ff_sponsor_review_queue_raw": []}
    # FF_WAVE10C_DASHBOARD_REVIEW_QUEUE_CONTEXT_V3_END


    # FF_ROOT_PLATFORM_HOME_V1_START
    # Public root intentionally opens the SaaS platform surface.
    # Keep the flagship campaign demo at /c/connect-atx-elite.
    @app.before_request
    def _ff_root_platform_home_v1():
        from flask import redirect, request

        if request.path == "/" and request.method in {"GET", "HEAD"}:
            return redirect("/platform/", code=302)

        return None
    # FF_ROOT_PLATFORM_HOME_V1_END


    # FF_NATIVE_SMS_BLUEPRINT_V1_START
    # Native FutureFunded SMS/Text-to-Donate webhook.
    try:
        from .routes.sms import sms_bp as _ff_sms_bp
        app.register_blueprint(_ff_sms_bp)
    except Exception as exc:
        app.logger.warning("FutureFunded SMS blueprint not registered: %s", exc)
    # FF_NATIVE_SMS_BLUEPRINT_V1_END






    # === FutureFunded hoi-console-hygiene-csp-final-header-v3 START ===
    # Final outgoing CSP patch for fixed inline snippets detected by the
    # console hygiene gate. This patches the WSGI response header after any
    # Flask/Talisman/header middleware has produced the CSP.
    def _ff_patch_final_csp_header_for_known_inline_hashes(value):
        # Marker: hoi-phase3c-csp-known-inline-hashes-v1
        script_hashes = (
            "'sha256-xNlbosNiX81JFLnBe9S2TlVb59AzMgNhddzmmzwPkv8='",
            "'sha256-0A2AULUYoZH+oYvGufGDVF/50/7IdAfj6aGDdRSGpTU='",
            "'sha256-2W+1Kis6Ki2XpUlKbh9DMHtaYzFjW29XuADc6CbQRRk='",
            "'sha256-odo5rg5eVzJLNl0FdzjpdnVCzDJ/q42tGM2wsT98CmQ='",
        )
        style_hash = "'sha256-t0esl956mDzVzwKc5pfR4KE32BvFdoRCmvPWLBktoqM='"
        unsafe_hashes = "'unsafe-hashes'"

        if not value:
            return value

        patched_parts = []

        for raw_part in str(value).split(";"):
            part = raw_part.strip()

            if not part:
                continue

            tokens = part.split()
            directive = tokens[0] if tokens else ""

            if directive == "script-src":
                for script_hash in script_hashes:
                    if script_hash not in tokens:
                        tokens.append(script_hash)

            if directive == "style-src":
                if unsafe_hashes not in tokens:
                    tokens.append(unsafe_hashes)
                if style_hash not in tokens:
                    tokens.append(style_hash)

            patched_parts.append(" ".join(tokens))

        return "; ".join(patched_parts)

    _ff_original_wsgi_app_for_final_csp = app.wsgi_app

    def _ff_console_hygiene_final_csp_wsgi_app(environ, start_response):
        def _ff_start_response(status, headers, exc_info=None):
            patched_headers = []

            for name, value in headers:
                if str(name).lower() == "content-security-policy":
                    value = _ff_patch_final_csp_header_for_known_inline_hashes(value)

                patched_headers.append((name, value))

            return start_response(status, patched_headers, exc_info)

        return _ff_original_wsgi_app_for_final_csp(environ, _ff_start_response)

    app.wsgi_app = _ff_console_hygiene_final_csp_wsgi_app
    # === FutureFunded hoi-console-hygiene-csp-final-header-v3 END ===

    return app
def _ensure_instance_path(app: Flask) -> None:
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)


def _load_config(app, config_object=None):
    """
    Deterministic config loader.
    Avoids import_string issues entirely.
    """

    from apps.web.app.config import Config

    app.config.from_object(Config)

    return Config

    resolved = str(app or "").replace(":", ".")

    module_name, _, attr_name = resolved.rpartition(".")
    if not module_name or not attr_name:
        return resolved

    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def _validate_runtime(config_object: Any) -> None:
    validator = getattr(config_object, "validate_runtime", None)
    if callable(validator):
        validator()


def _configure_logging(app: Flask) -> None:
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
        )
        app.logger.addHandler(handler)

    app.logger.setLevel(level)
    app.logger.propagate = False


def _configure_runtime_defaults(app: Flask) -> None:
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", bool(app.debug))
    app.config.setdefault("SEND_FILE_MAX_AGE_DEFAULT", 3600)
    app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    app.config.setdefault("JSON_SORT_KEYS", False)
    app.config.setdefault(
        "PREFERRED_URL_SCHEME",
        "https" if app.config.get("IS_PRODUCTION", False) else "http",
    )


def _register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_global_template_context() -> dict[str, Any]:
        public_base_url = str(app.config.get("PUBLIC_BASE_URL", "")).rstrip("/")

        if not public_base_url and has_request_context():
            public_base_url = request.url_root.rstrip("/")

        return {
            "asset_v": app.config.get("ASSET_V", "1"),
            "brand_name": app.config.get("BRAND_NAME", "FutureFunded"),
            "support_email": app.config.get("SUPPORT_EMAIL", "support@getfuturefunded.com"),
            "sponsor_contact_email": app.config.get(
                "SPONSOR_CONTACT_EMAIL",
                app.config.get("SUPPORT_EMAIL", "support@getfuturefunded.com"),
            ),
            "platform_logo": app.config.get("PLATFORM_LOGO", ""),
            "theme": app.config.get("DEFAULT_THEME", "light"),
            "density": app.config.get("DEFAULT_DENSITY", "compact"),
            "ff_public_base_url": public_base_url,
            "ff_api_base_url": app.config.get("API_BASE_URL", "").rstrip("/"),
            "ff_env": app.config.get("ENV", "development"),
            "ff_demo_mode": app.config.get("DEMO_MODE", "preview"),
        }


def _register_blueprints(app: Flask) -> None:
    from .blueprints.campaign.routes import campaign_bp
    from .blueprints.legal.routes import legal_bp
    from .blueprints.platform.routes import platform_bp
    from .blueprints.sponsors.routes import sponsors_bp

    for blueprint in (platform_bp, campaign_bp, sponsors_bp, legal_bp):
        _safe_register(app, blueprint)


def _safe_register(app: Flask, blueprint: Any) -> None:
    if blueprint.name in app.blueprints:
        app.logger.debug("Blueprint '%s' already registered. Skipping.", blueprint.name)
        return

    app.register_blueprint(blueprint)


def _register_core_routes(app: Flask) -> None:
    @app.get("/")
    def home():
        if "platform.index" in app.view_functions:
            return redirect(url_for("platform.index"), code=302)
        return redirect("/platform", code=302)

    @app.get("/healthz")
    def healthz():
        response = jsonify(
            {
                "ok": True,
                "service": "futurefunded-web",
                "env": app.config.get("ENV", "development"),
                "app_name": app.config.get("APP_NAME", "FutureFunded"),
            }
        )
        response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return (
            """
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Not Found • FutureFunded</title>
              </head>
              <body style="font-family: Inter, system-ui, sans-serif; padding: 2rem;">
                <h1>Page not found</h1>
                <p>The page you requested could not be found.</p>
              </body>
            </html>
            """,
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled application error: %s", error)
        return (
            """
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Server Error • FutureFunded</title>
              </head>
              <body style="font-family: Inter, system-ui, sans-serif; padding: 2rem;">
                <h1>Something went wrong</h1>
                <p>Please try again in a moment.</p>
              </body>
            </html>
            """,
            500,
        )


def _log_startup_banner(app: Flask) -> None:
    app.logger.info(
        "FutureFunded booted | env=%s | public=%s | api=%s | instance=%s",
        app.config.get("ENV", "development"),
        app.config.get("PUBLIC_BASE_URL", ""),
        app.config.get("API_BASE_URL", ""),
        app.instance_path,
    )
