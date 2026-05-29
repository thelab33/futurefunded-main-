from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "audit_outputs" / "repo-authority"
OUT.mkdir(parents=True, exist_ok=True)

ACTIVE_ROUTE_HINTS = {
    "platform_home": [
        "apps/web/app/templates/platform/index.html",
        "apps/web/app/static/css/platform-home.css",
    ],
    "campaign": [
        "apps/web/app/templates/campaign/index.html",
        "apps/web/app/templates/campaign_premium.html",
        "apps/web/app/static/css/ff.css",
        "apps/web/app/static/js/ff-campaign.js",
    ],
    "onboarding": [
        "apps/web/app/templates/platform/onboarding.html",
        "apps/web/app/static/js/islands/onboarding.js",
        "apps/web/app/static/css/ff.css",
    ],
    "login": [
        "apps/web/app/templates/platform/login.html",
        "apps/web/app/static/css/login.css",
        "apps/web/app/static/css/ff-login-calm.css",
    ],
    "dashboard": [
        "apps/web/app/templates/platform/dashboard.html",
        "apps/web/app/templates/platform/dashboard_locked.html",
        "apps/web/app/static/css/dashboard-modern.css",
        "apps/web/app/static/css/ff-dashboard-final.css",
        "apps/web/app/static/css/ff-dashboard-protected-exec.css",
        "apps/web/app/static/js/ff-dashboard-protected-exec.js",
    ],
    "shared": [
        "apps/web/app/templates/_base/site_base.html",
        "apps/web/app/templates/_partials/ff_site_header.html",
        "apps/web/app/static/css/ff.css",
    ],
}

TEXT_SUFFIXES = {
    ".py", ".js", ".mjs", ".css", ".html", ".jinja", ".jinja2",
    ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".env",
}

SCAN_DIRS = [
    "apps/web/app/templates",
    "apps/web/app/static/css",
    "apps/web/app/static/js",
    "scripts",
    "docs",
]

STALE_NAME_HINTS = re.compile(
    r"(backup|bak|old|legacy|copy|tmp|temp|broken|restore|archive|quarantine|"
    r"patch|wave\d+|rescue|before|after|wip|draft|unused|duplicate)",
    re.I,
)

AUTHORITY_HINTS = re.compile(
    r"(AUTHORITY|SINGLE AUTHORITY|FINAL|PROTECTED_EXEC|NOFLASH|NO-FLASH|"
    r"CAMPAIGN|DASHBOARD|PLATFORM|LOGIN|ONBOARDING|HOI)",
    re.I,
)

ASSET_REF_RE = re.compile(
    r"""(?:href|src)=["']([^"']+\.(?:css|js)(?:\?[^"']*)?)["']""",
    re.I,
)

JINJA_INCLUDE_RE = re.compile(
    r"""{%\s*(?:include|extends|import|from)\s+["']([^"']+)["']""",
    re.I,
)

def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"ERROR: {exc}"

def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def git_tracked_files() -> set[str]:
    out = run(["git", "ls-files"])
    if out.startswith("ERROR"):
        return set()
    return set(x.strip() for x in out.splitlines() if x.strip())

def git_status() -> list[str]:
    out = run(["git", "status", "--short", "--untracked-files=all"])
    if out.startswith("ERROR"):
        return [out]
    return out.splitlines()

def collect_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and is_text_file(path):
                files.append(path)
    return sorted(files)

def classify_file(path: Path, tracked: set[str]) -> dict:
    text = read(path)
    r = rel(path)
    stat = path.stat()

    asset_refs = ASSET_REF_RE.findall(text) if path.suffix.lower() in {".html", ".jinja", ".jinja2"} else []
    includes = JINJA_INCLUDE_RE.findall(text) if path.suffix.lower() in {".html", ".jinja", ".jinja2"} else []

    active_route_uses = []
    for surface, hints in ACTIVE_ROUTE_HINTS.items():
        if r in hints:
            active_route_uses.append(surface)

    return {
        "path": r,
        "tracked": r in tracked,
        "suffix": path.suffix.lower(),
        "bytes": stat.st_size,
        "lines": text.count("\n") + 1 if text else 0,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "active_route_hint": active_route_uses,
        "stale_name_hint": bool(STALE_NAME_HINTS.search(path.name) or STALE_NAME_HINTS.search(r)),
        "authority_marker_count": len(AUTHORITY_HINTS.findall(text)),
        "asset_refs": asset_refs,
        "jinja_includes": includes,
        "has_todo": "TODO" in text or "FIXME" in text,
        "has_template_leak_literal": "{{" in text and path.suffix.lower() in {".css", ".js", ".mjs"},
    }

def main() -> None:
    tracked = git_tracked_files()
    files = collect_files()
    records = [classify_file(path, tracked) for path in files]

    by_suffix = defaultdict(int)
    for rec in records:
      by_suffix[rec["suffix"]] += 1

    active = [rec for rec in records if rec["active_route_hint"]]
    suspicious = [
        rec for rec in records
        if rec["stale_name_hint"]
        or rec["has_template_leak_literal"]
        or (rec["suffix"] in {".css", ".js", ".mjs"} and rec["bytes"] > 250_000)
    ]

    css_files = [rec for rec in records if rec["suffix"] == ".css"]
    js_files = [rec for rec in records if rec["suffix"] in {".js", ".mjs"}]
    template_files = [rec for rec in records if rec["suffix"] in {".html", ".jinja", ".jinja2"}]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(ROOT),
        "git_branch": run(["git", "branch", "--show-current"]),
        "git_head": run(["git", "rev-parse", "--short", "HEAD"]),
        "git_status": git_status(),
        "counts": {
            "total_scanned": len(records),
            "active_hint_files": len(active),
            "suspicious_or_stale_hint_files": len(suspicious),
            "css_files": len(css_files),
            "js_files": len(js_files),
            "template_files": len(template_files),
            "by_suffix": dict(sorted(by_suffix.items())),
        },
        "active_route_hints": ACTIVE_ROUTE_HINTS,
        "files": records,
        "active": active,
        "suspicious": suspicious,
    }

    (OUT / "repo_authority_inventory.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    md = []
    md.append("# FutureFunded Repo Authority Inventory\n")
    md.append(f"Generated: `{report['generated_at_utc']}`\n")
    md.append(f"Branch: `{report['git_branch']}`  \nHEAD: `{report['git_head']}`\n")

    md.append("## Counts\n")
    for k, v in report["counts"].items():
        md.append(f"- **{k}**: `{v}`")
    md.append("")

    md.append("## Current git status\n")
    if report["git_status"]:
        md.extend([f"- `{line}`" for line in report["git_status"]])
    else:
        md.append("- Clean")
    md.append("")

    md.append("## Canonical active-route hints\n")
    for surface, paths in ACTIVE_ROUTE_HINTS.items():
        md.append(f"### {surface}")
        for p in paths:
            exists = (ROOT / p).exists()
            md.append(f"- {'✅' if exists else '⚠️'} `{p}`")
        md.append("")

    md.append("## Suspicious / stale-name candidates")
    md.append("These are **not deleted**. Review before quarantine.\n")
    for rec in suspicious[:250]:
        reasons = []
        if rec["stale_name_hint"]:
            reasons.append("name")
        if rec["has_template_leak_literal"]:
            reasons.append("template-literal-in-static")
        if rec["bytes"] > 250_000:
            reasons.append("large")
        md.append(f"- `{rec['path']}` — {', '.join(reasons)}")
    md.append("")

    md.append("## CSS files")
    for rec in css_files:
        marker = "ACTIVE" if rec["active_route_hint"] else ""
        md.append(f"- `{rec['path']}` {marker}".rstrip())
    md.append("")

    md.append("## JS/MJS files")
    for rec in js_files:
        marker = "ACTIVE" if rec["active_route_hint"] else ""
        md.append(f"- `{rec['path']}` {marker}".rstrip())
    md.append("")

    md.append("## Template files")
    for rec in template_files:
        marker = "ACTIVE" if rec["active_route_hint"] else ""
        md.append(f"- `{rec['path']}` {marker}".rstrip())
    md.append("")

    (OUT / "repo_authority_inventory.md").write_text("\n".join(md), encoding="utf-8")

    print("FutureFunded repo authority inventory complete")
    print(f"JSON: {rel(OUT / 'repo_authority_inventory.json')}")
    print(f"MD:   {rel(OUT / 'repo_authority_inventory.md')}")
    print("")
    print(f"Scanned: {len(records)}")
    print(f"Active hint files: {len(active)}")
    print(f"Suspicious/stale candidates: {len(suspicious)}")

if __name__ == "__main__":
    main()
