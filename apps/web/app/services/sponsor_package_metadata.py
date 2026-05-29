"""Sponsor package metadata validation.

Turns untrusted browser/form sponsor package fields into a server-verified
package object from the campaign profile resolver.
"""

from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

from typing import Any, Mapping

from apps.web.app.services.campaign_profile import resolve_campaign_profile


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _key(value: Any) -> str:
    text = _clean(value).lower()
    text = "".join(ch if ch.isalnum() else "-" for ch in text)
    return "-".join(part for part in text.split("-") if part)


def _amount(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(str(value).replace("$", "").replace(",", "").strip()))
    except Exception:
        return fallback


def sponsor_packages_for_campaign(slug: str = DEFAULT_CAMPAIGN_SLUG) -> list[dict[str, Any]]:
    profile = resolve_campaign_profile(slug)
    packages = profile.get("sponsor_packages") or []
    return [dict(package) for package in packages if isinstance(package, dict)]


def resolve_sponsor_package_metadata(
    form_data: Mapping[str, Any] | None = None,
    *,
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any]:
    """Return server-verified sponsor package metadata.

    Hidden fields are untrusted. This resolves the submitted package against
    the campaign profile and normalizes name/amount from server-side truth.
    """

    form_data = form_data or {}

    selected_key = _key(
        form_data.get("package_key")
        or form_data.get("package")
        or form_data.get("sponsor_package")
        or form_data.get("tier")
        or form_data.get("package_name")
    )

    selected_name = _clean(form_data.get("package_name"))
    selected_amount = _amount(form_data.get("package_amount"), 0)

    packages = sponsor_packages_for_campaign(campaign_slug)
    matched: dict[str, Any] | None = None

    for package in packages:
        package_name = _clean(package.get("label") or package.get("name"), "Sponsor Package")
        package_key = _key(package.get("key") or package_name)

        if selected_key and selected_key == package_key:
            matched = package
            break

        if selected_name and selected_name.lower() == package_name.lower():
            matched = package
            break

    # Secure fallback: do not trust unknown submitted amount.
    if not matched and packages:
        matched = packages[0]

    if matched:
        name = _clean(matched.get("label") or matched.get("name"), "Sponsor Package")
        key = _key(matched.get("key") or name)
        amount = _amount(matched.get("amount"), selected_amount)

        return {
            "package_key": key,
            "package_name": name,
            "package_amount": amount,
            "package_price": _clean(matched.get("price"), f"${amount:,}" if amount else ""),
            "package_best_for": _clean(matched.get("best_for")),
            "package_copy": _clean(matched.get("copy")),
            "package_recognition": list(matched.get("recognition") or []),
            "package_validated": True,
            "package_source": "campaign_profile",
        }

    return {
        "package_key": selected_key,
        "package_name": selected_name or "Sponsor Package",
        "package_amount": selected_amount,
        "package_price": f"${selected_amount:,}" if selected_amount else "",
        "package_best_for": "",
        "package_copy": "",
        "package_recognition": [],
        "package_validated": False,
        "package_source": "submitted_form",
    }
