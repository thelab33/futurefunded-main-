#!/usr/bin/env python3
"""Audit: Provider Readiness v2 renders actionable launch controls."""

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


def check_panel(html: str, surface: str) -> None:
    required = [
        "data-ff-provider-readiness",
        "data-ff-provider-readiness-v2",
        "Launch controls",
        "Provider setup for a sellable fundraising OS.",
        "launch-critical ready",
        "Launch gate",
        "Operator follow-up",
        "Optional rails",
        "Stripe",
        "PayPal",
        "Email",
        "Public URL",
        "Optional / not enabled",
        "Receipts disabled until SMTP is configured.",
        "Stripe can carry launch without PayPal.",
    ]

    for term in required:
        ok(f"{surface} provider v2 contains {term}") if term in html else fail(f"{surface} provider v2 missing {term}")


def main() -> int:
    print("\nFutureFunded Provider Readiness v2 audit")
    print("=" * 72)

    css = (ROOT / "apps/web/app/static/css/ff.css").read_text(encoding="utf-8", errors="ignore")
    for term in [
        "FutureFunded Provider Readiness v2",
        ".ff-providerReadiness--v2",
        ".ff-providerReadinessV2__summary",
        ".ff-providerReadinessV2__actions",
        'data-provider-state="optional"',
    ]:
        ok(f"CSS/source contains {term}") if term in css or term in (ROOT / "apps/web/app/templates/platform/_provider_readiness_panel.html").read_text(encoding="utf-8", errors="ignore") else fail(f"CSS/source missing {term}")

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
    check_panel(onboarding_html, "onboarding")

    op_token = token()
    if op_token:
        dashboard = client.get(f"/platform/dashboard?token={op_token}", follow_redirects=False)
        dashboard_html = dashboard.get_data(as_text=True)
        ok("/platform/dashboard token access loads") if dashboard.status_code == 200 else fail(f"/platform/dashboard HTTP {dashboard.status_code}")
        check_panel(dashboard_html, "dashboard")
    else:
        ok("operator token not available; dashboard provider v2 check skipped")

    campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
    campaign_html = campaign.get_data(as_text=True)
    ok("/c/connect-atx-elite loads") if campaign.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {campaign.status_code}")
    ok("public campaign does not render provider readiness v2") if "data-ff-provider-readiness-v2" not in campaign_html else fail("public campaign leaked provider readiness v2")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PROVIDER READINESS V2 AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
