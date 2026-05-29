"""Sponsor confirmation notification bridge."""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def sponsor_mail_configured() -> bool:
    return bool(
        os.getenv("MAIL_SERVER")
        or os.getenv("SMTP_HOST")
        or os.getenv("MAIL_USERNAME")
        or os.getenv("SMTP_USERNAME")
    )


def dispatch_sponsor_confirmation_notification(
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(payload or {})

    result = {
        "type": "sponsor_confirmation_notification",
        "status": "skipped",
        "reason": "mail_not_configured",
        "subject": _clean(payload.get("subject"), "Thanks for your sponsorship"),
        "to_email": _clean(payload.get("to_email")),
        "business_name": _clean(payload.get("business_name"), "Sponsor"),
        "summary": _clean(payload.get("summary"), "Sponsor Package"),
        "mail_configured": sponsor_mail_configured(),
    }

    try:
        if result["mail_configured"]:
            result["status"] = "queued"
            result["reason"] = "mail_bridge_ready"

        logger.info(
            "Sponsor confirmation notification %s | sponsor=%s | summary=%s | to=%s",
            result["status"],
            result["business_name"],
            result["summary"],
            result["to_email"] or "missing",
        )
        return result
    except Exception as exc:
        logger.exception("Sponsor confirmation notification dispatch failed")
        result["status"] = "failed"
        result["reason"] = exc.__class__.__name__
        return result
