"""Sponsor operator notification payload builder.

Turns an accepted sponsor lead + validated sponsor package metadata into a
clean operator-facing payload. This is the bridge from "lead submitted" to
"operator knows exactly what to do next."
"""

from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

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


def build_sponsor_operator_payload(
    form_data: Mapping[str, Any] | None = None,
    *,
    package_metadata: Mapping[str, Any] | None = None,
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any]:
    """Build a normalized sponsor notification payload for campaign operators."""

    form_data = form_data or {}
    package_metadata = package_metadata or {}

    business_name = _clean(
        form_data.get("business_name")
        or form_data.get("company_name")
        or form_data.get("company"),
        "New sponsor lead",
    )

    contact_name = _clean(
        form_data.get("contact_name")
        or form_data.get("name"),
        "Primary contact",
    )

    contact_email = _clean(
        form_data.get("contact_email")
        or form_data.get("email")
        or form_data.get("sponsor_email"),
    ).lower()

    contact_phone = _clean(form_data.get("contact_phone") or form_data.get("phone"))
    message = _clean(form_data.get("message"))

    package_name = _clean(package_metadata.get("package_name"), "Sponsor Package")
    package_key = _clean(package_metadata.get("package_key"), "sponsor-package")
    package_amount = package_metadata.get("package_amount") or 0
    package_price = _clean(package_metadata.get("package_price"), _money(package_amount))
    package_validated = bool(package_metadata.get("package_validated"))

    summary = f"{package_name} — {package_price}" if package_price else package_name

    next_steps = [
        "Confirm the sponsorship package with the sponsor.",
        "Request logo or preferred business name for recognition.",
        "Request website/social link for the campaign page.",
        "Request a short sponsor message if included in the package.",
        "Approve sponsor placement before publishing recognition.",
    ]

    return {
        "type": "sponsor_lead",
        "campaign_slug": _clean(campaign_slug, DEFAULT_CAMPAIGN_SLUG),
        "business_name": business_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "message": message,
        "package_key": package_key,
        "package_name": package_name,
        "package_amount": int(package_amount or 0),
        "package_price": package_price,
        "package_validated": package_validated,
        "summary": summary,
        "subject": f"New sponsor lead: {summary}",
        "next_steps": next_steps,
        "operator_message": (
            f"New sponsor lead: {summary}\n\n"
            f"Sponsor: {business_name}\n"
            f"Contact: {contact_name}\n"
            f"Email: {contact_email or 'Not provided'}\n"
            f"Phone: {contact_phone or 'Not provided'}\n\n"
            "Next steps:\n"
            + "\n".join(f"{index}. {step}" for index, step in enumerate(next_steps, start=1))
        ),
    }
