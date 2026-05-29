#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import json
import time
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TOKEN = os.environ.get("FF_OPERATOR_ACCESS_TOKEN", "").strip()
STAMP = f"dom-{int(time.time())}"

OUT_DIR = Path("audit_outputs/live-dom-inventory") / STAMP
LATEST = Path("audit_outputs/live-dom-inventory/latest")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = [
    ("platform", "/platform/"),
    ("campaign", "/c/connect-atx-elite"),
    ("login", "/platform/login"),
    ("onboarding", "/platform/onboarding"),
    ("dashboard-locked", "/platform/dashboard"),
]

if TOKEN:
    ROUTES.append(("dashboard-token", f"/platform/dashboard?access_token={TOKEN}"))

EXPECTED = {
    "platform": [
        "ff-platformHero",
        "ff-platformHero__grid",
        "ff-platformHero__copy",
        "ff-platformHeroTitle",
        "ff-platformHeroTitle--accented",
        "ff-launchCard",
        "ff-platformSection",
        "ff-siteHeader--platform",
    ],
    "campaign": [
        "ff-campaignPage",
        "ff-campaignHero",
        "ff-campaignHero__grid",
        "ff-campaignHero__story",
        "ff-heroTitle",
        "ff-donatePanel",
    ],
    "login": [
        "ff-loginAuthority",
        "ff-loginAuthority__stage",
        "ff-loginAuthority__hero",
        "ff-loginAuthority__card",
    ],
    "onboarding": [
        "ff-onboardShell",
        "ff-onboardHeader",
        "ff-onboardHero",
        "ff-onboardForm",
    ],
    "dashboard-locked": [
        "ff-dashboardLockedBody",
        "ff-dashboardLockedShell",
        "ff-dashboardLockedHero",
        "ff-dashboardLockedPanel",
    ],
    "dashboard-token": [
        "ff-dashboardModernBody",
        "ff-dashboardModern",
        "ff-dashboardModern__hero",
        "ff-dashboardModern__panel",
    ],
}

LOCAL_CSS = [
    Path("apps/web/app/static/css/ff.css"),
    Path("apps/web/app/static/css/platform-home.css"),
    Path("apps/web/app/static/css/campaign.css"),
    Path("apps/web/app/static/css/login.css"),
    Path("apps/web/app/static/css/onboarding.css"),
    Path("apps/web/app/static/css/dashboard.css"),
]

TEMPLATE_ROOT = Path("apps/web/app/templates")


def fetch(url: str) -> tuple[int | str, str]:
    try:
        req = Request(url, headers={"User-Agent": "FutureFundedLiveDOMInventory/1.0"})
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


def extract_classes(html: str) -> list[str]:
    found = []
    for _, raw in re.findall(r'class\s*=\s*(["\'])(.*?)\1', html, flags=re.I | re.S):
        found.extend([c.strip() for c in raw.split() if c.strip()])
    return found


def extract_attrs(tag: str) -> dict[str, str]:
    attrs = {}
    for key, _, value in re.findall(r'([:\w-]+)(\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+)))?', tag):
        attrs[key] = value or ""
    return attrs


def get_open_tag(html: str, tag: str) -> str:
    match = re.search(rf"<{tag}\b[^>]*>", html, flags=re.I)
    return match.group(0) if match else ""


def extract_css_links(html: str, base_url: str) -> list[str]:
    links = []
    for tag in re.findall(r"<link\b[^>]*>", html, flags=re.I):
        if "stylesheet" not in tag.lower():
            continue
        m = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
        if m:
            links.append(urljoin(base_url, m.group(1)))
    return links


def extract_data_attrs(html: str) -> Counter:
    return Counter(re.findall(r'\s(data-[\w:-]+)(?:\s*=|\s|>)', html, flags=re.I))


def local_css_text() -> str:
    chunks = []
    for p in LOCAL_CSS:
        if p.exists():
            chunks.append(f"\n/* {p} */\n" + p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def template_locations_for(needle: str) -> list[str]:
    hits = []
    if not TEMPLATE_ROOT.exists():
        return hits
    for p in TEMPLATE_ROOT.rglob("*.html"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if needle in text:
            hits.append(str(p))
    return hits[:12]


def main() -> int:
    css_text = local_css_text()
    results = []
    blockers = []

    for name, path in ROUTES:
        url = route_url(path)
        status, html = fetch(url)
        classes = extract_classes(html)
        counts = Counter(classes)
        unique = sorted(counts)

        html_tag = get_open_tag(html, "html")
        body_tag = get_open_tag(html, "body")
        css_links = extract_css_links(html, url)
        data_attrs = extract_data_attrs(html)

        expected = EXPECTED.get(name, [])
        missing_expected = [c for c in expected if c not in counts]

        for c in missing_expected:
            blockers.append(f"{name}: expected CSS-target class missing from rendered HTML: .{c}")

        ff_classes = [c for c in unique if c.startswith("ff")]
        live_not_in_css = [c for c in ff_classes if f".{c}" not in css_text and c not in css_text]

        top_prefixes = Counter()
        for c in unique:
            prefix = c.split("__", 1)[0].split("--", 1)[0]
            top_prefixes[prefix] += 1

        result = {
            "name": name,
            "url": url,
            "status": status,
            "html_bytes": len(html),
            "html_tag": html_tag,
            "body_tag": body_tag,
            "css_links": css_links,
            "class_count": len(classes),
            "unique_class_count": len(unique),
            "top_classes": counts.most_common(80),
            "ff_classes": ff_classes[:220],
            "top_prefixes": top_prefixes.most_common(60),
            "data_attrs": data_attrs.most_common(80),
            "missing_expected": missing_expected,
            "live_ff_classes_not_found_in_local_css": live_not_in_css[:160],
        }

        (OUT_DIR / f"{name}.html").write_text(html, encoding="utf-8")
        results.append(result)

    md = []
    md.append("# FutureFunded Live DOM Inventory")
    md.append("")
    md.append(f"Base URL: `{BASE_URL}`")
    md.append(f"Stamp: `{STAMP}`")
    md.append("")

    md.append("## Blockers")
    md.append("")
    if blockers:
        md.extend([f"- {b}" for b in blockers])
    else:
        md.append("- No missing expected classes.")
    md.append("")

    for item in results:
        md.append(f"## {item['name']}")
        md.append("")
        md.append(f"URL: `{item['url']}`")
        md.append(f"Status: `{item['status']}`")
        md.append(f"HTML bytes: `{item['html_bytes']}`")
        md.append(f"Class instances: `{item['class_count']}`")
        md.append(f"Unique classes: `{item['unique_class_count']}`")
        md.append("")
        md.append("### HTML tag")
        md.append("")
        md.append(f"```html\n{item['html_tag']}\n```")
        md.append("")
        md.append("### Body tag")
        md.append("")
        md.append(f"```html\n{item['body_tag']}\n```")
        md.append("")
        md.append("### Stylesheets")
        md.append("")
        for href in item["css_links"]:
            md.append(f"- `{href}`")
        md.append("")
        md.append("### Missing expected CSS-target classes")
        md.append("")
        if item["missing_expected"]:
            for c in item["missing_expected"]:
                locs = template_locations_for(c)
                suffix = f" | template refs: {', '.join(locs)}" if locs else " | template refs: none"
                md.append(f"- `.{c}`{suffix}")
        else:
            md.append("- None")
        md.append("")
        md.append("### Actual ff* classes rendered")
        md.append("")
        if item["ff_classes"]:
            for c in item["ff_classes"]:
                md.append(f"- `.{c}`")
        else:
            md.append("- No `ff*` classes rendered.")
        md.append("")
        md.append("### ff* classes rendered but not found in local CSS")
        md.append("")
        if item["live_ff_classes_not_found_in_local_css"]:
            for c in item["live_ff_classes_not_found_in_local_css"]:
                md.append(f"- `.{c}`")
        else:
            md.append("- None")
        md.append("")
        md.append("### Top class prefixes")
        md.append("")
        for prefix, count in item["top_prefixes"]:
            md.append(f"- `{prefix}`: {count}")
        md.append("")
        md.append("### Data attributes")
        md.append("")
        for attr, count in item["data_attrs"]:
            md.append(f"- `{attr}`: {count}")
        md.append("")

    (OUT_DIR / "live-dom-inventory.md").write_text("\n".join(md), encoding="utf-8")
    (OUT_DIR / "live-dom-inventory.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    if LATEST.exists():
        shutil.rmtree(LATEST)
    shutil.copytree(OUT_DIR, LATEST)

    print()
    print("================================================")
    print("FutureFunded Live DOM Inventory")
    print("================================================")
    print(f"Report: {OUT_DIR / 'live-dom-inventory.md'}")
    print(f"Latest: {LATEST}")
    print()
    print("Blockers:")
    if blockers:
        for b in blockers:
            print(f"- {b}")
    else:
        print("- No missing expected classes.")
    print()
    print("Quick class summary:")
    for item in results:
        print(f"\n[{item['name']}] status={item['status']} unique_classes={item['unique_class_count']}")
        print("body:", item["body_tag"][:220].replace("\n", " "))
        print("top prefixes:", ", ".join(f"{p}:{n}" for p, n in item["top_prefixes"][:12]))
        print("first ff classes:", ", ".join(item["ff_classes"][:40]) if item["ff_classes"] else "none")

    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
