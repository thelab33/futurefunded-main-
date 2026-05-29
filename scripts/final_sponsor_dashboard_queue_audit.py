#!/usr/bin/env python3
"""FutureFunded dashboard sponsor queue preview audit."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.campaign_profile import resolve_campaign_profile  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded dashboard sponsor queue audit")
    print("=" * 72)

    partial = REPO_ROOT / "apps/web/app/templates/platform/_sponsor_queue_preview.html"
    dashboard = REPO_ROOT / "apps/web/app/templates/platform/dashboard.html"

    if partial.exists():
        ok("sponsor queue preview partial exists")
    else:
        fail("sponsor queue preview partial missing")

    dashboard_text = dashboard.read_text(errors="ignore")
    if 'platform/_sponsor_queue_preview.html' in dashboard_text:
        ok("dashboard includes sponsor queue preview partial")
    else:
        fail("dashboard missing sponsor queue preview include")

    partial_text = partial.read_text(errors="ignore") if partial.exists() else ""
    for forbidden in ["Connect ATX Elite", "connect-atx-elite", "Austin, TX"]:
        if forbidden in partial_text:
            fail(f"sponsor queue partial hard-codes demo identity: {forbidden}")
        else:
            ok(f"sponsor queue partial avoids hard-coded demo identity: {forbidden}")

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if not token:
        fail("FF_OPERATOR_ACCESS_TOKEN missing; cannot audit dashboard render")
    else:
        app = create_app()
        client = app.test_client()
        res = client.get(f"/platform/dashboard?token={token}", follow_redirects=False)

        if res.status_code == 200:
            ok("dashboard loads with operator token")
            html = res.get_data(as_text=True)

            for term in [
                "Sponsor pipeline",
                "Lead intake",
                "Package validation",
                "Follow-up",
                "Open sponsor path",
                "Sponsor center",
            ]:
                if term in html:
                    ok(f"dashboard renders sponsor queue term: {term}")
                else:
                    fail(f"dashboard missing sponsor queue term: {term}")

            profile = resolve_campaign_profile("connect-atx-elite")
            for package in profile.get("sponsor_packages", [])[:3]:
                name = package.get("label") or package.get("name")
                if name and name in html:
                    ok(f"dashboard sponsor queue renders package: {name}")
                else:
                    fail(f"dashboard sponsor queue missing package: {name}")
        else:
            fail(f"dashboard returned HTTP {res.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR DASHBOARD QUEUE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
