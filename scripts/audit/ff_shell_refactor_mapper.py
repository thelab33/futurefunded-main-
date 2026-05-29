#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "shell-refactor-mapper" / STAMP
LATEST = ROOT / "audit_outputs" / "shell-refactor-mapper" / "latest"

FILES = [
    "apps/web/app/templates/_base/site_base.html",
    "apps/web/app/templates/_base/campaign_base.html",
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/onboarding.html",
    "apps/web/app/templates/platform/dashboard.html",
]

PATTERNS = {
    "doctype": re.compile(r"<!doctype html>", re.I),
    "html_open": re.compile(r"<html\b", re.I),
    "head_open": re.compile(r"<head\b", re.I),
    "body_open": re.compile(r"<body\b", re.I),
    "header_tags": re.compile(r"<header\b", re.I),
    "footer_tags": re.compile(r"<footer\b", re.I),
    "nav_tags": re.compile(r"<nav\b", re.I),
    "main_tags": re.compile(r"<main\b", re.I),
    "extends": re.compile(r"{%\s*extends\s+['\"]([^'\"]+)['\"]"),
    "includes": re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]"),
    "css_refs": re.compile(r"href=['\"]([^'\"]+\.css(?:\?[^'\"]*)?)['\"]", re.I),
    "js_refs": re.compile(r"src=['\"]([^'\"]+\.js(?:\?[^'\"]*)?)['\"]", re.I),
    "data_page": re.compile(r"data-ff-page=['\"]([^'\"]+)['\"]", re.I),
    "data_surface": re.compile(r"data-ff-surface=['\"]([^'\"]+)['\"]", re.I),
    "site_header_class": re.compile(r"ff-siteHeader[\w-]*", re.I),
    "platform_footer_class": re.compile(r"ff-platformFooter[\w-]*", re.I),
    "campaign_header_class": re.compile(r"ff-campaignHeader[\w-]*", re.I),
    "dashboard_class": re.compile(r"ffDash[\w-]*|ff-dashboard[\w-]*", re.I),
    "onboard_class": re.compile(r"ffOnboard[\w-]*", re.I),
}

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def uniq(items):
    return sorted(set(x for x in items if x))

def line_snippets(text: str, rx: re.Pattern, radius: int = 2):
    lines = text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        if rx.search(line):
            start = max(0, idx - radius)
            end = min(len(lines), idx + radius + 1)
            out.append({
                "line": idx + 1,
                "context": [
                    {"line": i + 1, "text": lines[i].rstrip()}
                    for i in range(start, end)
                ],
            })
    return out[:8]

def scan_file(rel: str):
    path = ROOT / rel
    text = read(path)
    return {
        "path": rel,
        "exists": path.exists(),
        "lines": text.count("\n") + (1 if text else 0),
        "has_document_shell": bool(PATTERNS["doctype"].search(text) or PATTERNS["html_open"].search(text)),
        "doctype_count": len(PATTERNS["doctype"].findall(text)),
        "html_count": len(PATTERNS["html_open"].findall(text)),
        "head_count": len(PATTERNS["head_open"].findall(text)),
        "body_count": len(PATTERNS["body_open"].findall(text)),
        "header_count": len(PATTERNS["header_tags"].findall(text)),
        "footer_count": len(PATTERNS["footer_tags"].findall(text)),
        "nav_count": len(PATTERNS["nav_tags"].findall(text)),
        "main_count": len(PATTERNS["main_tags"].findall(text)),
        "extends": uniq(PATTERNS["extends"].findall(text)),
        "includes": uniq(PATTERNS["includes"].findall(text)),
        "css_refs": uniq(PATTERNS["css_refs"].findall(text)),
        "js_refs": uniq(PATTERNS["js_refs"].findall(text)),
        "data_ff_pages": uniq(PATTERNS["data_page"].findall(text)),
        "data_ff_surfaces": uniq(PATTERNS["data_surface"].findall(text)),
        "site_header_classes": uniq(PATTERNS["site_header_class"].findall(text)),
        "platform_footer_classes": uniq(PATTERNS["platform_footer_class"].findall(text)),
        "campaign_header_classes": uniq(PATTERNS["campaign_header_class"].findall(text)),
        "dashboard_classes_sample": uniq(PATTERNS["dashboard_class"].findall(text))[:30],
        "onboard_classes_sample": uniq(PATTERNS["onboard_class"].findall(text))[:30],
        "header_snippets": line_snippets(text, PATTERNS["header_tags"]),
        "footer_snippets": line_snippets(text, PATTERNS["footer_tags"]),
        "css_snippets": line_snippets(text, PATTERNS["css_refs"], radius=1),
    }

def make_recommendations(scans):
    recs = []

    page_files = [
        "apps/web/app/templates/platform/index.html",
        "apps/web/app/templates/campaign/index.html",
        "apps/web/app/templates/platform/login.html",
        "apps/web/app/templates/platform/onboarding.html",
        "apps/web/app/templates/platform/dashboard.html",
    ]

    full_docs = [s["path"] for s in scans if s["path"] in page_files and s["has_document_shell"]]
    extenders = [s["path"] for s in scans if s["path"] in page_files and s["extends"]]

    if full_docs:
        recs.append(f"Several route templates own full document shells: {', '.join(full_docs)}.")
    if extenders:
        recs.append(f"Some route templates already extend a base shell: {', '.join(extenders)}.")

    header_owners = [s["path"] for s in scans if s["header_count"] > 0]
    footer_owners = [s["path"] for s in scans if s["footer_count"] > 0]

    recs.append(f"Header markup currently appears in {len(header_owners)} file(s).")
    recs.append(f"Footer markup currently appears in {len(footer_owners)} file(s).")

    css_refs = {}
    for s in scans:
        if s["path"] in page_files:
            css_refs[s["path"]] = s["css_refs"]

    recs.append("Target shell direction: site_base owns document/meta/core CSS; shared shell partial owns header/footer; pages own content only.")
    recs.append("Do not migrate campaign into the shared shell first. Start with login + onboarding because they are lower conversion risk.")
    recs.append("Keep campaign.css isolated until the shared shell is proven across platform/auth/operator pages.")

    return recs

def write_report(data):
    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "shell-refactor-map.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# FutureFunded Shell Refactor Mapper")
    lines.append("")
    lines.append(f"Generated: `{data['generated_at']}`")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    for rec in data["recommendations"]:
        lines.append(f"- {rec}")

    lines.append("")
    lines.append("## File ownership map")
    lines.append("")
    lines.append("| File | Doc shell | Extends | Header | Nav | Main | Footer | CSS refs | JS refs |")
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|---:|")

    for s in data["files"]:
        lines.append(
            f"| `{s['path']}` | {s['has_document_shell']} | {', '.join(s['extends']) or '-'} | {s['header_count']} | {s['nav_count']} | {s['main_count']} | {s['footer_count']} | {len(s['css_refs'])} | {len(s['js_refs'])} |"
        )

    lines.append("")
    lines.append("## CSS references by active page")
    lines.append("")
    for s in data["files"]:
        if s["path"].startswith("apps/web/app/templates/platform/") or s["path"].startswith("apps/web/app/templates/campaign/"):
            lines.append(f"### `{s['path']}`")
            if s["css_refs"]:
                for ref in s["css_refs"]:
                    lines.append(f"- `{ref}`")
            else:
                lines.append("- No direct CSS refs found.")
            lines.append("")

    lines.append("## Header snippets")
    lines.append("")
    for s in data["files"]:
        if not s["header_snippets"]:
            continue
        lines.append(f"### `{s['path']}`")
        lines.append("")
        for item in s["header_snippets"][:2]:
            lines.append(f"Line {item['line']}")
            lines.append("```jinja")
            for row in item["context"]:
                marker = ">" if row["line"] == item["line"] else " "
                lines.append(f"{marker} {row['line']}: {row['text']}")
            lines.append("```")
            lines.append("")

    lines.append("## Footer snippets")
    lines.append("")
    for s in data["files"]:
        if not s["footer_snippets"]:
            continue
        lines.append(f"### `{s['path']}`")
        lines.append("")
        for item in s["footer_snippets"][:2]:
            lines.append(f"Line {item['line']}")
            lines.append("```jinja")
            for row in item["context"]:
                marker = ">" if row["line"] == item["line"] else " "
                lines.append(f"{marker} {row['line']}: {row['text']}")
            lines.append("```")
            lines.append("")

    (OUT / "shell-refactor-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)

def main():
    scans = [scan_file(rel) for rel in FILES]
    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": scans,
        "recommendations": make_recommendations(scans),
    }
    write_report(data)

    print("FutureFunded shell refactor mapper complete")
    print(f"Report: {LATEST / 'shell-refactor-map.md'}")
    print(f"JSON:   {LATEST / 'shell-refactor-map.json'}")

if __name__ == "__main__":
    main()
