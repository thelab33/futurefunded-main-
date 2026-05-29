from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "audit_outputs" / "repo-authority"
OUT.mkdir(parents=True, exist_ok=True)

BASE_URL = os.environ.get("FF_VERIFY_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TOKEN = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()

ROUTES = [
    {
        "name": "Platform homepage",
        "url": "/platform/",
        "expected_status": 200,
    },
    {
        "name": "Campaign demo",
        "url": "/c/connect-atx-elite",
        "expected_status": 200,
    },
    {
        "name": "Launch workspace / onboarding",
        "url": "/platform/onboarding",
        "expected_status": 200,
        "token": True,
    },
    {
        "name": "Operator login",
        "url": "/platform/login",
        "expected_status": 200,
    },
    {
        "name": "Protected dashboard",
        "url": "/platform/dashboard",
        "expected_status": 200,
        "token": True,
    },
    {
        "name": "Locked dashboard",
        "url": "/platform/dashboard",
        "expected_status": 403,
    },
]

class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_attrs = {}
        self.body_attrs = {}
        self.links = []
        self.scripts = []
        self.inline_scripts = []
        self.meta = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)

        if tag == "html":
            self.html_attrs.update(data)

        if tag == "body":
            self.body_attrs.update(data)

        if tag == "title":
            self._in_title = True

        if tag == "link":
            self.links.append(data)

        if tag == "script":
            self.scripts.append(data)
            if not data.get("src"):
                self.inline_scripts.append(data)

        if tag == "meta":
            self.meta.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data

def build_url(route: dict) -> str:
    url = urllib.parse.urljoin(BASE_URL + "/", route["url"].lstrip("/"))
    parsed = urllib.parse.urlparse(url)
    qs = dict(urllib.parse.parse_qsl(parsed.query))

    qs["asset_manifest"] = str(int(datetime.now(tz=timezone.utc).timestamp()))

    if route.get("token") and TOKEN:
        qs["operator_token"] = TOKEN

    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(qs)))

def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "FutureFundedRouteAssetManifest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, body

def clean_asset_url(value: str) -> str:
    value = value or ""
    value = value.split("?", 1)[0].split("#", 1)[0]
    return value

def localize_asset(value: str) -> str:
    cleaned = clean_asset_url(value)
    if cleaned.startswith("/static/"):
        return "apps/web/app/static/" + cleaned.removeprefix("/static/")
    if "/static/" in cleaned:
        return "apps/web/app/static/" + cleaned.split("/static/", 1)[1]
    return cleaned

def extract_jinja_template_hints(html: str) -> list[str]:
    hints = []

    markers = {
        "platform-dashboard": "apps/web/app/templates/platform/dashboard.html",
        "platform-dashboard-locked": "apps/web/app/templates/platform/dashboard_locked.html",
        "platform-home": "apps/web/app/templates/platform/index.html",
        "platform-login": "apps/web/app/templates/platform/login.html",
        "platform-onboarding": "apps/web/app/templates/platform/onboarding.html",
    }

    for marker, path in markers.items():
        if marker in html:
            hints.append(path)

    if "ffCampaignConfig" in html or "Fuel the season" in html or "data-ff-page-root" in html:
        hints.append("apps/web/app/templates/campaign/index.html or apps/web/app/templates/campaign_premium.html")

    return sorted(set(hints))

def classify_inline_contracts(html: str) -> list[str]:
    contracts = []
    checks = [
        ("ffCampaignConfig", "Campaign JSON config"),
        ("ffSponsorContract", "Sponsor JSON contract"),
        ("ffSelectors", "Selector contract"),
        ("data-ff-dashboard-hard-noflash", "Dashboard hard no-flash gate"),
        ("data-ff-dashboard-exec-assistant-template", "Dashboard inert Launch Assistant template"),
        ("data-ff-page", "Page identity marker"),
        ("data-ff-surface", "Surface identity marker"),
        ("data-ff-onboard-root", "Onboarding island root"),
        ("data-ff-dashboard-root", "Dashboard root"),
        ("data-ff-login", "Login marker"),
    ]
    for needle, label in checks:
        if needle in html:
            contracts.append(label)
    return contracts

def analyze(route: dict) -> dict:
    url = build_url(route)
    status, html = fetch(url)

    parser = AssetParser()
    parser.feed(html)

    stylesheets = []
    preloads = []

    for link in parser.links:
        href = link.get("href", "")
        rel = " ".join([
            link.get("rel", ""),
            link.get("as", ""),
        ]).lower()

        if "stylesheet" in rel or href.endswith(".css") or ".css?" in href:
            stylesheets.append({
                "href": href,
                "local_path": localize_asset(href),
                "data_attrs": {k: v for k, v in link.items() if k.startswith("data-")},
            })

        if "preload" in rel:
            preloads.append({
                "href": href,
                "local_path": localize_asset(href),
                "as": link.get("as", ""),
            })

    scripts = []
    inline_count = 0
    for script in parser.scripts:
        src = script.get("src", "")
        if src:
            scripts.append({
                "src": src,
                "local_path": localize_asset(src),
                "defer": "defer" in script,
                "type": script.get("type", ""),
                "data_attrs": {k: v for k, v in script.items() if k.startswith("data-")},
            })
        else:
            inline_count += 1

    return {
        "name": route["name"],
        "url": url,
        "path": route["url"],
        "status": status,
        "expected_status": route["expected_status"],
        "status_ok": status == route["expected_status"],
        "title": " ".join(parser.title.split()),
        "html_attrs": parser.html_attrs,
        "body_attrs": parser.body_attrs,
        "template_hints": extract_jinja_template_hints(html),
        "contracts": classify_inline_contracts(html),
        "stylesheets": stylesheets,
        "preloads": preloads,
        "scripts": scripts,
        "inline_script_count": inline_count,
        "css_count": len(stylesheets),
        "js_count": len(scripts),
        "html_bytes": len(html.encode("utf-8")),
    }

def main() -> None:
    records = [analyze(route) for route in ROUTES]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "token_present": bool(TOKEN),
        "routes": records,
    }

    (OUT / "live_route_asset_manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = []
    lines.append("# FutureFunded Live Route Asset Manifest\n")
    lines.append(f"Generated: `{report['generated_at_utc']}`  ")
    lines.append(f"Base URL: `{BASE_URL}`  ")
    lines.append(f"Operator token present: `{bool(TOKEN)}`\n")

    lines.append("## Route summary\n")
    lines.append("| Surface | Path | Status | CSS | JS | Title |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for rec in records:
        status = f"{rec['status']} {'✅' if rec['status_ok'] else '⚠️'}"
        lines.append(
            f"| {rec['name']} | `{rec['path']}` | {status} | "
            f"{rec['css_count']} | {rec['js_count']} | {rec['title']} |"
        )
    lines.append("")

    for rec in records:
        lines.append(f"## {rec['name']}")
        lines.append(f"- **URL:** `{rec['url']}`")
        lines.append(f"- **Status:** `{rec['status']}` expected `{rec['expected_status']}`")
        lines.append(f"- **Title:** `{rec['title']}`")
        lines.append(f"- **HTML attrs:** `{rec['html_attrs']}`")
        lines.append(f"- **Body attrs/classes:** `{rec['body_attrs']}`")
        lines.append("")

        lines.append("### Template hints")
        if rec["template_hints"]:
            for item in rec["template_hints"]:
                lines.append(f"- `{item}`")
        else:
            lines.append("- No template marker detected")
        lines.append("")

        lines.append("### CSS linked")
        if rec["stylesheets"]:
            for item in rec["stylesheets"]:
                lines.append(f"- `{item['local_path']}`")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("### JS linked")
        if rec["scripts"]:
            for item in rec["scripts"]:
                lines.append(f"- `{item['local_path']}`")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("### Inline/config contracts")
        if rec["contracts"]:
            for item in rec["contracts"]:
                lines.append(f"- {item}")
        else:
            lines.append("- None detected")
        lines.append("")

        lines.append(f"### Inline script count: `{rec['inline_script_count']}`")
        lines.append("")

    (OUT / "live_route_asset_manifest.md").write_text("\n".join(lines), encoding="utf-8")

    print("FutureFunded live route asset manifest complete")
    print(f"MD:   {OUT.relative_to(ROOT)}/live_route_asset_manifest.md")
    print(f"JSON: {OUT.relative_to(ROOT)}/live_route_asset_manifest.json")
    print("")
    for rec in records:
        print(
            f"{rec['name']}: status={rec['status']} css={rec['css_count']} "
            f"js={rec['js_count']} title={rec['title']}"
        )

if __name__ == "__main__":
    main()
