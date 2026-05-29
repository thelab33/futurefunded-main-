"""Sponsor lead repository.

MVP-safe persistence for accepted sponsor leads. Uses instance JSONL storage
now, with a clean seam for database-backed sponsor queues later.
"""

from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from flask import current_app, has_app_context


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _amount(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(str(value).replace("$", "").replace(",", "").strip()))
    except Exception:
        return fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_path() -> Path:
    if has_app_context():
        root = Path(current_app.instance_path)
    else:
        root = Path("instance")

    root.mkdir(parents=True, exist_ok=True)
    return root / "futurefunded_sponsor_leads.jsonl"


def build_sponsor_lead_record(
    form_data: Mapping[str, Any] | None = None,
    *,
    package_metadata: Mapping[str, Any] | None = None,
    operator_payload: Mapping[str, Any] | None = None,
    confirmation_payload: Mapping[str, Any] | None = None,
    operator_notification: Mapping[str, Any] | None = None,
    confirmation_notification: Mapping[str, Any] | None = None,
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any]:
    """Normalize an accepted sponsor lead into dashboard-ready data."""

    form_data = form_data or {}
    package_metadata = package_metadata or {}
    operator_payload = operator_payload or {}
    confirmation_payload = confirmation_payload or {}
    operator_notification = operator_notification or {}
    confirmation_notification = confirmation_notification or {}

    business_name = _clean(
        form_data.get("business_name")
        or form_data.get("company_name")
        or form_data.get("company"),
        "New sponsor",
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

    package_name = _clean(package_metadata.get("package_name"), "Sponsor Package")
    package_key = _clean(package_metadata.get("package_key"), "sponsor-package")
    package_amount = _amount(package_metadata.get("package_amount"), 0)
    package_price = _clean(
        package_metadata.get("package_price"),
        f"${package_amount:,}" if package_amount else "",
    )

    return {
        "id": uuid.uuid4().hex,
        "created_at": _now(),
        "source": "sponsors.lead",
        "status": "new",
        "stage": "logo_needed",
        "campaign_slug": _clean(campaign_slug, DEFAULT_CAMPAIGN_SLUG),
        "business_name": business_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": _clean(form_data.get("contact_phone") or form_data.get("phone")),
        "message": _clean(form_data.get("message")),
        "package_key": package_key,
        "package_name": package_name,
        "package_amount": package_amount,
        "package_price": package_price,
        "summary": _clean(operator_payload.get("summary"), f"{package_name} — {package_price}".strip(" —")),
        "operator_subject": _clean(operator_payload.get("subject")),
        "confirmation_subject": _clean(confirmation_payload.get("subject")),
        "operator_notification_status": _clean(operator_notification.get("status"), "unknown"),
        "confirmation_notification_status": _clean(confirmation_notification.get("status"), "unknown"),
        "next_steps": list(operator_payload.get("next_steps") or [
            "Request logo or preferred business name.",
            "Request website/social link.",
            "Request sponsor message.",
            "Approve placement.",
        ]),
    }


def record_sponsor_lead(
    form_data: Mapping[str, Any] | None = None,
    *,
    package_metadata: Mapping[str, Any] | None = None,
    operator_payload: Mapping[str, Any] | None = None,
    confirmation_payload: Mapping[str, Any] | None = None,
    operator_notification: Mapping[str, Any] | None = None,
    confirmation_notification: Mapping[str, Any] | None = None,
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any]:
    """Append an accepted sponsor lead and return the persisted record."""

    record = build_sponsor_lead_record(
        form_data,
        package_metadata=package_metadata,
        operator_payload=operator_payload,
        confirmation_payload=confirmation_payload,
        operator_notification=operator_notification,
        confirmation_notification=confirmation_notification,
        campaign_slug=campaign_slug,
    )

    path = _storage_path()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")

    return record


def recent_sponsor_leads(
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return recent sponsor leads for a campaign."""

    path = _storage_path()

    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            record = json.loads(line)
        except Exception:
            continue

        if record.get("campaign_slug") != campaign_slug:
            continue

        rows.append(record)

        if len(rows) >= limit:
            break

    return rows

SPONSOR_LEAD_STAGES: tuple[str, ...] = (
    "new",
    "logo_needed",
    "website_needed",
    "message_needed",
    "ready_for_approval",
    "approved",
    "displayed",
    "thank_you_sent",
)

SPONSOR_LEAD_STAGE_LABELS: dict[str, str] = {
    "new": "New",
    "logo_needed": "Logo needed",
    "website_needed": "Website needed",
    "message_needed": "Message needed",
    "ready_for_approval": "Ready for approval",
    "approved": "Approved",
    "displayed": "Displayed",
    "thank_you_sent": "Thank-you sent",
}


def normalize_sponsor_lead_stage(stage: Any) -> str:
    """Normalize and validate sponsor lead stage."""

    normalized = _clean(stage, "new").lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in SPONSOR_LEAD_STAGES else "new"


def sponsor_lead_status_for_stage(stage: str) -> str:
    """Map workflow stage to broad lead status."""

    stage = normalize_sponsor_lead_stage(stage)

    if stage in {"approved", "displayed", "thank_you_sent"}:
        return "approved"

    if stage in {"ready_for_approval"}:
        return "review"

    return "new"


def update_sponsor_lead_stage(
    lead_id: str,
    stage: str,
    *,
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any] | None:
    """Update a persisted sponsor lead stage.

    MVP-safe implementation rewrites the local JSONL file. This keeps the API
    stable for a future database-backed sponsor queue.
    """

    lead_id = _clean(lead_id)
    next_stage = normalize_sponsor_lead_stage(stage)
    path = _storage_path()

    if not lead_id or not path.exists():
        return None

    records: list[dict[str, Any]] = []
    updated: dict[str, Any] | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except Exception:
            continue

        if (
            record.get("id") == lead_id
            and record.get("campaign_slug") == campaign_slug
        ):
            record["stage"] = next_stage
            record["status"] = sponsor_lead_status_for_stage(next_stage)
            record["updated_at"] = _now()
            record["stage_label"] = SPONSOR_LEAD_STAGE_LABELS.get(next_stage, next_stage.title())
            updated = record

        records.append(record)

    if updated is None:
        return None

    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    return updated


PUBLIC_SPONSOR_STAGES: tuple[str, ...] = (
    "displayed",
    "thank_you_sent",
)


def public_sponsor_recognitions(
    campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return sponsor leads approved for public campaign recognition."""

    leads = recent_sponsor_leads(campaign_slug, limit=100)
    public: list[dict[str, Any]] = []

    for lead in leads:
        if normalize_sponsor_lead_stage(lead.get("stage")) not in PUBLIC_SPONSOR_STAGES:
            continue

        public.append(
            {
                "id": lead.get("id"),
                "business_name": _clean(lead.get("business_name"), "Community Sponsor"),
                "package_name": _clean(lead.get("package_name"), "Sponsor Package"),
                "package_price": _clean(lead.get("package_price")),
                "summary": _clean(lead.get("summary"), lead.get("package_name") or "Sponsor Package"),
                "stage": normalize_sponsor_lead_stage(lead.get("stage")),
                "status": _clean(lead.get("status"), "approved"),
                "message": _clean(lead.get("message")),
                "created_at": lead.get("created_at"),
                "updated_at": lead.get("updated_at"),
            }
        )

        if len(public) >= limit:
            break

    return public
