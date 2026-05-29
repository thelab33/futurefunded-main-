#!/usr/bin/env python3
"""FutureFunded Campaign Momentum OS audit."""

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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def main() -> int:
    print("\nFutureFunded Campaign Momentum OS audit")
    print("=" * 72)

    partial = ROOT / "apps/web/app/templates/campaign/_campaign_momentum_bar.html"
    css = ROOT / "apps/web/app/static/css/ff.css"
    js = ROOT / "apps/web/app/static/js/ff.momentum.js"
    premium = ROOT / "apps/web/app/templates/campaign_premium.html"
    campaign_index = ROOT / "apps/web/app/templates/campaign/index.html"
    public_sponsor_partial = ROOT / "apps/web/app/templates/campaign/_public_sponsor_recognition.html"

    for path, label in [
        (partial, "momentum partial"),
        (js, "momentum JS"),
        (css, "ff.css"),
    ]:
        ok(f"{label} exists") if path.exists() else fail(f"{label} missing")

    css_text = read(css)
    for term in [
        "FutureFunded Campaign Momentum OS v1",
        ".ff-momentum",
        "ffMomentumMarquee",
        "prefers-reduced-motion",
        ".ff-sponsorConfirmStrip",
    ]:
        ok(f"CSS contains {term}") if term in css_text else fail(f"CSS missing {term}")

    js_text = read(js)
    for term in [
        "data-ff-momentum-paused",
        "futurefunded:sponsor-package-selected",
        "mouseenter",
        "focusin",
    ]:
        ok(f"JS contains {term}") if term in js_text else fail(f"JS missing {term}")

    combined_templates = "\n".join(read(path) for path in [premium, campaign_index])
    ok("campaign template includes momentum partial") if "campaign/_campaign_momentum_bar.html" in combined_templates else fail("campaign template missing momentum partial")
    ok("campaign template includes momentum JS") if "ff.momentum.js" in combined_templates else fail("campaign template missing ff.momentum.js")

    retired_text = read(public_sponsor_partial)
    if public_sponsor_partial.exists():
        ok("public sponsor recognition partial exists as retired/stubbed file")
        if "retired" in retired_text.lower() and "Live campaign signal" in retired_text:
            ok("public sponsor recognition partial is retired")
        else:
            fail("public sponsor recognition partial may still render old sponsor wall")

    for term in [
        "Sponsor onboarding",
        "Ready to be recognized?",
        "Pick a package above or email the sponsor team",
        "Sponsors helping move this campaign forward",
        "FutureFunded Public Sponsor",
            "FutureFunded Public Sponsor ae7dbb3d",
            "ae7dbb3d",
            "Support is moving. Join the next wave.",
            "A clean signal layer for donations, sponsors, shares, and season milestones",
            "helps cover tournament-day support",
            "package ready for local partners",
    ]:
        if term not in combined_templates and term not in retired_text:
            ok(f"legacy public copy removed from templates: {term}")
        else:
            fail(f"legacy public copy still present in templates: {term}")

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        create_app = None

    if create_app:
        app = create_app()
        client = app.test_client()

        asset = client.get("/static/js/ff.momentum.js")
        ok("momentum JS static asset loads") if asset.status_code == 200 else fail(f"momentum JS asset HTTP {asset.status_code}")

        res = client.get("/c/connect-atx-elite", follow_redirects=False)
        html = res.get_data(as_text=True)
        ok("/c/connect-atx-elite loads") if res.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {res.status_code}")

        for term in [
            "Live campaign signal",
            "Momentum is building.",
            "data-ff-momentum",
            "ff.momentum.js",
            "id=\"sponsor-form\"",
            "data-ff-sponsor-package-key-input",
            "data-ff-sponsor-package-name-input",
            "data-ff-sponsor-package-amount-input",
            "data-ff-sponsor-submit",
        ]:
            ok(f"rendered campaign contains {term}") if term in html else fail(f"rendered campaign missing {term}")

        for term in [
            "Sponsor onboarding",
            "Ready to be recognized?",
            "Pick a package above or email the sponsor team",
            "Sponsors helping move this campaign forward",
            "FutureFunded Public Sponsor",
            "FutureFunded Public Sponsor ae7dbb3d",
            "ae7dbb3d",
            "Support is moving. Join the next wave.",
            "A clean signal layer for donations, sponsors, shares, and season milestones",
            "helps cover tournament-day support",
            "package ready for local partners",
        ]:
            ok(f"rendered campaign removed {term}") if term not in html else fail(f"rendered campaign still contains {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN MOMENTUM OS AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
