#!/usr/bin/env python3
"""Audit: FAQ renders as a bare-minimal donor confidence checkpoint."""

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


def extract_faq(html: str) -> str:
    match = re.search(
        r'<section\b[^>]*\bid=["\']faq["\'][^>]*>[\s\S]*?</section>',
        html,
        flags=re.IGNORECASE,
    )
    return match.group(0) if match else ""


def main() -> int:
    print("\nFutureFunded minimal FAQ audit")
    print("=" * 72)

    css = read(ROOT / "apps/web/app/static/css/ff.css")

    for term in [
        "FutureFunded Minimal FAQ v2",
        ".ff-faqMini",
        ".ff-faqMini__list",
        ".ff-faqMiniItem",
    ]:
        ok(f"CSS contains {term}") if term in css else fail(f"CSS missing {term}")

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = res.get_data(as_text=True)
    faq = extract_faq(html)

    ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")
    ok("#faq section renders") if faq else fail("#faq section missing")

    required = [
        "Quick answers",
        "The essentials before you give.",
        "Simple answers for donors, parents, and sponsors.",
        "ff-faqMini",
        "Where does the money go?",
        "Is checkout secure?",
        "How do sponsors work?",
    ]

    for term in required:
        ok(f"minimal FAQ contains {term}") if term in faq else fail(f"minimal FAQ missing {term}")

    banned_in_faq = [
        "Trust center",
        "Give with clarity.",
        "ff-faqLive",
        "ff-faqLive__statusGrid",
        "ff-faqLiveDecision",
        "Secure checkout</strong>",
        "Receipt-ready",
        "Reviewed sponsors",
        "Still deciding?",
        "Share campaign",
        "Contact",
        "Can I share this with someone else?",
        "Donate now",
        "Sponsor next",
        "Become a sponsor",
        "data-ff-open-checkout",
        "data-ff-open-sponsor",
        "data-ff-donate-trigger",
        "data-ff-sponsor-trigger",
        "sponsor@futurefunded.com",
    ]

    for term in banned_in_faq:
        ok(f"minimal FAQ removed clutter: {term}") if term not in faq else fail(f"minimal FAQ still contains clutter: {term}")

    global_required = [
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-submit",
        "Live campaign signal",
        "Momentum is building.",
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

    print("\n✅ MINIMAL FAQ AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
