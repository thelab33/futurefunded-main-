"""
FutureFunded lifecycle message contracts.

Owns donor, sponsor, and operator message copy for the fundraising funnel.
Framework-light so payment routes, webhooks, sponsor flows, and dashboard tools
can share the same message language.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Mapping


@dataclass(frozen=True)
class LifecycleEmail:
    category: str
    to_email: str
    subject: str
    preview_text: str
    text_body: str
    html_body: str
    reply_to: str | None = None
    metadata: dict[str, Any] | None = None


def _v(payload: Mapping[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


def _money(payload: Mapping[str, Any]) -> str:
    cents = _v(payload, "amount_cents", "total_cents", default=None)
    if cents not in (None, ""):
        try:
            return f"${int(cents) / 100:,.2f}"
        except Exception:
            pass

    amount = _v(payload, "amount", "amount_dollars", default=None)
    if amount not in (None, ""):
        try:
            return f"${float(amount):,.0f}"
        except Exception:
            return str(amount)

    return "your support"


def _campaign_url(payload: Mapping[str, Any]) -> str:
    explicit = _v(payload, "campaign_url", default="")
    if explicit:
        return str(explicit)

    base = str(_v(payload, "public_base_url", default="https://getfuturefunded.com")).rstrip("/")
    slug = str(_v(payload, "campaign_slug", "slug", default="connect-atx-elite")).strip("/")
    return f"{base}/c/{slug}"


def _wrap(title: str, preview: str, body: str, cta_label: str, cta_url: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(title)}</title>
</head>
<body style="margin:0;background:#f6f7fb;color:#101828;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preview)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f7fb;padding:28px 14px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border:1px solid #e6e9f2;border-radius:28px;overflow:hidden;box-shadow:0 24px 70px rgba(16,24,40,.10);">
          <tr>
            <td style="padding:28px;background:linear-gradient(135deg,#101828,#1d2939);color:#fff;">
              <div style="font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#b7c4d8;font-weight:800;">FutureFunded</div>
              <h1 style="margin:10px 0 0;font-size:28px;line-height:1.1;letter-spacing:-.04em;">{escape(title)}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;color:#344054;font-size:16px;line-height:1.65;">
              {body}
              <div style="margin-top:28px;">
                <a href="{escape(cta_url, quote=True)}" style="display:inline-block;background:#101828;color:#fff;text-decoration:none;font-weight:800;border-radius:999px;padding:14px 20px;">
                  {escape(cta_label)}
                </a>
              </div>
              <p style="margin:28px 0 0;color:#667085;font-size:13px;line-height:1.55;">
                Sent by FutureFunded because a campaign action was completed or submitted.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def donor_receipt_email(payload: Mapping[str, Any]) -> LifecycleEmail:
    team = str(_v(payload, "team_name", "organization_name", default="Connect ATX Elite"))
    campaign = str(_v(payload, "campaign_name", default="Connect ATX Elite Season Fund"))
    name = str(_v(payload, "supporter_name", "donor_name", default="Friend"))
    amount = _money(payload)
    url = _campaign_url(payload)
    to_email = str(_v(payload, "supporter_email", "donor_email", "email", default=""))
    reply_to = str(_v(payload, "reply_to", "contact_email", default="")) or None

    subject = f"Thank you for supporting {team}"
    preview = f"Your {amount} contribution to {campaign} has been received."

    text = (
        f"Hi {name},\n\n"
        f"Thank you for supporting {team}. Your {amount} contribution to {campaign} has been received.\n\n"
        "Your support helps cover travel, tournament days, meals, gear, training, and gym time.\n\n"
        f"Campaign page: {url}\n\n"
        "With appreciation,\nFutureFunded"
    )

    html = _wrap(
        subject,
        preview,
        f"""
        <p style="margin-top:0;">Hi {escape(name)},</p>
        <p>Thank you for supporting <strong>{escape(team)}</strong>. Your <strong>{escape(amount)}</strong> contribution to <strong>{escape(campaign)}</strong> has been received.</p>
        <p>Your support helps cover travel, tournament days, meals, gear, training, and gym time.</p>
        <p style="padding:16px 18px;border-radius:18px;background:#f8fafc;border:1px solid #e6e9f2;"><strong>Impact note:</strong> every contribution helps keep the season moving.</p>
        """,
        "View campaign",
        url,
    )

    return LifecycleEmail("donor_receipt", to_email, subject, preview, text, html, reply_to, dict(payload))


def sponsor_confirmation_email(payload: Mapping[str, Any]) -> LifecycleEmail:
    team = str(_v(payload, "team_name", "organization_name", default="Connect ATX Elite"))
    campaign = str(_v(payload, "campaign_name", default="Connect ATX Elite Season Fund"))
    sponsor = str(_v(payload, "sponsor_name", "business_name", default="Sponsor"))
    tier = str(_v(payload, "sponsor_tier", "tier", default="Community Partner"))
    amount = _money(payload)
    url = _campaign_url(payload)
    to_email = str(_v(payload, "sponsor_email", "email", default=""))
    reply_to = str(_v(payload, "reply_to", "contact_email", default="")) or None

    subject = f"Sponsor confirmation for {team}"
    preview = f"Your {tier} sponsor request for {campaign} is in review."

    text = (
        f"Hi {sponsor},\n\n"
        f"Thank you for choosing the {tier} package for {team}. Your {amount} sponsor commitment for {campaign} has been received or submitted for review.\n\n"
        "Next steps:\n"
        "1. The campaign operator reviews your business name and recognition details.\n"
        "2. If a logo or short sponsor note is needed, the operator will follow up.\n"
        "3. Public recognition is published only after review.\n\n"
        f"Campaign page: {url}\n\n"
        "Thank you for supporting the community,\nFutureFunded"
    )

    html = _wrap(
        subject,
        preview,
        f"""
        <p style="margin-top:0;">Hi {escape(sponsor)},</p>
        <p>Thank you for choosing the <strong>{escape(tier)}</strong> package for <strong>{escape(team)}</strong>. Your <strong>{escape(amount)}</strong> sponsor commitment for <strong>{escape(campaign)}</strong> has been received or submitted for review.</p>
        <div style="padding:16px 18px;border-radius:18px;background:#f8fafc;border:1px solid #e6e9f2;">
          <strong>Next steps</strong>
          <ol style="margin:10px 0 0;padding-left:20px;">
            <li>The campaign operator reviews your business name and recognition details.</li>
            <li>If a logo or sponsor note is needed, the operator will follow up.</li>
            <li>Public recognition is published only after review.</li>
          </ol>
        </div>
        """,
        "View campaign",
        url,
    )

    return LifecycleEmail("sponsor_confirmation", to_email, subject, preview, text, html, reply_to, dict(payload))


def operator_donation_alert_email(payload: Mapping[str, Any]) -> LifecycleEmail:
    team = str(_v(payload, "team_name", default="Connect ATX Elite"))
    name = str(_v(payload, "supporter_name", "donor_name", default="Supporter"))
    amount = _money(payload)
    url = _campaign_url(payload)
    to_email = str(_v(payload, "operator_email", "admin_email", default="arodgps@gmail.com"))

    subject = f"New donation for {team}"
    preview = f"{name} contributed {amount}."

    text = (
        f"New donation received\n\nTeam: {team}\nSupporter: {name}\nAmount: {amount}\nCampaign: {url}\n\n"
        "Recommended action: verify the ledger entry and thank the supporter if personal follow-up is appropriate."
    )

    html = _wrap(
        subject,
        preview,
        f"""
        <p style="margin-top:0;"><strong>New donation received.</strong></p>
        <p><strong>Team:</strong> {escape(team)}<br><strong>Supporter:</strong> {escape(name)}<br><strong>Amount:</strong> {escape(amount)}</p>
        <p style="padding:16px 18px;border-radius:18px;background:#f8fafc;border:1px solid #e6e9f2;">Recommended action: verify the ledger entry and thank the supporter if personal follow-up is appropriate.</p>
        """,
        "Open campaign",
        url,
    )

    return LifecycleEmail("operator_donation_alert", to_email, subject, preview, text, html, None, dict(payload))


def operator_sponsor_alert_email(payload: Mapping[str, Any]) -> LifecycleEmail:
    team = str(_v(payload, "team_name", default="Connect ATX Elite"))
    sponsor = str(_v(payload, "sponsor_name", "business_name", default="Sponsor"))
    tier = str(_v(payload, "sponsor_tier", "tier", default="Community Partner"))
    amount = _money(payload)
    url = _campaign_url(payload)
    to_email = str(_v(payload, "operator_email", "admin_email", default="arodgps@gmail.com"))

    subject = f"New sponsor request for {team}"
    preview = f"{sponsor} selected {tier}."

    text = (
        f"New sponsor request\n\nTeam: {team}\nSponsor: {sponsor}\nTier: {tier}\nAmount: {amount}\nCampaign: {url}\n\n"
        "Recommended action: review sponsor details before public recognition appears."
    )

    html = _wrap(
        subject,
        preview,
        f"""
        <p style="margin-top:0;"><strong>New sponsor request received.</strong></p>
        <p><strong>Team:</strong> {escape(team)}<br><strong>Sponsor:</strong> {escape(sponsor)}<br><strong>Tier:</strong> {escape(tier)}<br><strong>Amount:</strong> {escape(amount)}</p>
        <p style="padding:16px 18px;border-radius:18px;background:#f8fafc;border:1px solid #e6e9f2;">Recommended action: review sponsor details before public recognition appears.</p>
        """,
        "Open campaign",
        url,
    )

    return LifecycleEmail("operator_sponsor_alert", to_email, subject, preview, text, html, None, dict(payload))


def sample_payload() -> dict[str, Any]:
    return {
        "public_base_url": "https://getfuturefunded.com",
        "campaign_slug": "connect-atx-elite",
        "campaign_name": "Connect ATX Elite Season Fund",
        "team_name": "Connect ATX Elite",
        "supporter_name": "Jordan Supporter",
        "supporter_email": "supporter@example.com",
        "donor_email": "supporter@example.com",
        "sponsor_name": "Austin Community Partner",
        "business_name": "Austin Community Partner",
        "sponsor_email": "sponsor@example.com",
        "sponsor_tier": "Community Partner",
        "amount_cents": 5000,
        "operator_email": "arodgps@gmail.com",
        "reply_to": "arodgps@gmail.com",
    }


def render_all_samples(payload: Mapping[str, Any] | None = None) -> list[LifecycleEmail]:
    data = dict(payload or sample_payload())
    return [
        donor_receipt_email(data),
        sponsor_confirmation_email(data),
        operator_donation_alert_email(data),
        operator_sponsor_alert_email(data),
    ]
