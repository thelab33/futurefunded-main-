#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path.cwd()
WEB_ROOT = ROOT / "apps/web"
STATIC_ROOT = WEB_ROOT / "app/static"
OUT = ROOT / "audit_outputs/public-ux-contract"
sys.path.insert(0, str(ROOT.resolve()))
sys.path.insert(0, str(WEB_ROOT.resolve()))

from app import create_app  # noqa: E402

CSS_LINK_RE = re.compile(r"<link\b[^>]*\bhref=[\"']([^\"']+\.css(?:\?[^\"']*)?)[\"'][^>]*>", re.I)
RETIRED = {
    "platform-home.css",
    "login.css",
    "dashboard.css",
    "ff.homepage-flagship.css",
    "ff.campaign-polish.css",
    "ff.operator-dashboard.css",
    "ff.tokens.css",
    "ff.pages.css",
    "ff.base.css",
    "ff.checkout.css",
}

TOKEN_KEYS = [
    "FF_OPERATOR_ACCESS_TOKEN",
    "OPERATOR_TOKEN",
    "FF_OPERATOR_TOKEN",
    "FUTUREFUNDED_OPERATOR_TOKEN",
    "PLATFORM_OPERATOR_TOKEN",
    "DASHBOARD_OPERATOR_TOKEN",
    "ADMIN_OPERATOR_TOKEN",
    "DEMO_OPERATOR_TOKEN",
]

ROUTES = {
    "/platform/": {
        "css": ["apps/web/app/static/css/ff.css"],
        "any": [["FutureFunded", "data-ff-home-root", "ff-platformPage", "ff-home"]],
    },
    "/platform": {
        "css": ["apps/web/app/static/css/ff.css"],
        "any": [["FutureFunded", "data-ff-home-root", "ff-platformPage", "ff-home"]],
    },
    "/c/connect-atx-elite": {
        "css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/campaign.css"],
        "all": [
            "data-ff-page-root",
            "data-ff-open-checkout",
            "data-ff-donate-trigger",
            "data-ff-payment-trigger",
            "data-ff-open-sponsor",
            "data-ff-sponsor-modal",
            "data-ff-share",
            "ffCampaignConfig",
        ],
        "any": [["data-ff-embedded-checkout-shell", "data-ff-checkout-sheet", "ff-embeddedCheckout"]],
    },
    "/platform/login": {
        "css": ["apps/web/app/static/css/ff.css"],
        "any": [["data-ff-login-root", "Login", "Sign in"]],
    },
}


def normalize_static_href(href: str) -> str | None:
    path = unquote(urlparse(href).path)
    if not path.startswith("/static/"):
        return None
    return str((STATIC_ROOT / path.replace("/static/", "", 1)).relative_to(ROOT))


def css_files(html: str) -> list[str]:
    out = []
    for href in CSS_LINK_RE.findall(html):
        rel = normalize_static_href(href)
        if rel and rel not in out:
            out.append(rel)
    return out


def tokens(app) -> list[str]:
    found = []
    for key in TOKEN_KEYS:
        v = os.environ.get(key) or app.config.get(key)
        if v and str(v) not in found:
            found.append(str(v))
    tmp = Path("/tmp/ff_operator_token")
    if tmp.exists():
        v = tmp.read_text(errors="ignore").strip()
        if v and v not in found:
            found.append(v)
    return found


def main() -> int:
    app = create_app()
    errors: list[str] = []
    warnings: list[str] = []
    report = {"routes": {}, "css_health": {}}

    with app.test_client() as client:
        for route, contract in ROUTES.items():
            res = client.get(route)
            html = res.get_data(as_text=True)
            css = css_files(html)
            report["routes"][route] = {"status": res.status_code, "css": css}

            if res.status_code >= 500:
                errors.append(f"FAIL: {route} returned {res.status_code}")

            if res.status_code == 200:
                if css != contract["css"]:
                    errors.append(f"FAIL: {route} CSS stack mismatch. Expected {contract['css']}, got {css}")

                for token in contract.get("all", []):
                    if token not in html:
                        errors.append(f"FAIL: {route} missing required HTML hook/class: {token}")

                for group in contract.get("any", []):
                    if not any(token in html for token in group):
                        errors.append(f"FAIL: {route} missing one of required hook group: {group}")

                for rel in css:
                    if Path(rel).name in RETIRED or ".bak" in rel or "/_quarantine/" in rel:
                        errors.append(f"FAIL: {route} loads retired CSS: {rel}")
                    if not (ROOT / rel).exists():
                        errors.append(f"FAIL: {route} loads missing CSS: {rel}")

        base = "/platform/dashboard"
        rendered = False
        attempts = [(base, base)]
        for t in tokens(app):
            attempts.extend([
                (f"{base}?operator_token={t}", f"{base}?operator_token=<redacted>"),
                (f"{base}?access_token={t}", f"{base}?access_token=<redacted>"),
            ])

        for url, display in attempts:
            res = client.get(url)
            html = res.get_data(as_text=True)
            css = css_files(html)
            report["routes"][display] = {"status": res.status_code, "css": css}
            if res.status_code == 200 and "data-ff-operator-root" in html:
                rendered = True
                if css != ["apps/web/app/static/css/ff.css"]:
                    errors.append(f"FAIL: {display} CSS stack mismatch. Expected ['apps/web/app/static/css/ff.css'], got {css}")
                for token in ["data-ff-operator-root", "data-ff-ledger-url", "data-ff-events-url"]:
                    if token not in html:
                        errors.append(f"FAIL: {display} missing dashboard hook: {token}")
                break

        if not rendered:
            warnings.append("WARN: dashboard stayed auth-protected or token unavailable; operator UI hook check skipped")

    for rel in ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/campaign.css"]:
        p = ROOT / rel
        if not p.exists():
            errors.append(f"FAIL: missing CSS file: {rel}")
            continue
        text = p.read_text(errors="ignore")
        report["css_health"][rel] = {
            "lines": len(text.splitlines()),
            "bytes": p.stat().st_size,
            "important": text.count("!important"),
        }
        if rel.endswith("ff.css"):
            for token in ["FutureFunded", "--ff-font-sans", ".ff-button", ".ff-card"]:
                if token not in text:
                    errors.append(f"FAIL: ff.css missing {token}")
            for required in ["ff-login", "ff-operator", "dashboard", "ff-home"]:
                if required not in text:
                    warnings.append(f"WARN: ff.css may be missing merged surface marker/token: {required}")
        if rel.endswith("campaign.css"):
            for token in [".ff-campaignHero", ".ff-donatePanel", ".ff-shareDrawer", ".ff-sponsorModal", ".ff-checkoutModal"]:
                if token not in text:
                    errors.append(f"FAIL: campaign.css missing {token}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("FutureFunded Frontend Contract Audit")
    print("================================================")
    print("\nRendered route CSS stacks:")
    for route, data in report["routes"].items():
        print(f"\n{route} -> {data['status']}")
        for css in data["css"]:
            print(f"  - {css}")

    print("\nCSS file health:")
    for rel, data in report["css_health"].items():
        print(f"  - {rel}: {data['lines']} lines, {data['bytes']} bytes, {data['important']} !important")

    print("\nWarnings:")
    print("\n".join(warnings) if warnings else "  none")
    print("\nErrors:")
    print("\n".join(errors) if errors else "  none")

    (OUT / "latest.txt").write_text(
        "Errors:\n" + ("\n".join(errors) if errors else "none") + "\n\nWarnings:\n" + ("\n".join(warnings) if warnings else "none") + "\n",
        encoding="utf-8",
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
