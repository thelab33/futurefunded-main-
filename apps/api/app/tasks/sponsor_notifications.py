from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.email_service import EmailService


@dataclass(slots=True)
class SponsorNotificationRunner:
    email_service: EmailService

    def build_and_send(
        self,
        *,
        notify_email: str,
        lead: dict[str, Any],
    ) -> dict[str, Any]:
        message = self.email_service.build_sponsor_lead_email(
            notify_email=notify_email,
            lead=lead,
        )
        result = self.email_service.send(message)
        return {
            "ok": True,
            "task": "sponsor_notification",
            "result": result,
        }


def queue_sponsor_notification(
    *,
    notify_email: str,
    lead: dict[str, Any],
    sender_email: str = "support@getfuturefunded.com",
    sender_name: str = "FutureFunded",
    enabled: bool = False,
) -> dict[str, Any]:
    runner = SponsorNotificationRunner(
        email_service=EmailService(
            sender_email=sender_email,
            sender_name=sender_name,
            enabled=enabled,
        )
    )
    return runner.build_and_send(
        notify_email=notify_email,
        lead=lead,
    )
