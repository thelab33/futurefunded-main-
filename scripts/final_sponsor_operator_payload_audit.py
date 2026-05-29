#!/usr/bin/env python3
"""FutureFunded sponsor operator payload audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.sponsor_operator_payload import build_sponsor_operator_payload  # noqa: E402
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
    print("\nFutureFunded sponsor operator payload audit")
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
        "message": "Testing sponsor operator payload.",
        "website": "",
    }

    package_metadata = resolve_sponsor_package_metadata(
        form_data,
        campaign_slug="connect-atx-elite",
    )

    payload = build_sponsor_operator_payload(
        form_data,
        package_metadata=package_metadata,
        campaign_slug="connect-atx-elite",
    )

    expected = {
        "package_name": "Featured Sponsor",
        "package_amount": 750,
        "package_key": "featured",
        "business_name": "FutureFunded Test Sponsor",
        "contact_email": "test-sponsor@example.com",
    }

    for key, value in expected.items():
        if payload.get(key) == value:
            ok(f"operator payload normalizes {key} = {value}")
        else:
            fail(f"operator payload {key} mismatch: {payload.get(key)!r}")

    for term in ["logo", "website", "sponsor message", "Approve sponsor placement"]:
        haystack = " ".join(payload.get("next_steps", [])) + " " + payload.get("operator_message", "")
        if term.lower() in haystack.lower():
            ok(f"operator payload includes next-step concept: {term}")
        else:
            fail(f"operator payload missing next-step concept: {term}")

    if "Featured Sponsor" in payload.get("subject", "") and "$750" in payload.get("subject", ""):
        ok("operator payload subject includes package name and amount")
    else:
        fail(f"operator payload subject incomplete: {payload.get('subject')!r}")

    route_path = REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py"
    route_text = route_path.read_text(errors="ignore")

    for term in ["build_sponsor_operator_payload", "futurefunded.sponsor_operator_payload"]:
        if term in route_text:
            ok(f"sponsor route source contains {term}")
        else:
            fail(f"sponsor route source missing {term}")

    app = create_app()
    client = app.test_client()

    res = client.post("/sponsors/lead", data=form_data, follow_redirects=False)

    if res.status_code in {200, 201, 202, 302, 303}:
        ok(f"POST /sponsors/lead still accepts sponsor lead after operator payload wiring: HTTP {res.status_code}")
    else:
        fail(f"POST /sponsors/lead unexpected HTTP {res.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR OPERATOR PAYLOAD AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
