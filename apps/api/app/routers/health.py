from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

router = APIRouter()


def _clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    return value.strip() or default


def _request_id(request: Request) -> str | None:
    return (
        _clean(getattr(request.state, "request_id", None))
        or _clean(request.headers.get("x-request-id"))
        or None
    )


def _set_response_headers(response: Response, request_id: str | None = None) -> None:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if request_id:
        response.headers["X-Request-Id"] = request_id


@router.get("")
@router.get("/")
async def health(request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    _set_response_headers(response, request_id)

    return {
        "ok": True,
        "service": "futurefunded-api",
        "env": os.getenv("ENV", "development"),
        "time": datetime.now(UTC).isoformat(),
        "request_id": request_id,
    }


@router.get("/ready")
@router.get("/ready/")
async def ready(request: Request, response: Response) -> dict[str, object]:
    request_id = _request_id(request)
    _set_response_headers(response, request_id)

    return {
        "ok": True,
        "ready": True,
        "service": "futurefunded-api",
        "checks": {
            "api": True,
        },
        "request_id": request_id,
    }
