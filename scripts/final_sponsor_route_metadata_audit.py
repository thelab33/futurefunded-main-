#!/usr/bin/env python3
"""FutureFunded sponsor route metadata audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded sponsor route metadata audit")
    print("=" * 72)

    route_path = REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py"
    text = route_path.read_text(errors="ignore")

    required_route_terms = [
        "resolve_sponsor_package_metadata",
        "futurefunded.sponsor_package_metadata",
        "request.form",
        "campaign_slug",
    ]

    for term in required_route_terms:
        if term in text:
            ok(f"sponsor route source contains {term}")
        else:
            fail(f"sponsor route source missing {term}")

    metadata_service = REPO_ROOT / "apps/web/app/services/sponsor_package_metadata.py"
    service_text = metadata_service.read_text(errors="ignore") if metadata_service.exists() else ""

    required_metadata_terms = [
        "package_key",
        "package_name",
        "package_amount",
        "package_validated",
        "campaign_profile",
    ]

    for term in required_metadata_terms:
        if term in service_text:
            ok(f"sponsor metadata service contains {term}")
        else:
            fail(f"sponsor metadata service missing {term}")

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

            # Required sponsor lead contract from sponsors/services.py
            "business_name": "FutureFunded Test Sponsor",
            "contact_name": "FutureFunded Test Contact",
            "contact_email": "test-sponsor@example.com",
            "contact_phone": "512-555-0199",
            "message": "Testing sponsor package route metadata.",

            # Keep honeypot intentionally blank.
            "website": "",
        },
        follow_redirects=False,
    )

    # Successful lead creation may return JSON 200/201 or redirect 302 depending on existing route behavior.
    if res.status_code in {200, 201, 202, 302, 303}:
        ok(f"POST /sponsors/lead accepts sponsor package metadata: HTTP {res.status_code}")
    elif res.status_code == 400:
        body = res.get_data(as_text=True)[:500]
        fail(f"POST /sponsors/lead still fails validation: HTTP 400 body={body!r}")
    elif res.status_code < 500:
        ok(f"POST /sponsors/lead avoids server-error with sponsor package metadata: HTTP {res.status_code}")
    else:
        fail(f"POST /sponsors/lead server-error: HTTP {res.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR ROUTE METADATA AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
