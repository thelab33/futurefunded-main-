"""
FutureFunded transactional email sender.

Uses SMTP when configured. Otherwise writes preview JSON files to
instance/email-spool so lifecycle messages can be QA'd without sending email.
"""

from __future__ import annotations

import json
import os
import smtplib
from dataclasses import asdict
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from .ff_lifecycle_messages import LifecycleEmail


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _spool_dir() -> Path:
    path = Path(os.getenv("FF_EMAIL_PREVIEW_DIR", "instance/email-spool"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def smtp_ready() -> bool:
    return bool(os.getenv("FF_SMTP_HOST") and os.getenv("FF_EMAIL_FROM"))


def provider_status() -> dict[str, Any]:
    return {
        "smtp_ready": smtp_ready(),
        "dry_run": _truthy(os.getenv("FF_EMAIL_DRY_RUN", "1")),
        "from_email": os.getenv("FF_EMAIL_FROM", ""),
        "host": os.getenv("FF_SMTP_HOST", ""),
        "port": os.getenv("FF_SMTP_PORT", "587"),
        "preview_dir": str(_spool_dir()),
    }


def send_lifecycle_email(message: LifecycleEmail, *, dry_run: bool | None = None) -> dict[str, Any]:
    if not message.to_email:
        return {
            "sent": False,
            "mode": "skipped",
            "reason": "missing_recipient",
            "category": message.category,
        }

    use_dry_run = _truthy(os.getenv("FF_EMAIL_DRY_RUN", "1")) if dry_run is None else dry_run

    if use_dry_run or not smtp_ready():
        return _write_preview(message)

    msg = EmailMessage()
    msg["Subject"] = message.subject
    msg["From"] = os.getenv("FF_EMAIL_FROM", "FutureFunded <no-reply@getfuturefunded.com>")
    msg["To"] = message.to_email

    reply_to = message.reply_to or os.getenv("FF_EMAIL_REPLY_TO")
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(message.text_body)
    msg.add_alternative(message.html_body, subtype="html")

    host = os.environ["FF_SMTP_HOST"]
    port = int(os.getenv("FF_SMTP_PORT", "587"))
    username = os.getenv("FF_SMTP_USERNAME", "")
    password = os.getenv("FF_SMTP_PASSWORD", "")
    use_tls = _truthy(os.getenv("FF_SMTP_USE_TLS", "1"))

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username or password:
            smtp.login(username, password)
        smtp.send_message(msg)

    return {
        "sent": True,
        "mode": "smtp",
        "category": message.category,
        "to": message.to_email,
        "subject": message.subject,
    }


def _write_preview(message: LifecycleEmail) -> dict[str, Any]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_category = "".join(ch for ch in message.category if ch.isalnum() or ch in {"-", "_"})
    path = _spool_dir() / f"{stamp}-{safe_category}.json"

    payload = asdict(message)
    payload["created_at"] = datetime.now(timezone.utc).isoformat()

    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "sent": False,
        "mode": "preview_spool",
        "category": message.category,
        "to": message.to_email,
        "subject": message.subject,
        "path": str(path),
    }
