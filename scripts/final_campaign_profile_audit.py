#!/usr/bin/env python3
"""FutureFunded campaign profile resolver audit."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402
from apps.web.app.services.campaign_profile import resolve_campaign_profile  # noqa: E402


PASS: list[str] = []
WARN: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def warn(message: str) -> None:
    WARN.append(message)
    print(f"⚠️  {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded campaign profile audit")
    print("=" * 72)

    profile = resolve_campaign_profile("connect-atx-elite")

    required = [
        "brand_name",
        "team_name",
        "campaign_name",
        "campaign_slug",
        "campaign_url",
        "campaign_public_url",
        "location",
        "organizer_name",
        "goal_amount",
        "raised_amount",
        "donation_amounts",
        "sponsor_packages",
    ]

    for key in required:
        value = profile.get(key)
        if value not in (None, "", [], {}):
            ok(f"profile field present: {key} = {value}")
        else:
            if key in {"sponsor_packages"}:
                warn(f"profile field empty: {key}")
            else:
                fail(f"profile field missing/empty: {key}")

    if profile.get("campaign_slug") == "connect-atx-elite":
        ok("default flagship slug preserved")
    else:
        fail(f"unexpected flagship slug: {profile.get('campaign_slug')}")

    if profile.get("campaign_url") == "/c/connect-atx-elite":
        ok("default flagship campaign URL preserved")
    else:
        fail(f"unexpected campaign URL: {profile.get('campaign_url')}")

    app = create_app()
    client = app.test_client()

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    checks = {
        "/platform/": [profile["team_name"], profile["campaign_url"]],
        "/platform/onboarding": [profile["team_name"], profile["location"]],
    }

    if token:
        checks[f"/platform/dashboard?token={token}"] = [
            profile["team_name"],
            profile["location"],
            profile["campaign_url"],
        ]
    else:
        warn("FF_OPERATOR_ACCESS_TOKEN not set; dashboard rendered identity check skipped")

    for path, needles in checks.items():
        res = client.get(path, follow_redirects=False)

        if res.status_code != 200:
            fail(f"{path} HTTP {res.status_code}")
            continue

        html = res.get_data(as_text=True)

        for needle in needles:
            if str(needle) in html:
                ok(f"{path} renders {needle}")
            else:
                fail(f"{path} missing rendered value: {needle}")

    sponsor_package_names = [
        str(package.get("label") or package.get("name") or "").strip()
        for package in profile.get("sponsor_packages", [])
        if isinstance(package, dict) and (package.get("label") or package.get("name"))
    ]

    if sponsor_package_names:
        sponsor_render_paths = ["/platform/onboarding"]
        if token:
            sponsor_render_paths.append(f"/platform/dashboard?token={token}")

        for path in sponsor_render_paths:
            res = client.get(path, follow_redirects=False)
            html = res.get_data(as_text=True)
            for package_name in sponsor_package_names[:3]:
                if package_name in html:
                    ok(f"{path} renders sponsor package: {package_name}")
                else:
                    fail(f"{path} missing sponsor package: {package_name}")
    else:
        fail("profile sponsor packages unavailable for render audit")

    platform_sources = [
        REPO_ROOT / "apps/web/app/templates/platform",
        REPO_ROOT / "apps/web/app/templates/_base/platform_base.html",
    ]

    hardcoded_terms = [
        "Connect ATX Elite",
        "connect-atx-elite",
        "Austin, TX",
    ]

    source_hits: list[str] = []

    for source in platform_sources:
        files = [source] if source.is_file() else list(source.rglob("*.html"))

        for path in files:
            text = path.read_text(errors="ignore")
            for term in hardcoded_terms:
                if term in text:
                    source_hits.append(f"{path.relative_to(REPO_ROOT)} contains {term}")

    if source_hits:
        for hit in source_hits:
            fail(f"platform source still hard-codes demo identity: {hit}")
    else:
        ok("platform templates are free of hard-coded demo identity")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    if WARN:
        print("\nWarnings:")
        for item in WARN:
            print(f"⚠️  {item}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN PROFILE AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
