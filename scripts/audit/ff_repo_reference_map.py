from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / "audit_outputs" / "repo-authority"
OUT.mkdir(parents=True, exist_ok=True)

SCAN_SUFFIXES = {".html", ".jinja", ".jinja2", ".py", ".js", ".mjs", ".css", ".md"}
ASSET_SUFFIXES = {".css", ".js", ".mjs"}
TEMPLATE_SUFFIXES = {".html", ".jinja", ".jinja2"}

ACTIVE_AUTHORITY = {
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/platform-home.css",
    "apps/web/app/static/css/dashboard-modern.css",
    "apps/web/app/static/css/ff-dashboard-final.css",
    "apps/web/app/static/css/ff-dashboard-protected-exec.css",
    "apps/web/app/static/css/login.css",
    "apps/web/app/static/css/ff-login-calm.css",
    "apps/web/app/static/js/ff-campaign.js",
    "apps/web/app/static/js/ff-dashboard-protected-exec.js",
    "apps/web/app/static/js/islands/onboarding.js",
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/campaign_premium.html",
    "apps/web/app/templates/platform/onboarding.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/dashboard.html",
    "apps/web/app/templates/platform/dashboard_locked.html",
    "apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html",
    "apps/web/app/templates/_base/site_base.html",
    "apps/web/app/templates/_partials/ff_site_header.html",
}

REVIEW_ONLY = {
    "apps/web/app/static/css/campaign.css",
    "apps/web/app/static/css/ff-campaign-enterprise.css",
    "apps/web/app/static/css/ff-campaign-final-compression.css",
    "apps/web/app/static/css/ff.checkout.css",
    "apps/web/app/static/css/ff.cinematic.css",
    "apps/web/app/static/css/onboarding.css",
    "apps/web/app/static/css/ff-onboarding-executive.css",
    "apps/web/app/static/css/ff-homepage-executive.css",
    "apps/web/app/static/js/ff-embedded-checkout.js",
    "apps/web/app/static/js/ff-checkout-direct.js",
    "apps/web/app/static/js/ff-campaign-enterprise.js",
    "apps/web/app/static/js/ff-campaign-final-compression.js",
    "apps/web/app/static/js/ff-homepage-executive.js",
    "apps/web/app/static/js/ff-operator-dashboard.js",
    "apps/web/app/static/js/ff-payment-provider-status.js",
}

IGNORE_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "audit_outputs",
    "dist",
    "build",
}

def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"ERROR: {exc}"

def should_skip(path: Path) -> bool:
    return any(part in IGNORE_PARTS for part in path.parts)

def files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in SCAN_SUFFIXES and not should_skip(path):
            out.append(path)
    return sorted(out)

def normalize_ref(raw: str) -> list[str]:
    raw = raw.split("?", 1)[0].split("#", 1)[0].strip()
    raw = raw.replace("{{ url_for('static', filename='", "apps/web/app/static/")
    raw = raw.replace('{{ url_for("static", filename="', "apps/web/app/static/")
    raw = raw.replace("') }}", "")
    raw = raw.replace('") }}', "")
    raw = raw.strip("'\" ")

    candidates = []

    if raw.startswith("/static/"):
        candidates.append("apps/web/app/static/" + raw.removeprefix("/static/"))

    if raw.startswith("static/"):
        candidates.append("apps/web/app/" + raw)

    if raw.startswith("css/") or raw.startswith("js/") or raw.startswith("images/"):
        candidates.append("apps/web/app/static/" + raw)

    if raw.startswith("_") or raw.startswith("campaign/") or raw.startswith("platform/") or raw.startswith("shared/"):
        candidates.append("apps/web/app/templates/" + raw)

    if raw.startswith("apps/") or raw.startswith("scripts/") or raw.startswith("docs/"):
        candidates.append(raw)

    return [c for c in candidates if c]

def main() -> None:
    all_files = files()

    assets = [
        rel(p) for p in all_files
        if rel(p).startswith("apps/web/app/static/") and p.suffix.lower() in ASSET_SUFFIXES
    ]
    templates = [
        rel(p) for p in all_files
        if rel(p).startswith("apps/web/app/templates/") and p.suffix.lower() in TEMPLATE_SUFFIXES
    ]

    refs: dict[str, set[str]] = defaultdict(set)

    raw_patterns = [
        re.compile(r'''(?:href|src)=["']([^"']+\.(?:css|js|mjs)(?:\?[^"']*)?)["']''', re.I),
        re.compile(r'''url_for\(["']static["'],\s*filename=["']([^"']+)["']''', re.I),
        re.compile(r'''(?:include|extends|import|from)\s+["']([^"']+\.(?:html|jinja|jinja2))["']''', re.I),
        re.compile(r'''["']([^"']+\.(?:css|js|mjs|html|jinja|jinja2))["']''', re.I),
    ]

    for path in all_files:
        text = read(path)
        source = rel(path)
        for pat in raw_patterns:
            for raw in pat.findall(text):
                for candidate in normalize_ref(raw):
                    refs[candidate].add(source)

        # Also catch direct basename references, useful for Flask url_for split strings.
        for target in assets + templates:
            name = Path(target).name
            if name in text:
                refs[target].add(source)

    records = []
    for target in sorted(set(assets + templates + list(ACTIVE_AUTHORITY) + list(REVIEW_ONLY))):
        records.append({
            "path": target,
            "exists": (ROOT / target).exists(),
            "active_authority": target in ACTIVE_AUTHORITY,
            "review_only": target in REVIEW_ONLY,
            "ref_count": len(refs.get(target, set())),
            "referenced_by": sorted(refs.get(target, set())),
        })

    review = [r for r in records if r["review_only"]]
    active = [r for r in records if r["active_authority"]]
    unreferenced_review = [r for r in review if r["exists"] and r["ref_count"] == 0]
    referenced_review = [r for r in review if r["exists"] and r["ref_count"] > 0]

    patch_candidates = []
    for path in sorted((ROOT / "scripts").rglob("*.py")):
        r = rel(path)
        if "/patches/" in r or Path(r).name.startswith(("patch_", "elite_patch_")):
            patch_candidates.append(r)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": run(["git", "branch", "--show-current"]),
        "head": run(["git", "rev-parse", "--short", "HEAD"]),
        "counts": {
            "assets": len(assets),
            "templates": len(templates),
            "records": len(records),
            "active_authority": len(active),
            "review_only": len(review),
            "review_only_referenced": len(referenced_review),
            "review_only_unref": len(unreferenced_review),
            "patch_archive_candidates": len(patch_candidates),
        },
        "active": active,
        "review_only": review,
        "referenced_review_only": referenced_review,
        "unreferenced_review_only": unreferenced_review,
        "patch_archive_candidates": patch_candidates,
    }

    (OUT / "repo_reference_map.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    md = []
    md.append("# FutureFunded Repo Reference Map\n")
    md.append(f"Generated: `{report['generated_at_utc']}`  \nBranch: `{report['branch']}`  \nHEAD: `{report['head']}`\n")

    md.append("## Counts\n")
    for k, v in report["counts"].items():
        md.append(f"- **{k}:** `{v}`")
    md.append("")

    md.append("## Review-only files still referenced\n")
    if referenced_review:
        for rec in referenced_review:
            md.append(f"### `{rec['path']}`")
            for src in rec["referenced_by"][:20]:
                md.append(f"- referenced by `{src}`")
            md.append("")
    else:
        md.append("- None\n")

    md.append("## Review-only files with no detected references")
    md.append("These are candidates for quarantine, not deletion.\n")
    if unreferenced_review:
        for rec in unreferenced_review:
            md.append(f"- `{rec['path']}`")
    else:
        md.append("- None")
    md.append("")

    md.append("## Patch script archive candidates")
    if patch_candidates:
        for p in patch_candidates:
            md.append(f"- `{p}`")
    else:
        md.append("- None")
    md.append("")

    md.append("## Active authority reference summary\n")
    for rec in active:
        md.append(f"- `{rec['path']}` — refs: `{rec['ref_count']}`")
    md.append("")

    (OUT / "repo_reference_map.md").write_text("\n".join(md), encoding="utf-8")

    print("FutureFunded repo reference map complete")
    print(f"MD:   {rel(OUT / 'repo_reference_map.md')}")
    print(f"JSON: {rel(OUT / 'repo_reference_map.json')}")
    print("")
    for k, v in report["counts"].items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
