#!/usr/bin/env python3
"""
FutureFunded route/template proof.

Proves which Flask endpoint and Jinja template each important route renders.
Useful when /, /platform/, onboarding, dashboard, or campaign pages appear to
be serving the wrong template.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Make `apps.web.app` importable when this script is executed from scripts/audit.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import template_rendered  # noqa: E402
from apps.web.app import create_app  # noqa: E402


OUT = ROOT / "audit_outputs" / "route-template-proof"

ROUTES = [
    ("root-home", "/"),
    ("platform-home", "/platform/"),
    ("platform-onboarding", "/platform/onboarding"),
    ("platform-login", "/platform/login"),
    ("platform-dashboard", "/platform/dashboard?access_token=dev-operator-20260529123018"),
    ("campaign-connect-atx", "/c/connect-atx-elite"),
]


def clean_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-")


def extract(pattern: str, html: str) -> str:
    match = re.search(pattern, html, flags=re.I | re.S)
    return match.group(1).strip() if match else ""


def rendered_templates_for(app, client, path: str) -> tuple[int, list[str], str]:
    rendered: list[str] = []

    def record(sender, template, context, **extra):
        rendered.append(template.name or "<unnamed>")

    with template_rendered.connected_to(record, app):
        response = client.get(path, follow_redirects=True)

    html = response.get_data(as_text=True)
    return response.status_code, rendered, html


def route_endpoint_for(app, path: str) -> str:
    split = urlsplit(path)

    try:
        adapter = app.url_map.bind("localhost")
        endpoint, _ = adapter.match(split.path, method="GET")
        return endpoint
    except Exception as exc:
        return f"<no endpoint: {exc}>"


def page_markers(html: str) -> dict[str, str]:
    return {
        "title": extract(r"<title>(.*?)</title>", html),
        "body_class": extract(r"<body[^>]*class=[\"']([^\"']+)[\"']", html),
        "data_page": extract(r"data-ff-page=[\"']([^\"']+)[\"']", html),
        "css": ", ".join(sorted(set(re.findall(r"/static/css/([^\"'?]+)", html)))),
        "js": ", ".join(sorted(set(re.findall(r"/static/js/([^\"'?]+)", html)))),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    app = create_app()
    rows: list[dict[str, str | int]] = []

    with app.test_client() as client:
        for label, path in ROUTES:
            endpoint = route_endpoint_for(app, path)
            status, templates, html = rendered_templates_for(app, client, path)

            html_file = OUT / f"{clean_filename(label)}.html"
            html_file.write_text(html, encoding="utf-8", errors="replace")

            markers = page_markers(html)

            rows.append(
                {
                    "label": label,
                    "path": path,
                    "status": status,
                    "endpoint": endpoint,
                    "templates": " | ".join(templates) if templates else "<none captured>",
                    "title": markers["title"],
                    "data_page": markers["data_page"],
                    "body_class": markers["body_class"],
                    "css": markers["css"],
                    "js": markers["js"],
                    "html_file": str(html_file.relative_to(ROOT)),
                    "bytes": len(html.encode("utf-8")),
                }
            )

    width = {
        "label": max(len("label"), *(len(str(r["label"])) for r in rows)),
        "status": len("status"),
        "bytes": max(len("bytes"), *(len(str(r["bytes"])) for r in rows)),
        "path": max(len("path"), *(len(str(r["path"])) for r in rows)),
        "endpoint": max(len("endpoint"), *(len(str(r["endpoint"])) for r in rows)),
    }

    print("== FutureFunded route/template proof ==")
    print()

    header = (
        f"{'label':<{width['label']}}  "
        f"{'status':<{width['status']}}  "
        f"{'bytes':<{width['bytes']}}  "
        f"{'path':<{width['path']}}  "
        f"{'endpoint':<{width['endpoint']}}  "
        f"templates"
    )
    print(header)
    print("-" * len(header))

    for r in rows:
        print(
            f"{str(r['label']):<{width['label']}}  "
            f"{str(r['status']):<{width['status']}}  "
            f"{str(r['bytes']):<{width['bytes']}}  "
            f"{str(r['path']):<{width['path']}}  "
            f"{str(r['endpoint']):<{width['endpoint']}}  "
            f"{r['templates']}"
        )

    print()
    print("== Page markers ==")

    for r in rows:
        print(f"\n[{r['label']}] {r['path']}")
        print(f"  status:     {r['status']}")
        print(f"  bytes:      {r['bytes']}")
        print(f"  endpoint:   {r['endpoint']}")
        print(f"  templates:  {r['templates']}")
        print(f"  title:      {r['title']}")
        print(f"  data-page:  {r['data_page']}")
        print(f"  body class: {r['body_class']}")
        print(f"  css:        {r['css']}")
        print(f"  js:         {r['js']}")
        print(f"  html file:  {r['html_file']}")

    print()
    print(f"✅ wrote rendered HTML snapshots to: {OUT.relative_to(ROOT)}")

    root = next((r for r in rows if r["label"] == "root-home"), None)
    platform = next((r for r in rows if r["label"] == "platform-home"), None)

    if root and platform and root["templates"] == platform["templates"]:
        print()
        print("⚠️ root-home and platform-home rendered the same template.")
        print("   That may be intentional, but it confirms why the two boards look alike.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
