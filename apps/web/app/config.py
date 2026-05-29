from __future__ import annotations

import os
from datetime import timedelta
from typing import Final


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip()) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_url(value: str | None, default: str) -> str:
    safe = (value or default).strip()
    return safe.rstrip("/")


class Config:
    APP_NAME: Final[str] = os.getenv("APP_NAME", "FutureFunded").strip()
    BRAND_NAME: Final[str] = os.getenv("BRAND_NAME", "FutureFunded").strip()

    ENV: Final[str] = os.getenv("ENV", "development").strip().lower()
    DEBUG: Final[bool] = _as_bool(os.getenv("DEBUG"), default=(ENV == "development"))
    TESTING: Final[bool] = _as_bool(os.getenv("TESTING"), default=False)
    IS_PRODUCTION: Final[bool] = ENV in {"production", "prod", "live"}

    SECRET_KEY: Final[str] = os.getenv("SECRET_KEY", "dev-secret-key-change-me").strip()
    LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    PUBLIC_BASE_URL: Final[str] = _as_url(
        os.getenv("PUBLIC_BASE_URL"),
        "http://127.0.0.1:5000",
    )
    API_BASE_URL: Final[str] = _as_url(
        os.getenv("API_BASE_URL"),
        "http://127.0.0.1:8000",
    )

    SERVER_NAME: Final[str | None] = (os.getenv("SERVER_NAME") or "").strip() or None
    PREFERRED_URL_SCHEME: Final[str] = "https" if IS_PRODUCTION else "http"

    DEFAULT_THEME: Final[str] = os.getenv("DEFAULT_THEME", "light").strip().lower()
    DEFAULT_DENSITY: Final[str] = os.getenv("DEFAULT_DENSITY", "compact").strip().lower()
    THEME_COLOR: Final[str] = os.getenv("THEME_COLOR", "#f97316").strip()
    THEME_COLOR_DARK: Final[str] = os.getenv("THEME_COLOR_DARK", "#0b0f17").strip()
    ASSET_V: Final[str] = os.getenv("ASSET_V", "2").strip()
    PLATFORM_LOGO: Final[str] = os.getenv("PLATFORM_LOGO", "").strip()

    SUPPORT_EMAIL: Final[str] = os.getenv("SUPPORT_EMAIL", "support@getfuturefunded.com").strip()
    SPONSOR_CONTACT_EMAIL: Final[str] = os.getenv(
        "SPONSOR_CONTACT_EMAIL",
        os.getenv("SUPPORT_EMAIL", "support@getfuturefunded.com"),
    ).strip()

    DATABASE_URL: Final[str] = os.getenv(
        "DATABASE_URL",
        "sqlite:////home/elCUCO/futurefunded-final/.data/futurefunded-dev.db",
    ).strip()
    DB_POOL_SIZE: Final[int] = _as_int(os.getenv("DB_POOL_SIZE"), 5)
    DB_MAX_OVERFLOW: Final[int] = _as_int(os.getenv("DB_MAX_OVERFLOW"), 10)
    DB_POOL_TIMEOUT: Final[int] = _as_int(os.getenv("DB_POOL_TIMEOUT"), 30)
    DB_POOL_RECYCLE: Final[int] = _as_int(os.getenv("DB_POOL_RECYCLE"), 1800)

    STRIPE_PUBLISHABLE_KEY: Final[str] = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    STRIPE_SECRET_KEY: Final[str] = os.getenv("STRIPE_SECRET_KEY", "").strip()
    STRIPE_WEBHOOK_SECRET: Final[str] = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    STRIPE_CURRENCY: Final[str] = os.getenv("STRIPE_CURRENCY", "USD").strip().upper()
    STRIPE_LIVE_MODE: Final[bool] = _as_bool(os.getenv("STRIPE_LIVE_MODE"), default=False)
    STRIPE_ENFORCE_LIVE_KEYS: Final[bool] = _as_bool(
        os.getenv("STRIPE_ENFORCE_LIVE_KEYS"),
        default=IS_PRODUCTION,
    )

    PAYPAL_CLIENT_ID: Final[str] = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    PAYPAL_CLIENT_SECRET: Final[str] = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    PAYPAL_WEBHOOK_ID: Final[str] = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    PAYPAL_ENV: Final[str] = os.getenv("PAYPAL_ENV", "sandbox").strip().lower()
    PAYPAL_CURRENCY: Final[str] = os.getenv("PAYPAL_CURRENCY", "USD").strip().upper()

    ENABLE_ANALYTICS: Final[bool] = _as_bool(os.getenv("ENABLE_ANALYTICS"), default=True)
    ENABLE_EMAILS: Final[bool] = _as_bool(os.getenv("ENABLE_EMAILS"), default=False)
    ENABLE_STRIPE: Final[bool] = _as_bool(
        os.getenv("ENABLE_STRIPE"),
        default=bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY),
    )
    ENABLE_PAYPAL: Final[bool] = _as_bool(
        os.getenv("ENABLE_PAYPAL"),
        default=bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET),
    )

    MAX_CONTENT_LENGTH: Final[int] = _as_int(os.getenv("MAX_CONTENT_LENGTH"), 16 * 1024 * 1024)
    SEND_FILE_MAX_AGE_DEFAULT: Final[int] = _as_int(os.getenv("SEND_FILE_MAX_AGE_DEFAULT"), 3600)

    SESSION_COOKIE_NAME: Final[str] = os.getenv(
        "SESSION_COOKIE_NAME", "futurefunded_session"
    ).strip()
    SESSION_COOKIE_HTTPONLY: Final[bool] = True
    SESSION_COOKIE_SAMESITE: Final[str] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax").strip()
    SESSION_COOKIE_SECURE: Final[bool] = _as_bool(
        os.getenv("SESSION_COOKIE_SECURE"),
        default=IS_PRODUCTION,
    )
    SESSION_REFRESH_EACH_REQUEST: Final[bool] = True
    PERMANENT_SESSION_LIFETIME: Final[timedelta] = timedelta(
        seconds=_as_int(os.getenv("PERMANENT_SESSION_LIFETIME_SECONDS"), 60 * 60 * 24 * 7)
    )

    JSON_SORT_KEYS: Final[bool] = False
    JSONIFY_PRETTYPRINT_REGULAR: Final[bool] = False

    TRUST_PROXY_HEADERS: Final[bool] = _as_bool(
        os.getenv("TRUST_PROXY_HEADERS"), default=IS_PRODUCTION
    )
    PROXY_FIX_X_FOR: Final[int] = _as_int(os.getenv("PROXY_FIX_X_FOR"), 1)
    PROXY_FIX_X_PROTO: Final[int] = _as_int(os.getenv("PROXY_FIX_X_PROTO"), 1)
    PROXY_FIX_X_HOST: Final[int] = _as_int(os.getenv("PROXY_FIX_X_HOST"), 1)
    PROXY_FIX_X_PORT: Final[int] = _as_int(os.getenv("PROXY_FIX_X_PORT"), 1)
    PROXY_FIX_X_PREFIX: Final[int] = _as_int(os.getenv("PROXY_FIX_X_PREFIX"), 1)

    ENABLE_SECURITY_HEADERS: Final[bool] = _as_bool(
        os.getenv("ENABLE_SECURITY_HEADERS"), default=True
    )
    ENABLE_CSP: Final[bool] = _as_bool(os.getenv("ENABLE_CSP"), default=True)
    REFERRER_POLICY: Final[str] = os.getenv(
        "REFERRER_POLICY", "strict-origin-when-cross-origin"
    ).strip()
    X_FRAME_OPTIONS: Final[str] = os.getenv("X_FRAME_OPTIONS", "SAMEORIGIN").strip()
    X_CONTENT_TYPE_OPTIONS: Final[str] = "nosniff"
    PERMISSIONS_POLICY: Final[str] = os.getenv(
        "PERMISSIONS_POLICY",
        "accelerometer=(), autoplay=(self), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(self), usb=()",
    ).strip()

    CONTENT_SECURITY_POLICY: Final[str] = os.getenv(
        "CONTENT_SECURITY_POLICY",
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' https:; "
        "font-src 'self' data: https:; "
        "script-src 'self' https://js.stripe.com https://www.paypal.com https://*.paypal.com https://static.cloudflareinsights.com; "
        f"connect-src 'self' {API_BASE_URL} https://api.stripe.com https://www.paypal.com https://*.paypal.com; "
        "frame-src 'self' https://js.stripe.com https://hooks.stripe.com https://www.paypal.com https://*.paypal.com https://www.youtube.com https://player.vimeo.com; "
        "form-action 'self' https://checkout.stripe.com https://www.paypal.com https://*.paypal.com;",
    ).strip()

    RATE_LIMIT_SPONSOR_PER_MINUTE: Final[int] = _as_int(
        os.getenv("RATE_LIMIT_SPONSOR_PER_MINUTE"), 10
    )
    RATE_LIMIT_ONBOARDING_PER_MINUTE: Final[int] = _as_int(
        os.getenv("RATE_LIMIT_ONBOARDING_PER_MINUTE"), 10
    )
    RATE_LIMIT_PAYMENT_PER_MINUTE: Final[int] = _as_int(
        os.getenv("RATE_LIMIT_PAYMENT_PER_MINUTE"), 20
    )

    DEMO_MODE: Final[str] = os.getenv("DEMO_MODE", "preview").strip().lower()

    @classmethod
    def validate_runtime(cls) -> None:
        if cls.IS_PRODUCTION and cls.SECRET_KEY == "dev-secret-key-change-me":
            raise RuntimeError("SECRET_KEY must be changed for production.")

        if cls.STRIPE_ENFORCE_LIVE_KEYS and cls.IS_PRODUCTION and cls.ENABLE_STRIPE:
            if cls.STRIPE_SECRET_KEY and not cls.STRIPE_SECRET_KEY.startswith("sk_live_"):
                raise RuntimeError("Production Stripe mode requires live secret keys.")
            if cls.STRIPE_PUBLISHABLE_KEY and not cls.STRIPE_PUBLISHABLE_KEY.startswith("pk_live_"):
                raise RuntimeError("Production Stripe mode requires live publishable keys.")

        if cls.IS_PRODUCTION and cls.PUBLIC_BASE_URL.startswith("http://"):
            raise RuntimeError("PUBLIC_BASE_URL must use https in production.")
