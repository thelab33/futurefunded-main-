"""Sponsor confirmation payload builder."""

from __future__ import annotations

from typing import Any, Mapping


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _money(value: Any) -> str:
    try:
        amount = int(float(str(value).replace("$", "").replace(",", "").strip()))
    except Exception:
        amount = 0
    return f"${amount:,}" if amount else ""


def build_sponsor_confirmation_payload(
    form_data: Mapping[str, Any] | None = None,
    *,
    package_metadata: Mapping[str, Any] | None = None,
    campaign_name: str = "Campaign",
    team_name: str = "the campaign",
    campaign_url: str = "/",
) -> dict[str, Any]:
    form_data = form_data or {}
    package_metadata = package_metadata or {}

    business_name = _clean(
        form_data.get("business_name")
        or form_data.get("company_name")
        or form_data.get("company"),
        "Sponsor",
    )

    contact_name = _clean(form_data.get("contact_name") or form_data.get("name"), "there")
    contact_email = _clean(
        form_data.get("contact_email")
        or form_data.get("email")
        or form_data.get("sponsor_email"),
    ).lower()

    package_name = _clean(package_metadata.get("package_name"), "Sponsor Package")
    package_amount = package_metadata.get("package_amount") or 0
    package_price = _clean(package_metadata.get("package_price"), _money(package_amount))
    summary = f"{package_name} — {package_price}" if package_price else package_name

    next_steps = [
        "Send your logo or preferred business name for recognition.",
        "Send your website or social link for the campaign page.",
        "Send a short sponsor message if you would like one included.",
        "The campaign organizer will confirm placement before publishing recognition.",
    ]

    body = (
        f"Hi {contact_name},\n\n"
        f"Thank you for supporting {team_name}. We received your sponsor interest for "
        f"the {summary} package.\n\n"
        f"Campaign: {campaign_name}\n"
        f"Sponsor: {business_name}\n"
        f"Package: {summary}\n"
        f"Campaign page: {campaign_url}\n\n"
        "Next steps:\n"
        + "\n".join(f"{index}. {step}" for index, step in enumerate(next_steps, start=1))
        + "\n\n"
        "We appreciate your support and will follow up with confirmation details."
    )

    return {
        "type": "sponsor_confirmation",
        "to_email": contact_email,
        "business_name": business_name,
        "contact_name": contact_name,
        "team_name": _clean(team_name, "the campaign"),
        "campaign_name": _clean(campaign_name, "Campaign"),
        "campaign_url": _clean(campaign_url, "/"),
        "package_name": package_name,
        "package_amount": int(package_amount or 0),
        "package_price": package_price,
        "summary": summary,
        "subject": f"Thanks for sponsoring {team_name}: {summary}",
        "next_steps": next_steps,
        "body": body,
    }
