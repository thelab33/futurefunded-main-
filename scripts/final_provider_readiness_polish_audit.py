#!/usr/bin/env python3
"""Audit: provider readiness panel renders on internal platform surfaces only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def token() -> str:
    env_token = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = Path("/tmp/ff_operator_token")
    return token_file.read_text(encoding="utf-8").strip() if token_file.exists() else ""


def main() -> int:
    print("\nFutureFunded provider readiness polish audit")
    print("=" * 72)

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    onboarding = client.get("/platform/onboarding", follow_redirects=False)
    onboarding_html = onboarding.get_data(as_text=True)

    ok("/platform/onboarding loads") if onboarding.status_code == 200 else fail(f"/platform/onboarding HTTP {onboarding.status_code}")

    for term in [
        "data-ff-provider-readiness",
        "Launch readiness",
        "Provider setup for a sellable fundraising OS.",
        "launch-critical ready",
        "Receipts disabled until SMTP is configured.",
        "Optional / not enabled",
        "Launch controls",
        "Stripe",
        "PayPal",
        "Email",
        "Public URL",
    ]:
        ok(f"onboarding provider panel contains {term}") if term in onboarding_html else fail(f"onboarding missing {term}")

    op_token = token()
    if op_token:
        dashboard = client.get(f"/platform/dashboard?token={op_token}", follow_redirects=False)
        dashboard_html = dashboard.get_data(as_text=True)
        ok("/platform/dashboard token access loads") if dashboard.status_code == 200 else fail(f"/platform/dashboard HTTP {dashboard.status_code}")

        for term in [
            "data-ff-provider-readiness",
            "Launch readiness",
            "Stripe",
            "PayPal",
            "Email",
            "Public URL",
        ]:
            ok(f"dashboard provider panel contains {term}") if term in dashboard_html else fail(f"dashboard missing {term}")
    else:
        ok("operator token not available; dashboard panel check skipped")

    campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
    campaign_html = campaign.get_data(as_text=True)

    ok("/c/connect-atx-elite loads") if campaign.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {campaign.status_code}")
    ok("public campaign does not render provider readiness panel") if "data-ff-provider-readiness" not in campaign_html else fail("public campaign renders provider readiness panel")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PROVIDER READINESS POLISH AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
