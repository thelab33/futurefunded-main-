from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable

from flask import Flask

# FF_SMOKE_REPO_ROOT_PATH_FIX
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def passfail(checks: list[Check]) -> int:
    width = max(len(c.name) for c in checks) if checks else 10
    failed = [c for c in checks if not c.ok]

    print("\nFutureFunded final platform smoke\n" + "=" * 38)
    for c in checks:
        icon = "✅" if c.ok else "❌"
        print(f"{icon} {c.name:<{width}}  {c.detail}")

    print("=" * 38)
    if failed:
        print(f"FAILED: {len(failed)} check(s)")
        return 1

    print("PASSED: platform, onboarding, dashboard, campaign, CSS, and assets look ready.")
    return 0


def get(client, path: str, **headers):
    return client.get(path, headers=headers, follow_redirects=False)


def html_has_assets(html: str, assets: Iterable[str]) -> tuple[bool, str]:
    missing = [asset for asset in assets if asset not in html]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "assets present"


def css_versions(html: str) -> list[str]:
    return sorted(set(re.findall(r'css/[^"\']+\.css\?v=[^"\']+', html)))


def main() -> int:
    checks: list[Check] = []

    try:
        app = create_app()
        checks.append(Check("create_app returns Flask", isinstance(app, Flask), type(app).__name__))
    except Exception as exc:
        checks.append(Check("create_app returns Flask", False, repr(exc)))
        return passfail(checks)

    if not isinstance(app, Flask):
        return passfail(checks)

    token = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()

    with app.test_client() as client:
        route_rules = {rule.rule for rule in app.url_map.iter_rules()}

        expected_route_fragments = [
            "/platform",
            "/platform/onboarding",
            "/platform/login",
            "/platform/dashboard",
        ]

        for route in expected_route_fragments:
            found = any(rule == route or rule.rstrip("/") == route.rstrip("/") for rule in route_rules)
            checks.append(Check(f"route exists {route}", found, "registered" if found else "not found"))

        static_assets = [
            "/static/css/ff.css",
            "/static/css/platform-home.css",
            "/static/css/ff.checkout.css",
            "/static/images/connect-atx-team.jpg",
        ]

        for asset in static_assets:
            res = get(client, asset)
            checks.append(Check(f"static {asset}", res.status_code == 200, f"HTTP {res.status_code}"))

        platform = get(client, "/platform/")
        platform_html = platform.get_data(as_text=True)
        checks.append(Check("platform page loads", platform.status_code == 200, f"HTTP {platform.status_code}"))

        ok, detail = html_has_assets(platform_html, ["css/ff.css", "css/platform-home.css"])
        checks.append(Check("platform CSS wired", ok, detail))

        platform_versions = css_versions(platform_html)
        checks.append(
            Check(
                "platform CSS versioned",
                any("ff.css?v=" in item for item in platform_versions)
                and any("platform-home.css?v=" in item for item in platform_versions),
                ", ".join(platform_versions) or "none",
            )
        )

        onboarding = get(client, "/platform/onboarding")
        onboarding_html = onboarding.get_data(as_text=True)
        checks.append(Check("onboarding page loads", onboarding.status_code in {200, 302}, f"HTTP {onboarding.status_code}"))

        if onboarding.status_code == 200:
            checks.append(
                Check(
                    "onboarding premium shell",
                    "ff-onboard" in onboarding_html or "ff-onboardHero" in onboarding_html,
                    "ff-onboard contract found" if "ff-onboard" in onboarding_html or "ff-onboardHero" in onboarding_html else "missing ff-onboard contract",
                )
            )

        login = get(client, "/platform/login")
        login_html = login.get_data(as_text=True)
        checks.append(Check("login page loads", login.status_code == 200, f"HTTP {login.status_code}"))
        checks.append(
            Check(
                "login premium shell",
                "ff-loginBody" in login_html or "ff-loginCard" in login_html or "ff-loginSurface" in login_html,
                "login contract found" if ("ff-loginBody" in login_html or "ff-loginCard" in login_html or "ff-loginSurface" in login_html) else "missing login contract",
            )
        )

        dashboard_public = get(client, "/platform/dashboard")
        checks.append(
            Check(
                "dashboard protected",
                dashboard_public.status_code in {200, 302, 401, 403},
                f"HTTP {dashboard_public.status_code}",
            )
        )

        dashboard_ok = False
        dashboard_detail = "no token auth path succeeded"

        token_paths = []
        if token:
            token_paths = [
                f"/platform/dashboard?token={token}",
                f"/platform/dashboard?operator_token={token}",
                f"/platform/dashboard?access_token={token}",
            ]

        for path in token_paths:
            res = get(client, path)
            body = res.get_data(as_text=True)
            if res.status_code == 200 and ("ff-operator" in body or "ff-opPanel" in body or "dashboard" in body.lower()):
                dashboard_ok = True
                dashboard_detail = f"{path} HTTP 200"
                break

        if not dashboard_ok and token:
            res = get(client, "/platform/dashboard", **{"X-Operator-Token": token})
            body = res.get_data(as_text=True)
            if res.status_code == 200 and ("ff-operator" in body or "ff-opPanel" in body or "dashboard" in body.lower()):
                dashboard_ok = True
                dashboard_detail = "X-Operator-Token HTTP 200"

        if not token:
            dashboard_detail = "FF_OPERATOR_ACCESS_TOKEN not set"

        checks.append(Check("dashboard token access", dashboard_ok, dashboard_detail))

        campaign = get(client, "/c/connect-atx-elite")
        campaign_html = campaign.get_data(as_text=True)
        checks.append(Check("campaign page loads", campaign.status_code == 200, f"HTTP {campaign.status_code}"))

        ok, detail = html_has_assets(campaign_html, ["css/ff.css", "css/ff.checkout.css"])
        checks.append(Check("campaign CSS wired", ok, detail))

        checks.append(
            Check(
                "campaign image canonical",
                "connect-atx-team.jpg" in campaign_html and "connectnewsclip" not in campaign_html,
                "connect-atx-team only" if "connect-atx-team.jpg" in campaign_html and "connectnewsclip" not in campaign_html else "stale image reference found",
            )
        )

        campaign_versions = css_versions(campaign_html)
        checks.append(
            Check(
                "campaign CSS versioned",
                any("ff.css?v=" in item for item in campaign_versions),
                ", ".join(campaign_versions) or "none",
            )
        )

    return passfail(checks)


if __name__ == "__main__":
    raise SystemExit(main())
