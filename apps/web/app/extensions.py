from __future__ import annotations

from typing import Any
from pathlib import Path
from uuid import uuid4

from flask import Flask, g, has_app_context, request
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from werkzeug.middleware.proxy_fix import ProxyFix

engine: Engine | None = None
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
)


def init_extensions(app: Flask) -> None:
    register_proxy_fix(app)
    init_db(app)
    register_request_context(app)
    register_security_headers(app)
    register_template_helpers(app)
    register_teardown_hooks(app)
    register_shell_context(app)


def register_proxy_fix(app: Flask) -> None:
    if not app.config.get("TRUST_PROXY_HEADERS", False):
        return

    app.wsgi_app = ProxyFix(  # type: ignore[assignment]
        app.wsgi_app,
        x_for=int(app.config.get("PROXY_FIX_X_FOR", 1)),
        x_proto=int(app.config.get("PROXY_FIX_X_PROTO", 1)),
        x_host=int(app.config.get("PROXY_FIX_X_HOST", 1)),
        x_port=int(app.config.get("PROXY_FIX_X_PORT", 1)),
        x_prefix=int(app.config.get("PROXY_FIX_X_PREFIX", 1)),
    )


def _engine_options(app: Flask) -> dict[str, Any]:
    database_url = str(app.config.get("DATABASE_URL", "")).strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured for FutureFunded.")

    options: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["pool_size"] = int(app.config.get("DB_POOL_SIZE", 5))
        options["max_overflow"] = int(app.config.get("DB_MAX_OVERFLOW", 10))
        options["pool_timeout"] = int(app.config.get("DB_POOL_TIMEOUT", 30))
        options["pool_recycle"] = int(app.config.get("DB_POOL_RECYCLE", 1800))

    return options



def _ensure_sqlite_database_path(database_url: str) -> None:
    """Create parent directories for file-backed SQLite DATABASE_URL values."""
    try:
        url = make_url(database_url)
    except Exception:
        return

    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        return

    database = str(url.database or "").strip()
    if not database or database == ":memory:":
        return

    db_path = Path(database).expanduser()
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

def init_db(app: Flask) -> None:
    global engine

    database_url = str(app.config.get("DATABASE_URL", "")).strip()
    _ensure_sqlite_database_path(database_url)

    engine = create_engine(database_url, **_engine_options(app))
    SessionLocal.configure(bind=engine)

    app.extensions["db"] = {
        "engine": engine,
        "session_factory": SessionLocal,
    }


def get_db_session() -> Session:
    if not has_app_context():
        raise RuntimeError("Database session requested outside application context.")

    global engine

    # Defensive bind repair:
    # In tests, reloads, or partial app boot paths, the scoped session can exist
    # before SessionLocal has an active bind. Rebind from current_app config.
    if engine is None:
        from flask import current_app

        init_db(current_app)

    session = getattr(g, "_ff_db_session", None)
    if session is None:
        session = SessionLocal()
        g._ff_db_session = session

    try:
        session.get_bind()
    except Exception:
        from flask import current_app

        init_db(current_app)
        SessionLocal.remove()
        session = SessionLocal()
        g._ff_db_session = session

    return session


def register_request_context(app: Flask) -> None:
    @app.before_request
    def attach_request_context() -> None:
        g.request_id = request.headers.get("X-Request-Id", uuid4().hex)
        g.request_started = True


def register_security_headers(app: Flask) -> None:
    if not app.config.get("ENABLE_SECURITY_HEADERS", True):
        return

    @app.after_request
    def set_security_headers(response):  # type: ignore[no-untyped-def]
        response.headers.setdefault(
            "X-Content-Type-Options", app.config.get("X_CONTENT_TYPE_OPTIONS", "nosniff")
        )
        response.headers.setdefault(
            "X-Frame-Options", app.config.get("X_FRAME_OPTIONS", "SAMEORIGIN")
        )
        response.headers.setdefault(
            "Referrer-Policy", app.config.get("REFERRER_POLICY", "strict-origin-when-cross-origin")
        )
        response.headers.setdefault(
            "Permissions-Policy",
            app.config.get("PERMISSIONS_POLICY", "accelerometer=(), camera=(), microphone=()"),
        )
        response.headers.setdefault("X-Request-Id", getattr(g, "request_id", uuid4().hex))

        if app.config.get("ENABLE_CSP", True):
            response.headers.setdefault(
                "Content-Security-Policy", app.config.get("CONTENT_SECURITY_POLICY", "")
            )

        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        if response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "no-store, max-age=0")

        return response


def register_teardown_hooks(app: Flask) -> None:
    @app.teardown_appcontext
    def shutdown_session(_exception: BaseException | None = None) -> None:
        session = getattr(g, "_ff_db_session", None)
        if session is not None:
            session.close()
            g._ff_db_session = None
        SessionLocal.remove()


def register_template_helpers(app: Flask) -> None:
    @app.context_processor
    def inject_extension_context() -> dict[str, Any]:
        return {
            "db_session": get_db_session,
            "theme_color": app.config.get("THEME_COLOR", "#f97316"),
            "theme_color_dark": app.config.get("THEME_COLOR_DARK", "#0b0f17"),
            "support_email": app.config.get("SUPPORT_EMAIL", "support@getfuturefunded.com"),
            "sponsor_contact_email": app.config.get(
                "SPONSOR_CONTACT_EMAIL", "sponsors@getfuturefunded.com"
            ),
            "public_base_url": app.config.get("PUBLIC_BASE_URL", ""),
            "api_base_url": app.config.get("API_BASE_URL", ""),
            "request_id": getattr(g, "request_id", None),
        }


def register_shell_context(app: Flask) -> None:
    @app.shell_context_processor
    def shell_context() -> dict[str, Any]:
        return {
            "app": app,
            "engine": engine,
            "db_session": get_db_session,
            "SessionLocal": SessionLocal,
        }
