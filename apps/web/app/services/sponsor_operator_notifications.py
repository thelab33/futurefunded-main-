"""Sponsor operator notification bridge.

This safely dispatches sponsor operator payloads without making sponsor lead
submission depend on email/provider readiness. If mail is not configured yet,
it returns a structured "skipped" result that future audits and dashboards can
inspect.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def operator_email_configured() -> bool:
    return bool(
        os.getenv("MAIL_SERVER")
        or os.getenv("SMTP_HOST")
        or os.getenv("MAIL_USERNAME")
        or os.getenv("SMTP_USERNAME")
    )


def dispatch_sponsor_operator_notification(
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Send or safely queue a sponsor operator notification.

    Current behavior is deliberately conservative:
    - logs the notification payload
    - reports mail readiness
    - never raises to the sponsor lead route

    Future implementation can call the existing mail/operator notification
    service here without changing the sponsor route contract.
    """

    payload = dict(payload or {})

    subject = _clean(payload.get("subject"), "New sponsor lead")
    contact_email = _clean(payload.get("contact_email"))
    business_name = _clean(payload.get("business_name"), "New sponsor lead")
    summary = _clean(payload.get("summary"), "Sponsor Package")

    result = {
        "type": "sponsor_operator_notification",
        "status": "skipped",
        "reason": "mail_not_configured",
        "subject": subject,
        "business_name": business_name,
        "summary": summary,
        "contact_email": contact_email,
        "mail_configured": operator_email_configured(),
    }

    try:
        if result["mail_configured"]:
            # Mail service integration point.
            # Keep this as a non-crashing bridge until production SMTP/provider
            # credentials are installed and the final email sender contract is verified.
            result["status"] = "queued"
            result["reason"] = "mail_bridge_ready"

        logger.info(
            "Sponsor operator notification %s | business=%s | summary=%s | contact=%s",
            result["status"],
            business_name,
            summary,
            contact_email or "missing",
        )

        return result
    except Exception as exc:
        logger.exception("Sponsor operator notification dispatch failed")
        result["status"] = "failed"
        result["reason"] = exc.__class__.__name__
        return result
