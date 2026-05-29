#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
STAMP = f"truthlite-{int(time.time())}"
TOKEN = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()

OUT_DIR = Path("audit_outputs/css-authority-truth-lite") / STAMP
LATEST_DIR = Path("audit_outputs/css-authority-truth-lite/latest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = [
    {
        "name": "platform",
        "path": "/platform/",
        "expected_css": ["ff.css", "platform-home.css"],
        "selectors": [
            ".ff-platformHero",
            ".ff-platformHero__grid",
            ".ff-platformHero__copy",
            ".ff-platformHeroTitle",
            ".ff-platformHeroTitle--accented",
            ".ff-launchCard",
            ".ff-platformSection",
            ".ff-siteHeader--platform",
        ],
    },
    {
        "name": "campaign",
        "path": "/c/connect-atx-elite",
        "expected_css": ["ff.css", "campaign.css"],
        "selectors": [
            ".ff-campaignPage",
            ".ff-campaignHero",
            ".ff-campaignHero__grid",
            ".ff-campaignHero__story",
            ".ff-heroTitle",
            ".ff-donatePanel",
            "[data-ff-open-checkout]",
            "[data-ff-open-sponsor]",
            "[data-ff-share-trigger]",
        ],
    },
    {
        "name": "login",
        "path": "/platform/login",
        "expected_css": ["ff.css", "login.css"],
        "selectors": [
            ".ff-loginAuthority",
            ".ff-loginAuthority__stage",
            ".ff-loginAuthority__hero",
            ".ff-loginAuthority__card",
            "form",
            "button",
        ],
    },
    {
        "name": "onboarding",
        "path": "/platform/onboarding",
        "expected_css": ["ff.css", "onboarding.css"],
        "selectors": [
            ".ff-onboardShell",
            ".ff-onboardHeader",
            ".ff-onboardHero",
            ".ff-onboardForm",
            "form",
            "button",
        ],
    },
    {
        "name": "dashboard-locked",
        "path": "/platform/dashboard",
        "expected_css": ["ff.css", "dashboard.css"],
        "selectors": [
            ".ff-dashboardLockedBody",
            ".ff-dashboardLockedShell",
            ".ff-dashboardLockedHero",
            ".ff-dashboardLockedPanel",
        ],
    },
]

if TOKEN:
    ROUTES.append({
        "name": "dashboard-token",
        "path": f"/platform/dashboard?access_token={TOKEN}",
        "expected_css": ["ff.css", "dashboard.css"],
        "selectors": [
            ".ff-dashboardModernBody",
            ".ff-dashboardModern",
            ".ff-dashboardModern__hero",
            ".ff-dashboardModern__panel",
            "[data-ff-operator-root]",
            "[data-ff-donations-table]",
            "[data-ff-sponsors-list]",
        ],
    })


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "link":
            return
        data = dict(attrs)
        rel = (data.get("rel") or "").lower()
        href = data.get("href") or ""
        if "stylesheet" in rel and href:
            self.links.append(href)


def fetch(url: str) -> tuple[int | str, str]:
    try:
        req = Request(url, headers={"User-Agent": "FutureFundedTruthGateLite/2.0"})
        with urlopen(req, timeout=20) as res:
            return int(res.status), res.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return int(e.code), e.read().decode("utf-8", errors="replace")
    except URLError as e:
        return "URL_ERROR", str(e)
    except Exception as e:
        return "ERROR", repr(e)


def route_url(path: str) -> str:
    sep = "&" if "?" in path else "?"
    return f"{BASE_URL}{path}{sep}css_v={STAMP}"


def extract_classes(html: str) -> set[str]:
    classes: set[str] = set()
    for raw in re.findall(r'class\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', html, flags=re.I | re.S):
        value = raw[0] or raw[1]
        for cls in value.split():
            classes.add(cls.strip())
    return classes


def has_attr(html: str, attr: str) -> bool:
    return bool(re.search(rf'\s{re.escape(attr)}(?:\s*=|\s|>)', html, flags=re.I))


def selector_present(html: str, classes: set[str], selector: str) -> bool:
    selector = selector.strip()

    if "," in selector:
        return any(selector_present(html, classes, part.strip()) for part in selector.split(","))

    if selector.startswith("."):
        return selector[1:] in classes

    if selector.startswith("[") and selector.endswith("]"):
        body = selector[1:-1].strip()
        attr = body.split("=", 1)[0].strip()
        return has_attr(html, attr)

    if selector in {"form", "button", "main", "header", "footer"}:
        return bool(re.search(rf"<{selector}\b", html, flags=re.I))

    return selector in html


def extract_version(css_text: str) -> str:
    match = re.search(r"Version:\s*([^\n\r]+)", css_text)
    return match.group(1).strip() if match else ""


def main() -> int:
    blockers: list[str] = []
    results: list[dict] = []

    for route in ROUTES:
        url = route_url(route["path"])
        status, html = fetch(url)

        parser = LinkParser()
        parser.feed(html)

        css_links = [urljoin(url, href) for href in parser.links]
        classes = extract_classes(html)

        item = {
            "name": route["name"],
            "url": url,
            "status": status,
            "html_bytes": len(html),
            "unique_classes": len(classes),
            "css_links": css_links,
            "selector_results": {},
            "css_asset_results": [],
        }

        if status not in {200, 403}:
            blockers.append(f"{route['name']}: unexpected route status {status}")

        for expected in route["expected_css"]:
            if not any(expected in href for href in css_links):
                blockers.append(f"{route['name']}: expected CSS not loaded: {expected}")

        if not any(STAMP in href for href in css_links):
            blockers.append(f"{route['name']}: css_v={STAMP} did not propagate into stylesheet URLs")

        for selector in route["selectors"]:
            present = selector_present(html, classes, selector)
            item["selector_results"][selector] = present
            if not present:
                blockers.append(f"{route['name']}: selector not found in rendered HTML: {selector}")

        for css_url in css_links:
            css_status, css_text = fetch(css_url)
            item["css_asset_results"].append({
                "url": css_url,
                "status": css_status,
                "bytes": len(css_text),
                "version": extract_version(css_text),
                "has_visual_rhythm_v16": "visual-rhythm-authority-v16" in css_text,
            })

        results.append(item)

    report = []
    report.append("# FutureFunded CSS Authority Truth Gate Lite v2")
    report.append("")
    report.append(f"Base URL: `{BASE_URL}`")
    report.append(f"Stamp: `{STAMP}`")
    report.append("")
    report.append("## Authority blockers")
    report.append("")
    if blockers:
        report.extend([f"- {b}" for b in blockers])
    else:
        report.append("- No authority blockers found.")
    report.append("")

    for item in results:
        report.append(f"## {item['name']}")
        report.append("")
        report.append(f"URL: `{item['url']}`")
        report.append(f"Status: `{item['status']}`")
        report.append(f"HTML bytes: `{item['html_bytes']}`")
        report.append(f"Unique classes: `{item['unique_classes']}`")
        report.append("")
        report.append("### Stylesheets")
        for href in item["css_links"]:
            report.append(f"- `{href}`")
        report.append("")
        report.append("### Selectors")
        for selector, present in item["selector_results"].items():
            report.append(f"- `{selector}`: {'yes' if present else 'NO'}")
        report.append("")
        report.append("### CSS assets")
        for asset in item["css_asset_results"]:
            report.append(f"- `{asset['url']}`")
            report.append(f"  - status: `{asset['status']}`")
            report.append(f"  - bytes: `{asset['bytes']}`")
            report.append(f"  - version: `{asset['version']}`")
            report.append(f"  - visual rhythm v16 marker: `{asset['has_visual_rhythm_v16']}`")
        report.append("")

    md_path = OUT_DIR / "css-authority-truth-lite.md"
    json_path = OUT_DIR / "css-authority-truth-lite.json"
    md_path.write_text("\n".join(report), encoding="utf-8")
    json_path.write_text(json.dumps({"blockers": blockers, "results": results}, indent=2), encoding="utf-8")

    if LATEST_DIR.exists():
        shutil.rmtree(LATEST_DIR)
    shutil.copytree(OUT_DIR, LATEST_DIR)

    print()
    print("================================================")
    print("FutureFunded CSS Authority Truth Gate Lite v2")
    print("================================================")
    print(f"Report: {md_path}")
    print(f"Latest: {LATEST_DIR}")
    print()
    print("Authority blockers:")
    if blockers:
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("- No authority blockers found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
