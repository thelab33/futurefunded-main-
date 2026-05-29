#!/usr/bin/env python3
"""FutureFunded sponsor confirmation payload/notification audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.sponsor_confirmation_notifications import dispatch_sponsor_confirmation_notification  # noqa: E402
from apps.web.app.services.sponsor_confirmation_payload import build_sponsor_confirmation_payload  # noqa: E402
from apps.web.app.services.sponsor_package_metadata import resolve_sponsor_package_metadata  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded sponsor confirmation audit")
    print("=" * 72)

    form_data = {
        "campaign_slug": "connect-atx-elite",
        "package": "featured",
        "package_key": "featured",
        "package_name": "Tampered Name",
        "package_amount": "1",
        "business_name": "FutureFunded Test Sponsor",
        "contact_name": "FutureFunded Test Contact",
        "contact_email": "test-sponsor@example.com",
        "contact_phone": "512-555-0199",
        "message": "Testing sponsor confirmation.",
        "website": "",
    }

    package_metadata = resolve_sponsor_package_metadata(form_data, campaign_slug="connect-atx-elite")

    payload = build_sponsor_confirmation_payload(
        form_data,
        package_metadata=package_metadata,
        campaign_name="Connect ATX Elite Season Fund",
        team_name="Connect ATX Elite",
        campaign_url="/c/connect-atx-elite",
    )

    expected = {
        "to_email": "test-sponsor@example.com",
        "business_name": "FutureFunded Test Sponsor",
        "package_name": "Featured Sponsor",
        "package_amount": 750,
    }

    for key, value in expected.items():
        if payload.get(key) == value:
            ok(f"confirmation payload normalizes {key} = {value}")
        else:
            fail(f"confirmation payload {key} mismatch: {payload.get(key)!r}")

    for term in ["logo", "website", "sponsor message", "confirm placement"]:
        haystack = " ".join(payload.get("next_steps", [])) + " " + payload.get("body", "")
        if term.lower() in haystack.lower():
            ok(f"confirmation payload includes next-step concept: {term}")
        else:
            fail(f"confirmation payload missing next-step concept: {term}")

    if "Featured Sponsor" in payload.get("subject", "") and "$750" in payload.get("subject", ""):
        ok("confirmation subject includes package name and amount")
    else:
        fail(f"confirmation subject incomplete: {payload.get('subject')!r}")

    result = dispatch_sponsor_confirmation_notification(payload)

    if result.get("status") in {"queued", "skipped"}:
        ok(f"confirmation notification bridge returns safe status: {result.get('status')}")
    else:
        fail(f"confirmation notification bridge returned unsafe status: {result}")

    route_text = (REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py").read_text(errors="ignore")

    for term in [
        "build_sponsor_confirmation_payload",
        "dispatch_sponsor_confirmation_notification",
        "futurefunded.sponsor_confirmation_payload",
        "futurefunded.sponsor_confirmation_notification",
    ]:
        if term in route_text:
            ok(f"sponsor route source contains {term}")
        else:
            fail(f"sponsor route source missing {term}")

    app = create_app()
    client = app.test_client()
    res = client.post("/sponsors/lead", data=form_data, follow_redirects=False)

    if res.status_code in {200, 201, 202, 302, 303}:
        ok(f"POST /sponsors/lead still accepts sponsor lead after confirmation bridge: HTTP {res.status_code}")
    else:
        fail(f"POST /sponsors/lead unexpected HTTP {res.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR CONFIRMATION AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
