#!/usr/bin/env python3
"""FutureFunded public sponsor publishing audit."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.sponsor_lead_repository import (  # noqa: E402
    public_sponsor_recognitions,
    recent_sponsor_leads,
)


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded public sponsor publishing audit")
    print("=" * 72)

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if not token:
        fail("FF_OPERATOR_ACCESS_TOKEN missing")
        return 1

    app = create_app()
    client = app.test_client()

    unique = uuid.uuid4().hex[:8]
    business_name = f"FutureFunded Public Sponsor {unique}"

    create_res = client.post(
        "/sponsors/lead",
        data={
            "campaign_slug": "connect-atx-elite",
            "package": "legacy",
            "package_key": "legacy",
            "package_name": "Tampered Name",
            "package_amount": "1",
            "sponsor_intent": "package",
            "business_name": business_name,
            "contact_name": "FutureFunded Public Contact",
            "contact_email": f"public-{unique}@example.com",
            "contact_phone": "512-555-0199",
            "message": "Proud to support this campaign.",
            "website": "",
        },
        follow_redirects=False,
    )

    if create_res.status_code in {200, 201, 202, 302, 303}:
        ok(f"created sponsor lead for public publishing: HTTP {create_res.status_code}")
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

    pre_public = public_sponsor_recognitions("connect-atx-elite", limit=25)
    if not any(item.get("business_name") == business_name for item in pre_public):
        ok("new sponsor lead is not public before displayed stage")
    else:
        fail("new sponsor lead appeared publicly before displayed stage")

    update_res = client.post(
        f"/sponsors/lead/{lead_id}/stage",
        data={
            "token": token,
            "campaign_slug": "connect-atx-elite",
            "stage": "displayed",
        },
        follow_redirects=False,
    )

    if update_res.status_code == 200:
        ok("stage update moves sponsor to displayed")
    else:
        fail(f"displayed stage update returned HTTP {update_res.status_code}")

    recognitions = public_sponsor_recognitions("connect-atx-elite", limit=25)
    if any(item.get("business_name") == business_name for item in recognitions):
        ok("displayed sponsor appears in public recognition repository")
    else:
        fail("displayed sponsor missing from public recognition repository")

    campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = campaign.get_data(as_text=True)

    if campaign.status_code == 200:
        ok("campaign page loads for sponsor recognition check")
    else:
        fail(f"campaign page returned HTTP {campaign.status_code}")

    for term in [
        business_name,
        "Community sponsors",
        "Sponsors helping move this campaign forward",
        "Legacy Sponsor",
    ]:
        if term in html:
            ok(f"campaign renders public sponsor term: {term}")
        else:
            fail(f"campaign missing public sponsor term: {term}")

    partial = REPO_ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html"
    if partial.exists():
        ok("public sponsor recognition partial exists")
    else:
        fail("public sponsor recognition partial missing")

    context_text = (REPO_ROOT / "apps/web/app/services/platform_context.py").read_text(errors="ignore")
    if "ff_public_sponsor_recognitions" in context_text:
        ok("platform context exposes public sponsor recognitions")
    else:
        fail("platform context missing public sponsor recognitions")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PUBLIC SPONSOR PUBLISHING AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
