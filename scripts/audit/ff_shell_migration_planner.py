#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "shell-migration-planner" / STAMP
LATEST = ROOT / "audit_outputs" / "shell-migration-planner" / "latest"

FILES = {
    "base": "apps/web/app/templates/_base/site_base.html",
    "campaign_base": "apps/web/app/templates/_base/campaign_base.html",
    "login": "apps/web/app/templates/platform/login.html",
    "onboarding": "apps/web/app/templates/platform/onboarding.html",
    "dashboard": "apps/web/app/templates/platform/dashboard.html",
    "platform": "apps/web/app/templates/platform/index.html",
    "campaign": "apps/web/app/templates/campaign/index.html",
}

BLOCK_RE = re.compile(r"{%\s*block\s+([A-Za-z_][\w]*)\s*%}")
EXTENDS_RE = re.compile(r"{%\s*extends\s+['\"]([^'\"]+)['\"]")
SET_RE = re.compile(r"{%\s*set\s+([A-Za-z_][\w]*)\s*=")
INCLUDE_RE = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]")
DOCTYPE_RE = re.compile(r"<!doctype html>", re.I)
HTML_RE = re.compile(r"<html\b", re.I)
HEAD_RE = re.compile(r"<head\b", re.I)
BODY_RE = re.compile(r"<body\b", re.I)
MAIN_RE = re.compile(r"<main\b", re.I)
MAIN_CLOSE_RE = re.compile(r"</main>", re.I)
FOOTER_RE = re.compile(r"<footer\b", re.I)
GLOBAL_HEADER_RE = re.compile(
    r"<header\b[^>]*(?:ff-siteHeader|ff-platformHeader|ff-campaignHeader|data-ff-header|role=['\"]banner['\"])",
    re.I,
)
LOCAL_MODAL_HEADER_RE = re.compile(
    r"<header\b[^>]*(?:checkout|modal|drawer|panel|dialog)",
    re.I,
)

def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def line_no(text: str, needle_re: re.Pattern) -> int | None:
    for idx, line in enumerate(text.splitlines(), 1):
        if needle_re.search(line):
            return idx
    return None

def extract_main(text: str) -> dict:
    start_match = MAIN_RE.search(text)
    end_match = MAIN_CLOSE_RE.search(text)

    if not start_match or not end_match or end_match.end() <= start_match.start():
        return {
            "found": False,
            "reason": "Could not locate a complete <main>...</main> region.",
        }

    main_region = text[start_match.start():end_match.end()]
    before = text[:start_match.start()]
    after = text[end_match.end():]

    return {
        "found": True,
        "start_index": start_match.start(),
        "end_index": end_match.end(),
        "line_start": before.count("\n") + 1,
        "line_end": text[:end_match.end()].count("\n") + 1,
        "main_lines": main_region.count("\n") + 1,
        "before_lines": before.count("\n") + 1,
        "after_lines": after.count("\n") + 1,
        "has_footer_after_main": bool(FOOTER_RE.search(after)),
        "has_script_after_main": "<script" in after.lower(),
        "main_preview": "\n".join(main_region.splitlines()[:18]),
    }

def scan(rel: str) -> dict:
    text = read(rel)

    global_headers = len(GLOBAL_HEADER_RE.findall(text))
    modal_headers = len(LOCAL_MODAL_HEADER_RE.findall(text))
    all_headers = len(re.findall(r"<header\b", text, re.I))

    return {
        "path": rel,
        "exists": bool(text),
        "lines": text.count("\n") + (1 if text else 0),
        "extends": EXTENDS_RE.findall(text),
        "blocks": BLOCK_RE.findall(text),
        "sets": sorted(set(SET_RE.findall(text))),
        "includes": INCLUDE_RE.findall(text),
        "owns_document": bool(DOCTYPE_RE.search(text) or HTML_RE.search(text) or HEAD_RE.search(text) or BODY_RE.search(text)),
        "doctype_count": len(DOCTYPE_RE.findall(text)),
        "html_count": len(HTML_RE.findall(text)),
        "head_count": len(HEAD_RE.findall(text)),
        "body_count": len(BODY_RE.findall(text)),
        "main_count": len(MAIN_RE.findall(text)),
        "footer_count": len(FOOTER_RE.findall(text)),
        "all_header_count": all_headers,
        "global_header_count": global_headers,
        "modal_header_count": modal_headers,
        "first_main_line": line_no(text, MAIN_RE),
        "first_footer_line": line_no(text, FOOTER_RE),
        "main": extract_main(text),
    }

def recommend(scans: dict) -> list[str]:
    recs = []

    base_blocks = set(scans["base"]["blocks"])
    login_blocks = set(scans["login"]["blocks"])
    onboarding = scans["onboarding"]

    recs.append(f"site_base exposes blocks: {', '.join(scans['base']['blocks']) or 'none found'}.")
    recs.append(f"login currently uses blocks: {', '.join(scans['login']['blocks']) or 'none found'}.")

    if not scans["login"]["extends"]:
        recs.append("Warning: login does not extend site_base according to this scan.")
    else:
        recs.append("Use login.html as the safest migration reference because it already extends the base shell.")

    if onboarding["owns_document"] and onboarding["main"]["found"]:
        recs.append("Onboarding is a good first migration candidate: it owns a document shell and has a clean <main> region.")
    else:
        recs.append("Do not auto-migrate onboarding yet: document shell or <main> extraction is not clean.")

    if "content" in base_blocks or "main" in base_blocks or "body" in base_blocks:
        recs.append("Base shell has a likely content block. Migration can probably be automated after reviewing block names.")
    else:
        recs.append("Base shell content block is not obvious. Inspect site_base before automated migration.")

    if onboarding["main"]["found"] and onboarding["main"]["has_footer_after_main"]:
        recs.append("Onboarding has footer/scripts after main; migration must preserve post-main content deliberately.")
    else:
        recs.append("Onboarding appears to have no footer after main; migration should be lower risk.")

    recs.append("Do not migrate campaign until onboarding + dashboard pass visual/payment gates after shell migration.")

    return recs

def write(data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "shell-migration-plan.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# FutureFunded Shell Migration Planner")
    lines.append("")
    lines.append(f"Generated: `{data['generated_at']}`")
    lines.append("")

    lines.append("## Recommendation")
    lines.append("")
    for rec in data["recommendations"]:
        lines.append(f"- {rec}")

    lines.append("")
    lines.append("## Shell ownership table")
    lines.append("")
    lines.append("| Key | File | Extends | Owns doc | Blocks | Sets | Main | Footer | Global header | Modal header |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for key, scan in data["files"].items():
        lines.append(
            f"| {key} | `{scan['path']}` | {', '.join(scan['extends']) or '-'} | {scan['owns_document']} | {len(scan['blocks'])} | {len(scan['sets'])} | {scan['main_count']} | {scan['footer_count']} | {scan['global_header_count']} | {scan['modal_header_count']} |"
        )

    lines.append("")
    lines.append("## Base shell blocks")
    lines.append("")
    for block in data["files"]["base"]["blocks"]:
        lines.append(f"- `{block}`")

    lines.append("")
    lines.append("## Login extension pattern")
    lines.append("")
    login_text = read(FILES["login"])
    lines.append("```jinja")
    lines.extend(login_text.splitlines()[:80])
    lines.append("```")

    lines.append("")
    lines.append("## Onboarding main extraction preview")
    lines.append("")
    main = data["files"]["onboarding"]["main"]
    if main.get("found"):
        lines.append(f"- Main starts line: `{main['line_start']}`")
        lines.append(f"- Main ends line: `{main['line_end']}`")
        lines.append(f"- Main lines: `{main['main_lines']}`")
        lines.append(f"- Has footer after main: `{main['has_footer_after_main']}`")
        lines.append(f"- Has script after main: `{main['has_script_after_main']}`")
        lines.append("")
        lines.append("```jinja")
        lines.append(main["main_preview"])
        lines.append("```")
    else:
        lines.append(f"Could not extract main: {main.get('reason')}")

    lines.append("")
    lines.append("## Migration rule")
    lines.append("")
    lines.append("Migrate only one surface at a time. After each migration run:")
    lines.append("")
    lines.append("```bash")
    lines.append("python -m py_compile scripts/audit/ff_shell_migration_planner.py")
    lines.append("scripts/demo/ff-fast-proof.sh")
    lines.append("FF_BASE_URL=\"http://127.0.0.1:5000\" FF_VISUAL_STRICT=1 node scripts/release/ff_visual_launch_gate.mjs 2>&1 | sed -E 's/(access_token=)[A-Za-z0-9_-]+/\\1<redacted>/g'")
    lines.append("```")
    lines.append("")

    (OUT / "shell-migration-plan.md").write_text("\n".join(lines), encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)

def main() -> int:
    scans = {key: scan(path) for key, path in FILES.items()}
    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": scans,
        "recommendations": recommend(scans),
    }

    write(data)

    print("FutureFunded shell migration planner complete")
    print(f"Report: {LATEST / 'shell-migration-plan.md'}")
    print(f"JSON:   {LATEST / 'shell-migration-plan.json'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
