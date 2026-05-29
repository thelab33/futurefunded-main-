from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.email_service import EmailService


@dataclass(slots=True)
class ReceiptTaskRunner:
    email_service: EmailService

    def build_and_send(
        self,
        *,
        to_email: str,
        supporter_name: str,
        amount_formatted: str,
        campaign_name: str,
    ) -> dict[str, Any]:
        message = self.email_service.build_receipt_email(
            to_email=to_email,
            supporter_name=supporter_name,
            amount_formatted=amount_formatted,
            campaign_name=campaign_name,
        )
        result = self.email_service.send(message)
        return {
            "ok": True,
            "task": "receipt_email",
            "result": result,
        }


def queue_receipt_email(
    *,
    to_email: str,
    supporter_name: str,
    amount_formatted: str,
    campaign_name: str,
    sender_email: str = "support@getfuturefunded.com",
    sender_name: str = "FutureFunded",
    enabled: bool = False,
) -> dict[str, Any]:
    runner = ReceiptTaskRunner(
        email_service=EmailService(
            sender_email=sender_email,
            sender_name=sender_name,
            enabled=enabled,
        )
    )
    return runner.build_and_send(
        to_email=to_email,
        supporter_name=supporter_name,
        amount_formatted=amount_formatted,
        campaign_name=campaign_name,
    )
