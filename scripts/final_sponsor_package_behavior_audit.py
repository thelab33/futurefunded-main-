#!/usr/bin/env python3
"""FutureFunded sponsor package behavior audit."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.campaign_profile import resolve_campaign_profile  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


class SponsorFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_sponsor_form = False
        self.form_fields: dict[str, dict[str, str]] = {}
        self.form_buttons: list[dict[str, str]] = []
        self.package_cards: list[dict[str, str]] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "form" and attrs.get("id") == "sponsor-form":
            self.in_sponsor_form = True

        if self.in_sponsor_form and tag in {"input", "select", "textarea"}:
            name = attrs.get("name", "")
            if name:
                self.form_fields[name] = attrs

        if self.in_sponsor_form and tag == "button":
            self.form_buttons.append(attrs)

        if tag in {"article", "button", "a", "div"}:
            has_package_marker = any(
                key in attrs
                for key in (
                    "data-ff-sponsor-package-card",
                    "data-ff-sponsor-tier",
                    "data-ff-sponsor-package",
                )
            )
            if has_package_marker:
                self.package_cards.append(attrs)

        if tag == "script":
            src = attrs.get("src", "")
            if src:
                self.scripts.append(src)

    def handle_endtag(self, tag):
        if tag == "form" and self.in_sponsor_form:
            self.in_sponsor_form = False


def main() -> int:
    print("\nFutureFunded sponsor package behavior audit")
    print("=" * 72)

    profile = resolve_campaign_profile("connect-atx-elite")
    packages = profile.get("sponsor_packages", [])

    if packages:
        ok(f"campaign profile exposes {len(packages)} sponsor packages")
    else:
        fail("campaign profile exposes no sponsor packages")

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)

    if res.status_code == 200:
        ok("/c/connect-atx-elite loads")
    else:
        fail(f"/c/connect-atx-elite returned HTTP {res.status_code}")
        return 1

    html = res.get_data(as_text=True)
    parser = SponsorFormParser()
    parser.feed(html)

    required_fields = [
        "package",
        "package_key",
        "package_name",
        "package_amount",
        "sponsor_intent",
    ]

    for field in required_fields:
        if field in parser.form_fields:
            ok(f"#sponsor-form has field: {field}")
        else:
            fail(f"#sponsor-form missing field: {field}")

    submit_count = sum(
        1
        for button in parser.form_buttons
        if button.get("type", "").lower() in {"", "submit"}
    )

    if submit_count:
        ok("#sponsor-form has submit control")
    else:
        fail("#sponsor-form missing submit control")

    if parser.package_cards:
        ok(f"campaign page exposes {len(parser.package_cards)} sponsor package selectable element(s)")
    else:
        fail("campaign page exposes no sponsor package selectable elements")

    if any("ff.sponsor-packages.js" in src for src in parser.scripts):
        ok("campaign page includes ff.sponsor-packages.js")
    else:
        fail("campaign page missing ff.sponsor-packages.js")

    js_path = REPO_ROOT / "apps/web/app/static/js/ff.sponsor-packages.js"

    if js_path.exists():
        js = js_path.read_text()
        ok("sponsor package JS file exists")

        for token in [
            "futurefunded:sponsor-package-selected",
            "package_key",
            "package_name",
            "package_amount",
        ]:
            if token in js:
                ok(f"sponsor package JS contains {token}")
            else:
                fail(f"sponsor package JS missing {token}")
    else:
        fail("sponsor package JS file missing")

    template_path = REPO_ROOT / "apps/web/app/templates/campaign_premium.html"
    template = template_path.read_text(errors="ignore")

    hardcoded_terms = [
        "package_key",
        "package_name",
        "package_amount",
    ]

    for term in hardcoded_terms:
        if term in template:
            ok(f"campaign template includes sponsor metadata term: {term}")
        else:
            fail(f"campaign template missing sponsor metadata term: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR PACKAGE BEHAVIOR AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
