#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path.cwd()

DEFAULT_OUT = ROOT.parent / f"futurefunded-active-surface-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"

TARGET_ROUTES = [
    ("platform_home", "/platform/"),
    ("campaign_demo", "/c/connect-atx-elite"),
    ("login", "/platform/login"),
    ("onboarding", "/platform/onboarding"),
    ("dashboard_locked", "/platform/dashboard"),
]

TEMPLATE_PATTERNS = {
    "platform_home": [
        "data-ff-page=\"platform-home\"",
        "ff-platformHomeBody",
        "ff-platformHomePage",
    ],
    "campaign_demo": [
        "data-ff-page=\"campaign\"",
        "ff-campaignBody",
        "ffCampaignConfig",
    ],
    "login": [
        "data-ff-login-template",
        "ff-loginAuthority",
        "platform-login",
    ],
    "onboarding": [
        "platform-onboarding",
        "ff-onboard",
        "data-ff-onboard",
    ],
    "dashboard_private": [
        "data-ff-page=\"platform-dashboard\"",
        "ff-dashboardModernBody",
        "ff-dashboardModern__topbar",
    ],
    "dashboard_locked": [
        "platform-dashboard-locked",
        "ff-dashboardLockedBody",
        "ff-dashboardLockedTopbar",
    ],
}

ALWAYS_KEEP_IF_EXISTS = [
    "README.md",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    ".gitignore",
    "scripts/audit/ff_visual_surface_board.mjs",
    "scripts/audit/ff_header_clip_audit.mjs",
    "scripts/audit/ff_prelive_ui_gate.sh",
]

STATIC_EXTS = {
    ".css", ".js", ".mjs",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico",
    ".json", ".webmanifest",
    ".woff", ".woff2", ".ttf",
}

TEMPLATE_EXTS = {".html", ".jinja", ".jinja2"}


class StaticHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ["href", "src", "poster", "content"]:
            value = attrs.get(key)
            if value:
                self._maybe_add(value)

        srcset = attrs.get("srcset")
        if srcset:
            for part in srcset.split(","):
                self._maybe_add(part.strip().split(" ")[0])

    def _maybe_add(self, value: str):
        value = value.strip()
        if not value:
            return

        if "/static/" in value:
            parsed = urlparse(value)
            path = unquote(parsed.path)
            idx = path.find("/static/")
            if idx != -1:
                rel = path[idx + 1 :]
                self.assets.add(rel)


def run(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def copy_file(src_rel: str, out: Path):
    src = ROOT / src_rel
    if not src.exists() or not src.is_file():
        return False

    dst = out / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def find_templates_by_patterns() -> dict[str, list[str]]:
    template_root = ROOT / "apps/web/app/templates"
    found: dict[str, list[str]] = {k: [] for k in TEMPLATE_PATTERNS}

    if not template_root.exists():
        return found

    for path in template_root.rglob("*"):
        if not path.is_file() or path.suffix not in TEMPLATE_EXTS:
            continue

        text = read(path)
        for surface, patterns in TEMPLATE_PATTERNS.items():
            if any(p in text for p in patterns):
                found[surface].append(rel(path))

    return found


def extract_jinja_deps(template_rel: str) -> set[str]:
    deps = set()
    path = ROOT / template_rel
    if not path.exists():
        return deps

    text = read(path)

    # {% extends "...html" %}, {% include "...html" %}
    for m in re.finditer(r"{%\s*(?:extends|include)\s+[\"']([^\"']+)[\"']", text):
        dep = "apps/web/app/templates/" + m.group(1).lstrip("/")
        if (ROOT / dep).exists():
            deps.add(dep)

    # {% from "...html" import ... %}
    for m in re.finditer(r"{%\s*from\s+[\"']([^\"']+)[\"']", text):
        dep = "apps/web/app/templates/" + m.group(1).lstrip("/")
        if (ROOT / dep).exists():
            deps.add(dep)

    return deps


def recursive_template_deps(seed: set[str]) -> set[str]:
    all_deps = set(seed)
    changed = True

    while changed:
        changed = False
        for item in list(all_deps):
            for dep in extract_jinja_deps(item):
                if dep not in all_deps:
                    all_deps.add(dep)
                    changed = True

    return all_deps


def extract_static_from_template(template_rel: str) -> set[str]:
    path = ROOT / template_rel
    if not path.exists():
        return set()

    text = read(path)
    assets = set()

    # url_for('static', filename='css/ff.css')
    for m in re.finditer(r"url_for\(\s*[\"']static[\"']\s*,\s*filename\s*=\s*[\"']([^\"']+)[\"']", text):
        assets.add("apps/web/app/static/" + m.group(1).lstrip("/"))

    # literal /static/ paths
    for m in re.finditer(r"[\"'](/static/[^\"'#?]+)", text):
        p = m.group(1).lstrip("/")
        assets.add("apps/web/app/" + p)

    return {a for a in assets if (ROOT / a).exists()}


def fetch_url(base_url: str, route: str, token: str = "") -> tuple[int | None, str, str]:
    url = base_url.rstrip("/") + route

    if route == "/platform/dashboard" and token:
        url = url + "?access_token=" + urllib.parse.quote(token)

    req = urllib.request.Request(url, headers={"User-Agent": "FutureFundedActiveSurfaceAudit/1.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, res.read().decode("utf-8", "replace"), url
    except urllib.error.HTTPError as exc:
        # Locked dashboard returns 403 but still may include rendered HTML.
        body = exc.read().decode("utf-8", "replace")
        return exc.code, body, url
    except Exception as exc:
        return None, f"FETCH_ERROR: {exc}", url


def extract_rendered_assets(base_url: str, token: str = "") -> tuple[set[str], list[dict]]:
    assets = set()
    reports = []

    routes = list(TARGET_ROUTES)

    if token:
        routes.append(("dashboard_private", "/platform/dashboard"))

    for name, route in routes:
        status, html, url = fetch_url(base_url, route, token if name == "dashboard_private" else "")

        parser = StaticHTMLParser()
        if html and not html.startswith("FETCH_ERROR"):
            parser.feed(html)

        found = set()
        for asset in parser.assets:
            candidate = "apps/web/app/" + asset
            if (ROOT / candidate).exists():
                found.add(candidate)

        assets |= found

        reports.append({
            "surface": name,
            "url": url,
            "status": status,
            "asset_count": len(found),
            "assets": sorted(found),
            "error": html if html.startswith("FETCH_ERROR") else "",
        })

    return assets, reports


def extract_css_url_assets(css_rel: str) -> set[str]:
    path = ROOT / css_rel
    if not path.exists():
        return set()

    text = read(path)
    assets = set()
    css_dir = path.parent

    for m in re.finditer(r"url\(([^)]+)\)", text):
        raw = m.group(1).strip().strip("'\"")

        if not raw or raw.startswith(("data:", "http:", "https:", "#")):
            continue

        if raw.startswith("/static/"):
            candidate = ROOT / "apps/web/app" / raw.lstrip("/")
        else:
            candidate = (css_dir / raw).resolve()

        try:
            candidate.relative_to(ROOT)
        except ValueError:
            continue

        if candidate.exists() and candidate.is_file():
            assets.add(rel(candidate))

    return assets


def recursive_css_assets(seed_assets: set[str]) -> set[str]:
    all_assets = set(seed_assets)
    changed = True

    while changed:
        changed = False
        for item in list(all_assets):
            if item.endswith(".css"):
                for dep in extract_css_url_assets(item):
                    if dep not in all_assets:
                        all_assets.add(dep)
                        changed = True

    return all_assets


def write_manifest(out: Path, manifest: dict):
    (out / "docs").mkdir(parents=True, exist_ok=True)

    json_path = out / "docs/ACTIVE_SURFACE_MANIFEST.json"
    json_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# FutureFunded Active Surface Repo",
        "",
        "This repo was generated from the active launch surfaces only.",
        "",
        "## Active surfaces",
        "",
    ]

    for surface in manifest["surfaces"]:
        lines.append(f"### {surface['surface']}")
        lines.append(f"- URL/status: `{surface['status']}`")
        lines.append(f"- Rendered assets: `{surface['asset_count']}`")
        lines.append("")

    lines += [
        "## CSS authority loop",
        "",
        "| Surface | CSS authority |",
        "|---|---|",
        "| Platform homepage | `ff.css` → `platform-home.css` |",
        "| Campaign | `ff.css` → `campaign.css` |",
        "| Login | `ff.css` via base → `login.css` |",
        "| Onboarding | `ff.css` → `onboarding.css` |",
        "| Dashboard / locked dashboard | `ff.css` → `dashboard.css` |",
        "",
        "## Copied files",
        "",
    ]

    for file in manifest["files"]:
        lines.append(f"- `{file}`")

    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output repo path")
    ap.add_argument("--base-url", default=os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000"))
    ap.add_argument("--token", default=os.environ.get("FF_OPERATOR_ACCESS_TOKEN", ""))
    ap.add_argument("--no-git", action="store_true")
    args = ap.parse_args()

    out = Path(args.out).resolve()

    if out.exists():
        raise SystemExit(f"Output path already exists. Choose another: {out}")

    print("FutureFunded active surface repo generator")
    print("=========================================")
    print(f"Root: {ROOT}")
    print(f"Output: {out}")
    print(f"Base URL: {args.base_url}")
    print(f"Private dashboard token: {'present' if args.token else 'not provided'}")

    template_matches = find_templates_by_patterns()
    seed_templates = {x for values in template_matches.values() for x in values}
    templates = recursive_template_deps(seed_templates)

    template_assets = set()
    for t in templates:
        template_assets |= extract_static_from_template(t)

    rendered_assets, surface_reports = extract_rendered_assets(args.base_url, args.token)

    active_assets = recursive_css_assets(template_assets | rendered_assets)

    keep = set()
    keep |= templates
    keep |= active_assets

    for item in ALWAYS_KEEP_IF_EXISTS:
        if (ROOT / item).exists():
            keep.add(item)

    # Include current audit/launch scripts that directly support this flow.
    for extra_dir in ["scripts/audit", "scripts/launch_gate", "scripts/repo"]:
        p = ROOT / extra_dir
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in {".py", ".mjs", ".sh", ".md"}:
                    keep.add(rel(f))

    out.mkdir(parents=True)

    copied = []
    missing = []

    for item in sorted(keep):
        if copy_file(item, out):
            copied.append(item)
        else:
            missing.append(item)

    manifest = {
        "generated_at": dt.datetime.now().isoformat(),
        "source_root": str(ROOT),
        "output_root": str(out),
        "base_url": args.base_url,
        "templates_found": template_matches,
        "surfaces": surface_reports,
        "files": copied,
        "missing": missing,
    }

    write_manifest(out, manifest)

    if not args.no_git:
        run(["git", "init"], cwd=out)
        run(["git", "add", "."], cwd=out)
        code, commit_out = run(["git", "commit", "-m", "Create active FutureFunded surface repo"], cwd=out)
        if code != 0:
            print("Git commit skipped/failed:")
            print(commit_out)

    print("")
    print("Done.")
    print(f"New active repo: {out}")
    print(f"Copied files: {len(copied)}")
    print(f"Missing references: {len(missing)}")
    print("")
    print("Open manifest:")
    print(f"  {out}/docs/ACTIVE_SURFACE_MANIFEST.json")
    print(f"  {out}/README.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
