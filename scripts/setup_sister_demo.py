#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import secrets
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Allow running as: python scripts/setup_sister_demo.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from werkzeug.security import generate_password_hash

from apps.web.app import create_app
from apps.web.app.blueprints.platform.setup_repository import (
    CampaignSetupRepository,
    normalize_onboarding_payload,
)


DEFAULT_EMAIL = "arodgps@gmail.com"
DEFAULT_NAME = "Angel Test Operator"
DEFAULT_CAMPAIGN_SLUG = "connect-atx-elite"
DEFAULT_CAMPAIGN_NAME = "Connect ATX Elite Season Fund"


def clean(value: Any, default: str = "") -> str:
    return str(value or "").strip() or default


def operator_auth_db_path(app) -> Path:
    configured = app.config.get("FF_OPERATOR_AUTH_DATABASE_PATH") or os.getenv(
        "FF_OPERATOR_AUTH_DATABASE_PATH",
        "",
    )

    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else REPO_ROOT / path

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "ff_operator_auth.sqlite3"


def ensure_operator_user(app, *, email: str, name: str, password: str, role: str) -> None:
    db_path = operator_auth_db_path(app)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ff_operator_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'organizer',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT
            )
            """
        )

        password_hash = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO ff_operator_users (
                email,
                name,
                password_hash,
                role,
                is_active
            )
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                password_hash = excluded.password_hash,
                role = excluded.role,
                is_active = 1
            """,
            (email.lower(), name, password_hash, role),
        )

        conn.commit()
    finally:
        conn.close()


def seed_campaign_setup(
    *,
    campaign_slug: str,
    campaign_name: str,
    operator_email: str,
    force_seed: bool,
) -> dict[str, Any] | None:
    repo = CampaignSetupRepository()
    existing = repo.latest_for_campaign(campaign_slug)

    if existing and not force_seed:
        return existing

    payload = normalize_onboarding_payload(
        {
            "campaign_slug": campaign_slug,
            "organization_name": "Connect ATX Elite",
            "organization_type": "Youth team",
            "campaign_name": campaign_name,
            "location": "Austin, TX",
            "goal": "$20,000",
            "operator_email": operator_email,
            "launch_window": "Before season launch",
            "primary_audience": "Families, alumni, local businesses",
            "support_story": (
                "Travel, training, tournament fees, meals, equipment, "
                "and scholarship support."
            ),
            "campaign_summary": (
                "A sponsor-ready campaign for Connect ATX Elite families, "
                "supporters, and local businesses."
            ),
            "primary_sponsor_package": "Featured Sponsor · $1,500",
            "payment_stack": "Stripe and PayPal",
            "launch_notes": (
                "Review setup, confirm sponsor package, test checkout, "
                "and share when marked launch-ready."
            ),
            "readiness_score": 92,
            "status": "launch_ready",
            "source": "sister_demo_bootstrap",
        },
        default_campaign_slug=campaign_slug,
    )

    return repo.save(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a FutureFunded sister/demo operator account and campaign setup."
    )

    parser.add_argument("--email", default=os.getenv("FF_SISTER_DEMO_EMAIL", DEFAULT_EMAIL))
    parser.add_argument("--name", default=os.getenv("FF_SISTER_DEMO_NAME", DEFAULT_NAME))
    parser.add_argument("--password", default=os.getenv("FF_SISTER_DEMO_PASSWORD", ""))
    parser.add_argument("--role", default="organizer")
    parser.add_argument("--campaign-slug", default=DEFAULT_CAMPAIGN_SLUG)
    parser.add_argument("--campaign-name", default=DEFAULT_CAMPAIGN_NAME)
    parser.add_argument("--base-url", default=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000"))
    parser.add_argument(
        "--force-seed",
        action="store_true",
        help="Create a new launch-ready setup record even if one already exists.",
    )

    args = parser.parse_args()

    password = clean(args.password)
    generated_password = False

    if not password:
        password = secrets.token_urlsafe(14)
        generated_password = True

    app = create_app()

    with app.app_context():
        ensure_operator_user(
            app,
            email=clean(args.email).lower(),
            name=clean(args.name, DEFAULT_NAME),
            password=password,
            role=clean(args.role, "organizer"),
        )

        setup = seed_campaign_setup(
            campaign_slug=clean(args.campaign_slug, DEFAULT_CAMPAIGN_SLUG),
            campaign_name=clean(args.campaign_name, DEFAULT_CAMPAIGN_NAME),
            operator_email=clean(args.email).lower(),
            force_seed=bool(args.force_seed),
        )

    base_url = clean(args.base_url, "http://127.0.0.1:5000").rstrip("/")
    setup_id = clean((setup or {}).get("setup_id"))

    print("\n✅ FutureFunded sister/demo account is ready.\n")
    print("Login")
    print(f"  Email:    {clean(args.email).lower()}")
    print(f"  Password: {password}")
    if generated_password:
        print("  Note: password was generated. Save it now.\n")

    print("URLs")
    print(f"  Login:      {base_url}/platform/login")
    print(f"  Dashboard:  {base_url}/platform/dashboard")
    print(f"  Onboarding: {base_url}/platform/onboarding")
    print(f"  Campaign:   {base_url}/c/{clean(args.campaign_slug, DEFAULT_CAMPAIGN_SLUG)}")

    if setup_id:
        print(f"  Review setup: {base_url}/platform/onboarding?setup_id={setup_id}")

    print("\nSuggested first move")
    print("  Log in, open Dashboard, review Campaign setup records, and mark the active setup Launch-ready or Launched.\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
