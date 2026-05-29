from __future__ import annotations
from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from apps.web.app.extensions import get_db_session


DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_SLUG

SETUP_STATUS_OPTIONS = ("draft", "review_needed", "launch_ready", "launched", "archived")
SETUP_STATUS_LABELS = {
    "draft": "Draft",
    "review_needed": "Review Needed",
    "launch_ready": "Launch Ready",
    "launched": "Launched",
    "archived": "Archived",
}


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _money_to_cents(value: Any) -> int:
    if isinstance(value, int):
        return max(0, value)

    raw = re.sub(r"[^0-9.]", "", str(value or ""))
    if not raw:
        return 0

    try:
        return max(0, int(round(float(raw) * 100)))
    except ValueError:
        return 0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))



def normalize_setup_status(value: Any, default: str = "draft") -> str:
    """Normalize setup workflow status into a known operator state."""
    raw = _clean(value, default).lower()
    safe = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")

    aliases = {
        "review": "review_needed",
        "needs_review": "review_needed",
        "review_needed": "review_needed",
        "launch_ready": "launch_ready",
        "ready": "launch_ready",
        "launchready": "launch_ready",
        "published": "launched",
        "live": "launched",
    }

    safe = aliases.get(safe, safe)

    if safe not in SETUP_STATUS_OPTIONS:
        return default if default in SETUP_STATUS_OPTIONS else "draft"

    return safe


def setup_status_label(value: Any) -> str:
    return SETUP_STATUS_LABELS.get(normalize_setup_status(value), "Draft")

def normalize_onboarding_payload(
    payload: dict[str, Any],
    *,
    default_campaign_slug: str = DEFAULT_CAMPAIGN_SLUG,
) -> dict[str, Any]:
    campaign_slug = _clean(
        payload.get("campaign_slug") or payload.get("slug"),
        default_campaign_slug,
    )

    goal_value = payload.get("goal")
    goal_cents_value = payload.get("goal_cents")
    goal_cents = _money_to_cents(goal_value) if goal_value not in (None, "") else _money_to_cents(goal_cents_value)

    return {
        "campaign_slug": campaign_slug,
        "organization_name": _clean(payload.get("organization_name")),
        "organization_type": _clean(payload.get("organization_type")),
        "campaign_name": _clean(payload.get("campaign_name")),
        "location": _clean(payload.get("location")),
        "goal": _clean(goal_value),
        "goal_cents": goal_cents,
        "launch_window": _clean(payload.get("launch_window")),
        "primary_audience": _clean(payload.get("primary_audience")),
        "operator_email": _clean(payload.get("operator_email")).lower(),
        "support_story": _clean(payload.get("support_story")),
        "campaign_summary": _clean(payload.get("campaign_summary")),
        "primary_sponsor_package": _clean(payload.get("primary_sponsor_package")),
        "payment_stack": _clean(payload.get("payment_stack")),
        "launch_notes": _clean(payload.get("launch_notes")),
        "readiness_score": _clamp(_int(payload.get("readiness_score"), 0)),
        "status": _clean(payload.get("status"), "draft"),
        "source": _clean(payload.get("source"), "platform_onboarding"),
    }


@dataclass(slots=True)
class CampaignSetupRepository:
    """Persistence boundary for FutureFunded campaign setup records."""

    def ensure_table(self) -> None:
        session = get_db_session()

        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ff_campaign_setups (
                    setup_id VARCHAR(64) PRIMARY KEY,
                    campaign_slug VARCHAR(160) NOT NULL,
                    organization_name VARCHAR(255) NOT NULL DEFAULT '',
                    organization_type VARCHAR(120) NOT NULL DEFAULT '',
                    campaign_name VARCHAR(255) NOT NULL DEFAULT '',
                    location VARCHAR(255) NOT NULL DEFAULT '',
                    goal_cents INTEGER NOT NULL DEFAULT 0,
                    operator_email VARCHAR(255) NOT NULL DEFAULT '',
                    primary_sponsor_package VARCHAR(255) NOT NULL DEFAULT '',
                    payment_stack VARCHAR(255) NOT NULL DEFAULT '',
                    readiness_score INTEGER NOT NULL DEFAULT 0,
                    status VARCHAR(40) NOT NULL DEFAULT 'draft',
                    source VARCHAR(80) NOT NULL DEFAULT 'platform_onboarding',
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # SQLite/dev self-heal for partially-created tables.
        bind_name = session.get_bind().dialect.name
        if bind_name == "sqlite":
            existing = {
                row[1]
                for row in session.execute(text("PRAGMA table_info(ff_campaign_setups)")).all()
            }

            columns = {
                "organization_type": "ALTER TABLE ff_campaign_setups ADD COLUMN organization_type VARCHAR(120) NOT NULL DEFAULT ''",
                "primary_sponsor_package": "ALTER TABLE ff_campaign_setups ADD COLUMN primary_sponsor_package VARCHAR(255) NOT NULL DEFAULT ''",
                "payment_stack": "ALTER TABLE ff_campaign_setups ADD COLUMN payment_stack VARCHAR(255) NOT NULL DEFAULT ''",
                "readiness_score": "ALTER TABLE ff_campaign_setups ADD COLUMN readiness_score INTEGER NOT NULL DEFAULT 0",
                "status": "ALTER TABLE ff_campaign_setups ADD COLUMN status VARCHAR(40) NOT NULL DEFAULT 'draft'",
                "source": "ALTER TABLE ff_campaign_setups ADD COLUMN source VARCHAR(80) NOT NULL DEFAULT 'platform_onboarding'",
                "payload_json": "ALTER TABLE ff_campaign_setups ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'",
                "created_at": "ALTER TABLE ff_campaign_setups ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "ALTER TABLE ff_campaign_setups ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            }

            for name, ddl in columns.items():
                if name not in existing:
                    session.execute(text(ddl))

        session.commit()

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_table()

        session = get_db_session()
        setup_id = uuid4().hex
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)

        try:
            session.execute(
                text(
                    """
                    INSERT INTO ff_campaign_setups (
                        setup_id,
                        campaign_slug,
                        organization_name,
                        organization_type,
                        campaign_name,
                        location,
                        goal_cents,
                        operator_email,
                        primary_sponsor_package,
                        payment_stack,
                        readiness_score,
                        status,
                        source,
                        payload_json
                    )
                    VALUES (
                        :setup_id,
                        :campaign_slug,
                        :organization_name,
                        :organization_type,
                        :campaign_name,
                        :location,
                        :goal_cents,
                        :operator_email,
                        :primary_sponsor_package,
                        :payment_stack,
                        :readiness_score,
                        :status,
                        :source,
                        :payload_json
                    )
                    """
                ),
                {
                    "setup_id": setup_id,
                    "campaign_slug": payload["campaign_slug"],
                    "organization_name": payload["organization_name"],
                    "organization_type": payload["organization_type"],
                    "campaign_name": payload["campaign_name"],
                    "location": payload["location"],
                    "goal_cents": payload["goal_cents"],
                    "operator_email": payload["operator_email"],
                    "primary_sponsor_package": payload["primary_sponsor_package"],
                    "payment_stack": payload["payment_stack"],
                    "readiness_score": payload["readiness_score"],
                    "status": payload["status"],
                    "source": payload["source"],
                    "payload_json": payload_json,
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        return self.get(setup_id) or {"setup_id": setup_id, **payload}

    def get(self, setup_id: str) -> dict[str, Any] | None:
        self.ensure_table()

        row = (
            get_db_session()
            .execute(
                text(
                    """
                    SELECT *
                    FROM ff_campaign_setups
                    WHERE setup_id = :setup_id
                    """
                ),
                {"setup_id": setup_id},
            )
            .mappings()
            .first()
        )

        return dict(row) if row else None

    def latest_for_campaign(self, campaign_slug: str) -> dict[str, Any] | None:
        self.ensure_table()

        row = (
            get_db_session()
            .execute(
                text(
                    """
                    SELECT *
                    FROM ff_campaign_setups
                    WHERE campaign_slug = :campaign_slug
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT 1
                    """
                ),
                {"campaign_slug": campaign_slug},
            )
            .mappings()
            .first()
        )

        return dict(row) if row else None


def campaign_setup_to_form_payload(setup: dict[str, Any] | None) -> dict[str, Any]:
    """Map a saved setup row back into onboarding form field names."""
    if not setup:
        return {}

    payload: dict[str, Any] = {}

    raw_payload = setup.get("payload_json")
    if raw_payload:
        try:
            decoded = json.loads(str(raw_payload))
            if isinstance(decoded, dict):
                payload.update(decoded)
        except Exception:
            pass

    goal_cents = _int(setup.get("goal_cents"), 0)
    fallback_goal = f"${goal_cents / 100:,.0f}" if goal_cents > 0 else ""

    payload.update(
        {
            "setup_id": _clean(setup.get("setup_id")),
            "campaign_slug": _clean(setup.get("campaign_slug"), DEFAULT_CAMPAIGN_SLUG),
            "organization_name": _clean(setup.get("organization_name") or payload.get("organization_name")),
            "organization_type": _clean(setup.get("organization_type") or payload.get("organization_type")),
            "campaign_name": _clean(setup.get("campaign_name") or payload.get("campaign_name")),
            "location": _clean(setup.get("location") or payload.get("location")),
            "goal": _clean(payload.get("goal"), fallback_goal),
            "operator_email": _clean(setup.get("operator_email") or payload.get("operator_email")),
            "primary_sponsor_package": _clean(
                setup.get("primary_sponsor_package") or payload.get("primary_sponsor_package")
            ),
            "payment_stack": _clean(setup.get("payment_stack") or payload.get("payment_stack")),
            "readiness_score": _int(setup.get("readiness_score"), _int(payload.get("readiness_score"), 0)),
            "status": _clean(setup.get("status") or payload.get("status"), "draft"),
            "created_at": _clean(setup.get("created_at")),
            "updated_at": _clean(setup.get("updated_at")),
        }
    )

    return payload


def _setup_list_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = campaign_setup_to_form_payload(row)

    return {
        "setup_id": payload.get("setup_id", ""),
        "campaign_slug": payload.get("campaign_slug", DEFAULT_CAMPAIGN_SLUG),
        "campaign_name": payload.get("campaign_name", ""),
        "organization_name": payload.get("organization_name", ""),
        "location": payload.get("location", ""),
        "goal": payload.get("goal", ""),
        "readiness_score": payload.get("readiness_score", 0),
        "status": payload.get("status", "draft"),
        "created_at": payload.get("created_at", ""),
        "updated_at": payload.get("updated_at", ""),
    }


# Attach after class definition to keep older imports stable.
def _list_for_campaign(self: CampaignSetupRepository, campaign_slug: str, *, limit: int = 12) -> list[dict[str, Any]]:
    self.ensure_table()

    safe_limit = max(1, min(int(limit or 12), 50))

    rows = (
        get_db_session()
        .execute(
            text(
                """
                SELECT *
                FROM ff_campaign_setups
                WHERE campaign_slug = :campaign_slug
                ORDER BY updated_at DESC, created_at DESC
                LIMIT :limit
                """
            ),
            {"campaign_slug": campaign_slug, "limit": safe_limit},
        )
        .mappings()
        .all()
    )

    return [_setup_list_row(dict(row)) for row in rows]


CampaignSetupRepository.list_for_campaign = _list_for_campaign


def _update_status(self: CampaignSetupRepository, setup_id: str, status: str) -> dict[str, Any] | None:
    """Update a saved setup workflow status."""
    safe_setup_id = _clean(setup_id)
    safe_status = normalize_setup_status(status)

    if not safe_setup_id:
        return None

    self.ensure_table()

    session = get_db_session()

    try:
        result = session.execute(
            text(
                """
                UPDATE ff_campaign_setups
                SET status = :status,
                    updated_at = CURRENT_TIMESTAMP
                WHERE setup_id = :setup_id
                """
            ),
            {
                "setup_id": safe_setup_id,
                "status": safe_status,
            },
        )

        if result.rowcount == 0:
            session.rollback()
            return None

        session.commit()
    except Exception:
        session.rollback()
        raise

    return self.get(safe_setup_id)


CampaignSetupRepository.update_status = _update_status

