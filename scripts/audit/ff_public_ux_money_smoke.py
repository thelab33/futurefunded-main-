#!/usr/bin/env python3
"""
FutureFunded Public UX + Money Smoke Gate

Checks:
- homepage, login, campaign render
- no Jinja leaks / traceback leaks
- required CSS/JS assets are linked and reachable
- interactive elements exist
- required CTAs exist
- public campaign payment hooks exist
- payment config and ledger endpoints respond
- obvious demo/internal language does not leak on platform/login
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List, Tuple


BASE = "http://127.0.0.1:5000"

ROUTES = {
    "platform": "/platform/",
    "login": "/platform/login",
    "campaign": "/c/connect-atx-elite",
}

ENDPOINTS = {
    "payments_config": "/c/connect-atx-elite/payments/config",
    "ledger_summary": "/c/connect-atx-elite/ledger/summary",
}

FORBIDDEN_GLOBAL = [
    "{{",
    "{%",
    "UndefinedError",
    "TemplateNotFound",
    "Traceback",
    "jinja2.exceptions",
    "/static//",
]

FORBIDDEN_PUBLIC_COPY = [
    "Campaign demo",
    "campaign demo",
    "demo campaign",
    "lorem ipsum",
    "TODO",
    "FIXME",
]

REQUIRED = {
    "platform": [
        "platform-public-official-v6",
        "Launch a premium fundraising page",
        "Start a campaign",
        "View live fundraiser",
        "FutureFunded",
        "platform-home.css",
        "ff.css",
    ],
    "login": [
        "login-public-official-v2",
        "data-ff-login-root",
        "data-ff-login-form",
        "Sign in securely",
        "login.css",
    ],
    "campaign": [
        "campaign-official-v5",
        "ffCampaignConfig",
        "data-ff-open-checkout",
        "data-ff-donate-trigger",
        "data-ff-payment-trigger",
        "data-ff-share-trigger",
        "data-ff-sponsor-trigger",
        "campaign.css",
        "ff.css",
    ],
}

MIN_COUNTS = {
    "platform": {"a": 10, "button": 0, "form": 0},
    "login": {"a": 3, "button": 1, "form": 1},
    "campaign": {"a": 8, "button": 6, "form": 1},
}


@dataclass
class PageReport:
    name: str
    path: str
    status: int | None
    body: str
    links: List[str]
    scripts: List[str]
    anchors: int
    buttons: int
    forms: int


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors = 0
        self.buttons = 0
        self.forms = 0
        self.links: List[str] = []
        self.scripts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs}
        if tag == "a":
            self.anchors += 1
        elif tag == "button":
            self.buttons += 1
        elif tag == "form":
            self.forms += 1
        elif tag == "link":
            href = attrs_dict.get("href")
            rel = attrs_dict.get("rel") or ""
            if href and "stylesheet" in rel:
                self.links.append(href)
        elif tag == "script":
            src = attrs_dict.get("src")
            if src:
                self.scripts.append(src)


def fetch(path: str) -> Tuple[int | None, str, str]:
    url = urllib.parse.urljoin(BASE, path)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "FutureFundedPublicUXMoneySmoke/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, res.read().decode("utf-8", "replace"), res.headers.get("content-type", "")
    except Exception as exc:
        return None, str(exc), ""


def absolute_asset_url(asset: str) -> str:
    return urllib.parse.urljoin(BASE, asset)


def parse_page(name: str, path: str) -> PageReport:
    status, body, _ctype = fetch(path)
    parser = SurfaceParser()
    if status == 200:
        parser.feed(body)

    return PageReport(
        name=name,
        path=path,
        status=status,
        body=body,
        links=parser.links,
        scripts=parser.scripts,
        anchors=parser.anchors,
        buttons=parser.buttons,
        forms=parser.forms,
    )


def check_asset(asset: str) -> Tuple[bool, str]:
    status, body, _ctype = fetch(asset)
    if status == 200 and len(body) > 20:
        return True, f"200 {len(body)} bytes"
    return False, f"{status} {len(body)} bytes"


def main() -> int:
    failures: List[str] = []
    reports: Dict[str, PageReport] = {}

    print("\nFutureFunded Public UX + Money Smoke Gate")
    print("=" * 48)

    for name, path in ROUTES.items():
        report = parse_page(name, path)
        reports[name] = report

        print(
            f"\n{name.upper()} {path}\n"
            f"  status:  {report.status}\n"
            f"  bytes:   {len(report.body)}\n"
            f"  anchors: {report.anchors}\n"
            f"  buttons: {report.buttons}\n"
            f"  forms:   {report.forms}"
        )

        if report.status != 200:
            failures.append(f"{name}: expected 200, got {report.status}")
            continue

        for needle in REQUIRED[name]:
            if needle not in report.body:
                failures.append(f"{name}: missing required marker/copy: {needle}")

        for bad in FORBIDDEN_GLOBAL:
            if bad in report.body:
                failures.append(f"{name}: forbidden global token found: {bad}")

        if name in {"platform", "login"}:
            for bad in FORBIDDEN_PUBLIC_COPY:
                if bad in report.body:
                    failures.append(f"{name}: forbidden demo/internal copy found: {bad}")

        counts = MIN_COUNTS[name]
        if report.anchors < counts["a"]:
            failures.append(f"{name}: too few anchors: {report.anchors} < {counts['a']}")
        if report.buttons < counts["button"]:
            failures.append(f"{name}: too few buttons: {report.buttons} < {counts['button']}")
        if report.forms < counts["form"]:
            failures.append(f"{name}: too few forms: {report.forms} < {counts['form']}")

        for asset in report.links + report.scripts:
            if asset.startswith("http"):
                continue
            ok, note = check_asset(asset)
            print(f"  asset: {asset} -> {note}")
            if not ok:
                failures.append(f"{name}: asset not reachable: {asset} -> {note}")

    campaign = reports.get("campaign")
    if campaign and campaign.status == 200:
        checkout_hooks = [
            "data-ff-open-checkout",
            "data-ff-donate-trigger",
            "data-ff-payment-trigger",
            "data-ff-donate-submit",
            "data-ff-checkout-form",
        ]
        for hook in checkout_hooks:
            count = campaign.body.count(hook)
            print(f"  campaign hook {hook}: {count}")
            if count < 1:
                failures.append(f"campaign: missing checkout hook {hook}")

        sponsor_hooks = [
            "data-ff-open-sponsor",
            "data-ff-sponsor-trigger",
            "data-ff-sponsor-package",
        ]
        for hook in sponsor_hooks:
            count = campaign.body.count(hook)
            print(f"  sponsor hook {hook}: {count}")
            if count < 1:
                failures.append(f"campaign: missing sponsor hook {hook}")

        share_hooks = [
            "data-ff-share-trigger",
            "data-ff-qr-trigger",
        ]
        for hook in share_hooks:
            count = campaign.body.count(hook)
            print(f"  share hook {hook}: {count}")
            if count < 1:
                failures.append(f"campaign: missing share hook {hook}")

    print("\nEndpoint checks")
    print("-" * 48)
    for name, path in ENDPOINTS.items():
        status, body, ctype = fetch(path)
        print(f"{name:16} {path:36} status={status} bytes={len(body)} content-type={ctype}")
        if status != 200:
            failures.append(f"endpoint {name}: expected 200, got {status}")
        if name == "payments_config" and status == 200:
            try:
                parsed = json.loads(body)
                if not isinstance(parsed, dict):
                    failures.append("payments_config: response is not a JSON object")
                provider_text = json.dumps(parsed).lower()
                if "stripe" not in provider_text and "paypal" not in provider_text:
                    failures.append("payments_config: no obvious payment provider present")
            except Exception as exc:
                failures.append(f"payments_config: invalid JSON: {exc}")

    print("\nSummary")
    print("-" * 48)

    if failures:
        print("❌ FAIL")
        for item in failures:
            print(f" - {item}")
        return 1

    print("✅ PASS — public UX contracts, assets, hooks, and money endpoints look healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
