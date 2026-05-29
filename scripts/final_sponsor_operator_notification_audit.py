#!/usr/bin/env python3
"""FutureFunded sponsor operator notification bridge audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.sponsor_operator_notifications import (  # noqa: E402
    dispatch_sponsor_operator_notification,
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
    print("\nFutureFunded sponsor operator notification audit")
    print("=" * 72)

    payload = {
        "subject": "New sponsor lead: Featured Sponsor — $750",
        "business_name": "FutureFunded Test Sponsor",
        "contact_name": "FutureFunded Test Contact",
        "contact_email": "test-sponsor@example.com",
        "summary": "Featured Sponsor — $750",
        "operator_message": "New sponsor lead: Featured Sponsor — $750",
    }

    result = dispatch_sponsor_operator_notification(payload)

    if result.get("status") in {"queued", "skipped"}:
        ok(f"notification bridge returns safe status: {result.get('status')}")
    else:
        fail(f"notification bridge returned unsafe status: {result}")

    if result.get("subject") == payload["subject"]:
        ok("notification bridge preserves subject")
    else:
        fail(f"notification subject mismatch: {result.get('subject')!r}")

    if result.get("business_name") == payload["business_name"]:
        ok("notification bridge preserves business name")
    else:
        fail(f"notification business mismatch: {result.get('business_name')!r}")

    route_path = REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py"
    route_text = route_path.read_text(errors="ignore")

    for term in [
        "dispatch_sponsor_operator_notification",
        "futurefunded.sponsor_operator_notification",
    ]:
        if term in route_text:
            ok(f"sponsor route source contains {term}")
        else:
            fail(f"sponsor route source missing {term}")

    app = create_app()
    client = app.test_client()

    res = client.post(
        "/sponsors/lead",
        data={
            "campaign_slug": "connect-atx-elite",
            "package": "featured",
            "package_key": "featured",
            "package_name": "Tampered Name",
            "package_amount": "1",
            "sponsor_intent": "package",
            "business_name": "FutureFunded Test Sponsor",
            "contact_name": "FutureFunded Test Contact",
            "contact_email": "test-sponsor@example.com",
            "contact_phone": "512-555-0199",
            "message": "Testing sponsor operator notification bridge.",
            "website": "",
        },
        follow_redirects=False,
    )

    if res.status_code in {200, 201, 202, 302, 303}:
        ok(f"POST /sponsors/lead still accepts sponsor lead after notification bridge: HTTP {res.status_code}")
    else:
        fail(f"POST /sponsors/lead unexpected HTTP {res.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR OPERATOR NOTIFICATION AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
