from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.schemas.events import AnalyticsEventIn, EventAccepted

router = APIRouter()

logger = logging.getLogger("futurefunded.analytics")

_MAX_EVENT_BODY_BYTES = 32 * 1024


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _set_response_headers(
    response: Response,
    *,
    request_id: str | None = None,
    cache_control: str = "no-store, max-age=0",
    robots: str = "noindex, nofollow",
) -> None:
    response.headers.setdefault("Cache-Control", cache_control)
    response.headers.setdefault("X-Robots-Tag", robots)
    if request_id:
        response.headers.setdefault("X-Request-Id", request_id)


def _enforce_body_limit(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if not content_length:
        return

    try:
        if int(content_length) > _MAX_EVENT_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Analytics payload too large.",
            )
    except ValueError:
        return


def _metadata_key_count(payload: AnalyticsEventIn) -> int:
    metadata = getattr(payload, "metadata", None)
    return len(metadata) if isinstance(metadata, dict) else 0


@router.post("/event", response_model=EventAccepted)
@router.post("/event/", response_model=EventAccepted)
async def ingest_event(
    payload: AnalyticsEventIn,
    request: Request,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="x-request-id"),
) -> EventAccepted:
    _enforce_body_limit(request)
    _set_response_headers(response, request_id=x_request_id)

    event_type = _clean(getattr(payload, "event_type", "unknown"), "unknown")
    campaign_slug = _clean(getattr(payload, "campaign_slug", ""))
    metadata_keys = _metadata_key_count(payload)

    logger.info(
        "Analytics event accepted | type=%s | campaign=%s | metadata_keys=%s | request_id=%s",
        event_type,
        campaign_slug,
        metadata_keys,
        x_request_id,
    )

    response.headers.setdefault("X-Analytics-Event-Type", event_type[:80] or "unknown")

    return EventAccepted(
        event_type=event_type,
        message="Analytics event accepted for processing.",
    )
