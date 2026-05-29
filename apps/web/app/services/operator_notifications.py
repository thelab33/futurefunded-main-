from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _notification_recipient() -> str:
    return _clean(
        current_app.config.get("INTERNAL_NOTIFICATION_EMAIL")
        or os.getenv("INTERNAL_NOTIFICATION_EMAIL")
        or current_app.config.get("DONATIONS_EMAIL")
        or os.getenv("DONATIONS_EMAIL")
        or current_app.config.get("SUPPORT_EMAIL")
        or os.getenv("SUPPORT_EMAIL"),
        "arodgps@gmail.com",
    )


def _notification_outbox_path() -> Path:
    configured = _clean(
        current_app.config.get("FF_OPERATOR_NOTIFICATION_OUTBOX")
        or os.getenv("FF_OPERATOR_NOTIFICATION_OUTBOX")
    )

    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    instance_path = Path(current_app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "operator-notification-outbox.jsonl"


def _existing_event_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    event_ids: set[str] = set()

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue

            event_id = _clean(record.get("event_id"))
            if event_id:
                event_ids.add(event_id)
    except Exception:
        return set()

    return event_ids


def record_operator_notification(
    *,
    event_type: str,
    subject: str,
    body: str,
    metadata: dict[str, Any] | None = None,
    recipient: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Record an operator notification event.

    Current delivery mode:
    - always appends an audit record to JSONL
    - if MAIL_ENABLED is false, this is the durable notification outbox
    - SMTP/provider delivery can be layered on later without losing auditability
    """

    safe_event_type = _clean(event_type, "operator_event")
    safe_subject = _clean(subject, "FutureFunded operator notification")
    safe_body = _clean(body, "A FutureFunded operator event was recorded.")
    safe_recipient = _clean(recipient, _notification_recipient())
    safe_event_id = _clean(event_id)

    mail_enabled = _bool(
        current_app.config.get("MAIL_ENABLED")
        if current_app.config.get("MAIL_ENABLED") is not None
        else os.getenv("MAIL_ENABLED")
    )

    outbox_path = _notification_outbox_path()

    if safe_event_id and safe_event_id in _existing_event_ids(outbox_path):
        return {
            "ok": True,
            "recorded": False,
            "duplicate": True,
            "event_id": safe_event_id,
            "path": str(outbox_path),
        }

    record = {
        "id": uuid4().hex,
        "event_id": safe_event_id or uuid4().hex,
        "event_type": safe_event_type,
        "to": safe_recipient,
        "subject": safe_subject,
        "body": safe_body,
        "metadata": metadata or {},
        "mail_enabled": mail_enabled,
        "delivery_mode": "jsonl_outbox" if not mail_enabled else "jsonl_outbox_pending_mail_provider",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with outbox_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    current_app.logger.info(
        "FutureFunded operator notification recorded | event=%s to=%s outbox=%s",
        safe_event_type,
        safe_recipient,
        outbox_path,
    )

    return {
        "ok": True,
        "recorded": True,
        "duplicate": False,
        "event_id": record["event_id"],
        "path": str(outbox_path),
        "mail_enabled": mail_enabled,
    }
