#!/usr/bin/env python3
"""FutureFunded sponsor queue stage update audit."""

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
    print("\nFutureFunded sponsor stage update audit")
    print("=" * 72)

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if not token:
        fail("FF_OPERATOR_ACCESS_TOKEN missing")
        return 1

    app = create_app()
    client = app.test_client()

    unique = uuid.uuid4().hex[:8]
    business_name = f"FutureFunded Stage Test {unique}"

    create_res = client.post(
        "/sponsors/lead",
        data={
            "campaign_slug": "connect-atx-elite",
            "package": "featured",
            "package_key": "featured",
            "package_name": "Tampered Name",
            "package_amount": "1",
            "sponsor_intent": "package",
            "business_name": business_name,
            "contact_name": "FutureFunded Stage Contact",
            "contact_email": f"stage-{unique}@example.com",
            "contact_phone": "512-555-0199",
            "message": "Testing sponsor stage update.",
            "website": "",
        },
        follow_redirects=False,
    )

    if create_res.status_code in {200, 201, 202, 302, 303}:
        ok(f"created sponsor lead for stage update: HTTP {create_res.status_code}")
    else:
        fail(f"sponsor lead create failed: HTTP {create_res.status_code}")
        return 1

    leads = recent_sponsor_leads("connect-atx-elite", limit=25)
    lead = next((item for item in leads if item.get("business_name") == business_name), None)

    if lead and lead.get("id"):
        ok("created sponsor lead has persisted id")
    else:
        fail("created sponsor lead missing persisted id")
        return 1

    lead_id = lead["id"]

    unauthorized = client.post(
        f"/sponsors/lead/{lead_id}/stage",
        data={
            "campaign_slug": "connect-atx-elite",
            "stage": "approved",
        },
        follow_redirects=False,
    )

    if unauthorized.status_code == 403:
        ok("stage update blocks missing operator token")
    else:
        fail(f"stage update without token returned HTTP {unauthorized.status_code}")

    update_res = client.post(
        f"/sponsors/lead/{lead_id}/stage?token={token}",
        data={
            "campaign_slug": "connect-atx-elite",
            "stage": "ready_for_approval",
        },
        follow_redirects=False,
    )

    if update_res.status_code == 200:
        ok("stage update accepts valid operator token")
    else:
        fail(f"stage update with token returned HTTP {update_res.status_code}")

    updated_leads = recent_sponsor_leads("connect-atx-elite", limit=25)
    updated = next((item for item in updated_leads if item.get("id") == lead_id), None)

    if updated and updated.get("stage") == "ready_for_approval":
        ok("repository updates sponsor lead stage")
    else:
        fail(f"repository stage mismatch: {updated}")

    if updated and updated.get("status") == "review":
        ok("repository updates sponsor lead status for review stage")
    else:
        fail(f"repository status mismatch: {updated}")

    dashboard = client.get(f"/platform/dashboard?token={token}", follow_redirects=False)
    html = dashboard.get_data(as_text=True)

    if dashboard.status_code == 200:
        ok("dashboard loads after stage update")
    else:
        fail(f"dashboard returned HTTP {dashboard.status_code}")

    for term in [business_name, "Ready For Approval", "Update"]:
        if term in html:
            ok(f"dashboard renders stage update term: {term}")
        else:
            fail(f"dashboard missing stage update term: {term}")

    route_text = (REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py").read_text(errors="ignore")
    for term in ["sponsor_lead_stage_update", "update_sponsor_lead_stage"]:
        if term in route_text:
            ok(f"sponsor route contains {term}")
        else:
            fail(f"sponsor route missing {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR STAGE UPDATE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
