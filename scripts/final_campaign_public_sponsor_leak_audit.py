#!/usr/bin/env python3
"""Focused audit: no demo/test sponsor identity leaks on public campaign page."""

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
    print("\nFutureFunded public sponsor leak audit")
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

    if res.status_code == 200:
        ok("/c/connect-atx-elite loads")
    else:
        fail(f"/c/connect-atx-elite HTTP {res.status_code}")

    required_terms = [
        "Live campaign signal",
        "data-ff-momentum",
        "ff.momentum.js",
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-package-name-input",
        "data-ff-sponsor-package-amount-input",
        "data-ff-sponsor-submit",
    ]

    for term in required_terms:
        if term in html:
            ok(f"required public contract present: {term}")
        else:
            fail(f"required public contract missing: {term}")

    banned_terms = [
        "FutureFunded Public Sponsor",
        "FutureFunded Public Sponsor ae7dbb3d",
        "ae7dbb3d",
        "Sponsor onboarding",
        "Ready to be recognized?",
        "Pick a package above or email the sponsor team",
        "Sponsors helping move this campaign forward",
    ]

    for term in banned_terms:
        if term not in html:
            ok(f"public campaign does not leak: {term}")
        else:
            fail(f"public campaign still leaks: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PUBLIC SPONSOR LEAK AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
