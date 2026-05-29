#!/usr/bin/env python3
"""FutureFunded sponsor lead repository/dashboard audit."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.sponsor_lead_repository import recent_sponsor_leads  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded sponsor lead repository audit")
    print("=" * 72)

    app = create_app()
    client = app.test_client()

    unique = uuid.uuid4().hex[:8]
    business_name = f"FutureFunded Queue Test {unique}"

    res = client.post(
        "/sponsors/lead",
        data={
            "campaign_slug": "connect-atx-elite",
            "package": "featured",
            "package_key": "featured",
            "package_name": "Tampered Name",
            "package_amount": "1",
            "sponsor_intent": "package",
            "business_name": business_name,
            "contact_name": "FutureFunded Queue Contact",
            "contact_email": f"queue-{unique}@example.com",
            "contact_phone": "512-555-0199",
            "message": "Testing sponsor lead repository persistence.",
            "website": "",
        },
        follow_redirects=False,
    )

    if res.status_code in {200, 201, 202, 302, 303}:
        ok(f"POST /sponsors/lead accepts repository test lead: HTTP {res.status_code}")
    else:
        fail(f"POST /sponsors/lead unexpected HTTP {res.status_code}")

    leads = recent_sponsor_leads("connect-atx-elite", limit=20)
    matched = next((lead for lead in leads if lead.get("business_name") == business_name), None)

    if matched:
        ok("repository stores accepted sponsor lead")
    else:
        fail("repository did not store accepted sponsor lead")
        matched = {}

    expected = {
        "package_name": "Featured Sponsor",
        "package_amount": 750,
        "package_key": "featured",
        "status": "new",
        "stage": "logo_needed",
    }

    for key, value in expected.items():
        if matched.get(key) == value:
            ok(f"stored lead normalizes {key} = {value}")
        else:
            fail(f"stored lead {key} mismatch: {matched.get(key)!r}")

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    if not token:
        fail("FF_OPERATOR_ACCESS_TOKEN missing; dashboard render check skipped")
    else:
        dashboard = client.get(f"/platform/dashboard?token={token}", follow_redirects=False)
        html = dashboard.get_data(as_text=True)

        if dashboard.status_code == 200:
            ok("dashboard loads for sponsor queue repository check")
        else:
            fail(f"dashboard returned HTTP {dashboard.status_code}")

        for term in [business_name, "Recent sponsor leads", "Featured Sponsor"]:
            if term in html:
                ok(f"dashboard renders persisted sponsor queue term: {term}")
            else:
                fail(f"dashboard missing persisted sponsor queue term: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR LEAD REPOSITORY AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
