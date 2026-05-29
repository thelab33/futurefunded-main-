"""
FutureFunded lifecycle dispatch bridge.

Routes/webhooks should call this layer instead of manually composing email copy.
It sends the supporter-facing message and the operator-facing alert together,
with safe error handling so lifecycle messaging never breaks checkout success.
"""

from __future__ import annotations

from typing import Any, Mapping

from .ff_lifecycle_messages import (
    donor_receipt_email,
    operator_donation_alert_email,
    operator_sponsor_alert_email,
    sponsor_confirmation_email,
)
from .ff_transactional_email import send_lifecycle_email


def _safe_send(message) -> dict[str, Any]:
    try:
        return send_lifecycle_email(message)
    except Exception as exc:
        return {
            "sent": False,
            "mode": "error",
            "category": getattr(message, "category", "unknown"),
            "to": getattr(message, "to_email", ""),
            "subject": getattr(message, "subject", ""),
            "error": f"{type(exc).__name__}: {exc}",
        }


def dispatch_donation_lifecycle(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Send donor receipt + operator donation alert.

    Expected payload keys may include:
    - supporter_email / donor_email / email
    - supporter_name / donor_name
    - amount_cents / amount
    - campaign_slug / campaign_url
    - campaign_name
    - team_name
    - operator_email
    - reply_to
    """
    data = dict(payload)

    donor_message = donor_receipt_email(data)
    operator_message = operator_donation_alert_email(data)

    return {
        "category": "donation_lifecycle",
        "results": [
            _safe_send(donor_message),
            _safe_send(operator_message),
        ],
    }


def dispatch_sponsor_lifecycle(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Send sponsor confirmation + operator sponsor alert.

    Expected payload keys may include:
    - sponsor_email / email
    - sponsor_name / business_name
    - sponsor_tier / tier
    - amount_cents / amount
    - campaign_slug / campaign_url
    - campaign_name
    - team_name
    - operator_email
    - reply_to
    """
    data = dict(payload)

    sponsor_message = sponsor_confirmation_email(data)
    operator_message = operator_sponsor_alert_email(data)

    return {
        "category": "sponsor_lifecycle",
        "results": [
            _safe_send(sponsor_message),
            _safe_send(operator_message),
        ],
    }
