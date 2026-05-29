#!/usr/bin/env python3
"""Audit: Campaign Momentum renders as a premium OS signal strip."""

from __future__ import annotations

import re
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


def extract_momentum_section(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*data-ff-campaign-momentum-section[^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded Campaign Momentum signal strip audit")
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
    section = extract_momentum_section(html)

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")
    ok("momentum section renders") if section else fail("momentum section missing")

    required = [
        "Live campaign signal",
        "Momentum is building.",
        "ff-momentum--signal",
        "ff-momentumSignal__metrics",
        "backers",
        "sponsor tiers",
        "checkout-ready",
        "Sponsor-ready",
        "Family-safe",
        "data-ff-momentum",
    ]

    for term in required:
        ok(f"signal strip contains: {term}") if term in section else fail(f"signal strip missing: {term}")

    banned = [
        "Live proof, without the noise.",
        "quiet pulse of support",
        "Support is moving. Join the next wave.",
        "A clean signal layer",
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "ff-momentum__actions",
    ]

    for term in banned:
        ok(f"signal strip removed baggage: {term}") if term not in section else fail(f"signal strip still contains: {term}")

    global_required = [
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "ff.momentum.js",
        "Donate",
        "Sponsor",
    ]

    for term in global_required:
        ok(f"global campaign contract still present: {term}") if term in html else fail(f"global campaign contract missing: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN MOMENTUM SIGNAL STRIP AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
