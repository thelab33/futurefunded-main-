from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    body_text: str
    body_html: str = ""
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EmailService:
    sender_email: str = "support@getfuturefunded.com"
    sender_name: str = "FutureFunded"
    enabled: bool = False

    @property
    def from_header(self) -> str:
        if self.sender_name:
            return f"{self.sender_name} <{self.sender_email}>"
        return self.sender_email

    def build_receipt_email(
        self,
        to_email: str,
        supporter_name: str,
        amount_formatted: str,
        campaign_name: str,
    ) -> EmailMessage:
        safe_name = _clean(supporter_name, "Supporter")
        safe_campaign = _clean(campaign_name, "the campaign")
        safe_amount = _clean(amount_formatted, "$0")

        subject = f"Receipt for your support of {safe_campaign}"
        body_text = (
            f"Hi {safe_name},\n\n"
            f"Thank you for supporting {safe_campaign}.\n"
            f"We received your contribution of {safe_amount}.\n\n"
            f"This message is your confirmation that the support was recorded.\n"
            f"If you need help, reply to {self.sender_email}.\n\n"
            f"— FutureFunded"
        )

        body_html = (
            f"<p>Hi {safe_name},</p>"
            f"<p>Thank you for supporting <strong>{safe_campaign}</strong>.</p>"
            f"<p>We received your contribution of <strong>{safe_amount}</strong>.</p>"
            f"<p>This message is your confirmation that the support was recorded.</p>"
            f"<p>If you need help, reply to {self.sender_email}.</p>"
            f"<p>— FutureFunded</p>"
        )

        return EmailMessage(
            to=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            reply_to=self.sender_email,
        )

    def build_sponsor_lead_email(
        self,
        notify_email: str,
        lead: dict[str, Any],
    ) -> EmailMessage:
        business_name = _clean(lead.get("business_name"), "Sponsor")
        sponsor_tier = _clean(lead.get("sponsor_tier"), "Unspecified tier")
        campaign_slug = _clean(lead.get("campaign_slug"), "campaign")
        contact_name = _clean(lead.get("contact_name"), "Primary Contact")
        contact_email = _clean(lead.get("contact_email"))
        contact_phone = _clean(lead.get("contact_phone"))
        message = _clean(lead.get("message"))

        subject = f"New sponsor lead for {campaign_slug}: {business_name}"
        body_text = (
            f"New sponsor lead received.\n\n"
            f"Business: {business_name}\n"
            f"Contact: {contact_name}\n"
            f"Email: {contact_email}\n"
            f"Phone: {contact_phone}\n"
            f"Tier: {sponsor_tier}\n"
            f"Campaign: {campaign_slug}\n\n"
            f"Message:\n{message or '(none)'}\n"
        )

        body_html = (
            f"<p><strong>New sponsor lead received.</strong></p>"
            f"<p><strong>Business:</strong> {business_name}<br>"
            f"<strong>Contact:</strong> {contact_name}<br>"
            f"<strong>Email:</strong> {contact_email}<br>"
            f"<strong>Phone:</strong> {contact_phone}<br>"
            f"<strong>Tier:</strong> {sponsor_tier}<br>"
            f"<strong>Campaign:</strong> {campaign_slug}</p>"
            f"<p><strong>Message:</strong><br>{message or '(none)'}</p>"
        )

        return EmailMessage(
            to=notify_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            reply_to=contact_email or self.sender_email,
        )

    def send(self, message: EmailMessage) -> dict[str, Any]:
        return {
            "ok": True,
            "enabled": self.enabled,
            "provider": "stub",
            "from": self.from_header,
            "message": message.to_dict(),
        }
