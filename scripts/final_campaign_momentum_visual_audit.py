#!/usr/bin/env python3
"""Audit: Campaign Momentum has premium visual console structure."""

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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def extract_momentum_section(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*data-ff-campaign-momentum-section[^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded Campaign Momentum visual console audit")
    print("=" * 72)

    css = read(ROOT / "apps/web/app/static/css/ff.css")
    retired = read(ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html")

    for term in [
        "FutureFunded Campaign Momentum Visual Console v3",
        ".ff-momentum--visualConsole",
        ".ff-momentumConsole",
        ".ff-momentumConsole__metrics",
        "prefers-reduced-motion",
    ]:
        ok(f"CSS contains {term}") if term in css else fail(f"CSS missing {term}")

    if "Retired" in retired and "Campaign Momentum" in retired and "Live campaign signal" in retired:
        ok("public sponsor recognition partial is a safe retired compatibility stub")
    else:
        fail("public sponsor recognition partial is not clearly retired")

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
        "ff-momentum--visualConsole",
        "ff-momentumConsole",
        "ff-momentumConsole__identity",
        "ff-momentumConsole__rail",
        "ff-momentumConsole__metrics",
        "Live campaign signal",
        "Momentum is building.",
        "data-ff-momentum",
        "data-ff-momentum-rail",
    ]

    for term in required:
        ok(f"visual console contains {term}") if term in section else fail(f"visual console missing {term}")

    banned = [
        "Donate now",
        "Sponsor next",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "ff-momentum__actions",
        "Support is moving. Join the next wave.",
        "A clean signal layer",
    ]

    for term in banned:
        ok(f"visual console avoids {term}") if term not in section else fail(f"visual console still contains {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN MOMENTUM VISUAL CONSOLE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
