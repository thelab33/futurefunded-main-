from __future__ import annotations

import logging
import os
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.routers.analytics import router as analytics_router
from app.routers.health import router as health_router
from app.routers.onboarding import router as onboarding_router
from app.routers.payments import router as payments_router
from app.routers.sponsors import router as sponsors_router

logger = logging.getLogger("futurefunded.api")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000")
    seen: set[str] = set()
    origins: list[str] = []

    for origin in raw.split(","):
        cleaned = _clean(origin)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            origins.append(cleaned)

    return origins


def _trusted_hosts() -> list[str]:
    raw = _clean(os.getenv("TRUSTED_HOSTS"))
    if not raw:
        return []

    seen: set[str] = set()
    hosts: list[str] = []

    for host in raw.split(","):
        cleaned = _clean(host)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            hosts.append(cleaned)

    return hosts


def _request_id(request: Request) -> str:
    existing = _clean(request.headers.get("x-request-id"))
    if existing:
        return existing[:128]

    current = _clean(getattr(request.state, "request_id", ""))
    if current:
        return current[:128]

    generated = secrets.token_hex(16)
    request.state.request_id = generated
    return generated


def _error_response(
    *,
    request: Request,
    status_code: int,
    error: str,
    message: str,
) -> JSONResponse:
    request_id = _request_id(request)
    response = JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "error": error,
            "message": message,
            "request_id": request_id,
        },
    )
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Request-Id"] = request_id
    return response


def create_app() -> FastAPI:
    docs_enabled = _as_bool(os.getenv("API_DOCS_ENABLED"), True)

    app = FastAPI(
        title="FutureFunded API",
        version="0.1.0",
        description="Service layer for FutureFunded payments, sponsors, onboarding, and analytics.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
        allow_headers=["*"],
    )

    trusted_hosts = _trusted_hosts()
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    @app.middleware("http")
    async def attach_request_id_and_secure_defaults(request: Request, call_next):
        request.state.request_id = _request_id(request)
        response = await call_next(request)
        response.headers.setdefault("X-Request-Id", request.state.request_id)
        response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(payments_router, prefix="/payments", tags=["payments"])
    app.include_router(sponsors_router, prefix="/sponsors", tags=["sponsors"])
    app.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])
    app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])

    @app.get("/")
    async def root(request: Request) -> dict[str, object]:
        return {
            "ok": True,
            "service": "futurefunded-api",
            "env": os.getenv("ENV", "development"),
            "docs": "/docs" if docs_enabled else None,
            "request_id": _request_id(request),
        }

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=400,
            error="bad_request",
            message=str(exc),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, str) and detail.strip():
            message = detail.strip()
        else:
            message = "Request could not be completed."

        return _error_response(
            request=request,
            status_code=exc.status_code,
            error="http_error",
            message=message,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error | request_id=%s", _request_id(request))
        return _error_response(
            request=request,
            status_code=500,
            error="internal_error",
            message="An internal error occurred.",
        )

    return app


app = create_app()
