#!/usr/bin/env python3
"""Audit: Campaign Momentum is compact, premium, and free of duplicate CTA baggage."""

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
    print("\nFutureFunded Campaign Momentum premium audit")
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
        "Live campaign signal",
        "data-ff-momentum",
        "ff-momentum--signal",
        "Sponsor-ready",
        "sponsor tiers",
        "Family-safe",
    ]

    for term in required:
        ok(f"premium momentum contains: {term}") if term in section else fail(f"premium momentum missing: {term}")

    banned_in_section = [
        "Support is moving. Join the next wave.",
        "A clean signal layer for donations, sponsors, shares, and season milestones",
        "built to make",
        "feel active, trusted, and sponsor-ready",
        "helps cover tournament-day support",
        "package ready for local partners",
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "ff-momentum__actions",
    ]

    for term in banned_in_section:
        ok(f"momentum section removed baggage: {term}") if term not in section else fail(f"momentum section still contains: {term}")

    # Keep global sponsor/donate behavior elsewhere.
    global_required = [
        "Donate",
        "Sponsor",
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "ff.momentum.js",
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

    print("\n✅ CAMPAIGN MOMENTUM PREMIUM AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
