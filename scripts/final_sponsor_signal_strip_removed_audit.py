#!/usr/bin/env python3
"""Audit: Sponsor Signal panel is removed while sponsor contract stays intact."""

from __future__ import annotations

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


def main() -> int:
    print("\nFutureFunded sponsor signal strip removal audit")
    print("=" * 72)

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = res.get_data(as_text=True)

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")

    required = [
        'id="sponsor-form"',
        'data-ff-sponsor-form',
        'data-ff-sponsor-package-input',
        'data-ff-sponsor-package-key-input',
        'data-ff-sponsor-package-name-input',
        'data-ff-sponsor-package-amount-input',
        'name="sponsor_intent"',
        'data-ff-sponsor-submit',
        'ff-sponsorForm--contractOnly',
        'ff-sponsorForm__submit--contract',
    ]

    for term in required:
        ok(f"sponsor contract still present: {term}") if term in html else fail(f"sponsor contract missing: {term}")

    banned = [
        "Sponsor Signal",
        "Selected package: choose above",
        "FutureFunded carries the package, amount, and sponsor intent",
        "sponsor follow-up stays clean",
        "Sponsor placements stay reviewed before public recognition",
        "This keeps the campaign premium, family-safe, and sellable",
        "ff-sponsorConfirmStrip",
        "ff-sponsorConfirmStrip__copy",
        "ff-sponsorConfirmStrip__microcopy",
    ]

    for term in banned:
        ok(f"removed visible sponsor signal copy: {term}") if term not in html else fail(f"still rendered: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR SIGNAL STRIP REMOVAL AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
