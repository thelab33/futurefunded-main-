from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

_EVENT_TYPE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]{0,78}[a-z0-9])?$")
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")
_ALLOWED_EVENT_SOURCES = {"web", "api", "admin", "system"}

_MAX_MAP_KEYS = 25
_MAX_KEY_LENGTH = 64
_MAX_VALUE_LENGTH = 500


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _truncate(value: Any, limit: int, default: str = "") -> str:
    return _clean(value, default)[:limit].strip()


def _normalize_event_type(value: Any, default: str = "unknown") -> str:
    cleaned = _truncate(value, 80, default).lower()
    if cleaned and _EVENT_TYPE_RE.fullmatch(cleaned):
        return cleaned
    return default


def _normalize_event_source(value: Any, default: str = "web") -> str:
    cleaned = _truncate(value, 32, default).lower()
    if cleaned in _ALLOWED_EVENT_SOURCES:
        return cleaned
    return default


def _normalize_slug(value: Any) -> str:
    cleaned = _truncate(value, 120).lower()
    if cleaned and _SLUG_RE.fullmatch(cleaned):
        return cleaned
    return ""


def _normalize_path(value: Any) -> str:
    cleaned = _truncate(value, 512)
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith("/") else f"/{cleaned.lstrip('/')}"


def _normalize_occurred_at(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        raw = _clean(value)
        if not raw:
            return datetime.now(UTC).isoformat()

        try:
            candidate = raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            return datetime.now(UTC).isoformat()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt.isoformat()


def _safe_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate(value, _MAX_VALUE_LENGTH)
    if isinstance(value, datetime):
        return _normalize_occurred_at(value)
    if isinstance(value, list):
        output: list[Any] = []
        for item in value[:10]:
            output.append(_safe_scalar(item))
        return output
    if isinstance(value, dict):
        return _normalize_map(value)
    return _truncate(value, _MAX_VALUE_LENGTH)


def _normalize_map(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, Any] = {}
    for raw_key, raw_value in list(value.items())[:_MAX_MAP_KEYS]:
        key = _truncate(raw_key, _MAX_KEY_LENGTH).lower()
        if not key:
            continue
        normalized[key] = _safe_scalar(raw_value)

    return normalized


@dataclass(slots=True)
class AnalyticsEventRecord:
    event_type: str
    event_source: str
    occurred_at: str
    event_id: str = ""
    campaign_slug: str = ""
    path: str = ""
    session_id: str = ""
    request_id: str = ""
    user_agent: str = ""
    referrer: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> AnalyticsEventRecord:
        return cls(
            event_type=_normalize_event_type(payload.get("event_type"), "unknown"),
            event_source=_normalize_event_source(payload.get("event_source"), "web"),
            occurred_at=_normalize_occurred_at(payload.get("occurred_at")),
            event_id=_truncate(payload.get("event_id"), 64, secrets.token_hex(12)),
            campaign_slug=_normalize_slug(payload.get("campaign_slug")),
            path=_normalize_path(payload.get("path")),
            session_id=_truncate(payload.get("session_id"), 120),
            request_id=_truncate(payload.get("request_id"), 128),
            user_agent=_truncate(payload.get("user_agent"), 500),
            referrer=_truncate(payload.get("referrer"), 500),
            properties=_normalize_map(payload.get("properties")),
            metadata=_normalize_map(payload.get("metadata")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalyticsService:
    enabled: bool = True

    def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = AnalyticsEventRecord.from_payload(payload)

        if not self.enabled:
            return {
                "ok": True,
                "enabled": False,
                "message": "Analytics is disabled. Event was accepted without processing.",
                "event": record.to_dict(),
            }

        return {
            "ok": True,
            "enabled": True,
            "message": "Analytics event accepted for processing.",
            "event": record.to_dict(),
        }
