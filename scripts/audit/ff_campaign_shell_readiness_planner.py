#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "campaign-shell-readiness" / STAMP
LATEST = ROOT / "audit_outputs" / "campaign-shell-readiness" / "latest"

FILES = {
    "site_base": "apps/web/app/templates/_base/site_base.html",
    "campaign_base": "apps/web/app/templates/_base/campaign_base.html",
    "campaign": "apps/web/app/templates/campaign/index.html",
    "ff_css": "apps/web/app/static/css/ff.css",
    "campaign_css": "apps/web/app/static/css/campaign.css",
    "campaign_js": "apps/web/app/static/js/ff-campaign.js",
}

REQUIRED_HOOK_GROUPS = {
    "checkout": [
        "data-ff-open-checkout",
        "data-ff-donate-trigger",
        "data-ff-payment-trigger",
        "data-ff-embedded-checkout",
        "data-ff-checkout-modal",
    ],
    "sponsor": [
        "data-ff-open-sponsor",
        "data-ff-sponsor-trigger",
        "data-ff-sponsor-modal",
    ],
    "share": [
        "data-ff-share-trigger",
        "data-ff-qr-trigger",
        "data-ff-share-modal",
    ],
    "campaign_root": [
        "data-ff-campaign-root",
        "data-ff-page-root",
        "data-ff-campaign",
    ],
    "progress": [
        "data-ff-progress",
        "data-ff-progress-bar",
        "data-ff-progress-value",
    ],
}

IMPORTANT_STRINGS = [
    "ffCampaignConfig",
    "ffSponsorContract",
    "ffSelectors",
    "Stripe",
    "paypal",
    "checkout",
    "sponsor",
    "share",
    "Fuel the season. Fund the future.",
]

BLOCK_RE = re.compile(r"{%\s*block\s+([A-Za-z_][\w]*)\s*%}")
EXTENDS_RE = re.compile(r"{%\s*extends\s+['\"]([^'\"]+)['\"]")
INCLUDE_RE = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]")
SET_RE = re.compile(r"{%\s*set\s+([A-Za-z_][\w]*)\s*=")
DOCTYPE_RE = re.compile(r"<!doctype html>", re.I)
HTML_RE = re.compile(r"<html\b", re.I)
HEAD_RE = re.compile(r"<head\b", re.I)
BODY_RE = re.compile(r"<body\b", re.I)
MAIN_RE = re.compile(r"<main\b", re.I)
FOOTER_RE = re.compile(r"<footer\b", re.I)
SCRIPT_RE = re.compile(r"<script\b([^>]*)>([\s\S]*?)</script>", re.I)
LINK_CSS_RE = re.compile(r"<link\b[^>]+(?:rel=['\"]stylesheet['\"][^>]+href=['\"]([^'\"]+)|href=['\"]([^'\"]+\.css[^'\"]*)).*?>", re.I)
DATA_FF_RE = re.compile(r"data-ff-[\w:-]+", re.I)


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def uniq(items):
    return sorted(set(x for x in items if x))


def attr_value(attrs: str, name: str) -> str:
    m = re.search(rf"\b{name}\s*=\s*['\"]([^'\"]+)['\"]", attrs, re.I)
    return m.group(1).strip() if m else ""


def line_snippets(text: str, needle: str, radius: int = 2, limit: int = 6):
    lines = text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        if needle.lower() in line.lower():
            start = max(0, idx - radius)
            end = min(len(lines), idx + radius + 1)
            out.append({
                "line": idx + 1,
                "context": [
                    {"line": i + 1, "text": lines[i].rstrip()}
                    for i in range(start, end)
                ],
            })
    return out[:limit]


def script_inventory(text: str):
    out = []
    for idx, match in enumerate(SCRIPT_RE.finditer(text), 1):
        attrs = match.group(1)
        body = match.group(2)
        out.append({
            "index": idx,
            "id": attr_value(attrs, "id"),
            "type": attr_value(attrs, "type") or "classic",
            "src": attr_value(attrs, "src"),
            "defer": bool(re.search(r"\bdefer\b", attrs, re.I)),
            "async": bool(re.search(r"\basync\b", attrs, re.I)),
            "nonce": bool(re.search(r"\bnonce\s*=", attrs, re.I)),
            "body_chars": len(body.strip()),
            "mentions": [s for s in IMPORTANT_STRINGS if s.lower() in (attrs + body).lower()],
        })
    return out


def scan_template(key: str, rel: str) -> dict:
    text = read(rel)
    scripts = script_inventory(text)

    css_refs = []
    for m in LINK_CSS_RE.finditer(text):
        css_refs.extend([g for g in m.groups() if g])

    hook_groups = {}
    for group, hooks in REQUIRED_HOOK_GROUPS.items():
        found = [hook for hook in hooks if hook.lower() in text.lower()]
        hook_groups[group] = {
            "found_any": bool(found),
            "found": found,
            "missing": [hook for hook in hooks if hook not in found],
        }

    important = {s: len(re.findall(re.escape(s), text, re.I)) for s in IMPORTANT_STRINGS}

    return {
        "key": key,
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
        "script_count": len(scripts),
        "scripts": scripts,
        "css_refs": uniq(css_refs),
        "data_ff_hooks": uniq(DATA_FF_RE.findall(text)),
        "hook_groups": hook_groups,
        "important_strings": important,
        "checkout_snippets": line_snippets(text, "checkout"),
        "config_snippets": line_snippets(text, "ffCampaignConfig") + line_snippets(text, "ffSponsorContract"),
    }


def scan_static(rel: str) -> dict:
    text = read(rel)
    return {
        "path": rel,
        "exists": bool(text),
        "lines": text.count("\n") + (1 if text else 0),
        "important_count": len(re.findall(r"!important", text)),
        "data_ff_refs": len(DATA_FF_RE.findall(text)),
        "checkout_refs": len(re.findall(r"checkout", text, re.I)),
        "sponsor_refs": len(re.findall(r"sponsor", text, re.I)),
        "share_refs": len(re.findall(r"share", text, re.I)),
        "campaign_refs": len(re.findall(r"campaign", text, re.I)),
    }


def recommendations(scans: dict, static: dict) -> list[str]:
    recs = []
    campaign = scans["campaign"]
    campaign_base = scans["campaign_base"]

    if not campaign["owns_document"]:
        recs.append("Campaign already appears migrated; do not run a document-shell migration.")
    else:
        recs.append("Campaign still owns a full document shell. Migration is still pending and should be last.")

    if campaign_base["extends"] == ["_base/site_base.html"]:
        recs.append("campaign_base already extends site_base. Prefer migrating campaign/index.html to campaign_base if campaign_base owns the payment/script contracts cleanly.")
    else:
        recs.append("campaign_base does not clearly extend site_base. Direct site_base migration may be safer after inspection.")

    missing_groups = [
        group for group, data in campaign["hook_groups"].items()
        if not data["found_any"]
    ]
    if missing_groups:
        recs.append(f"Check campaign hooks before migration: missing hook groups by broad scan: {', '.join(missing_groups)}.")
    else:
        recs.append("Campaign hook groups are present by broad scan: checkout, sponsor, share, campaign root, and progress.")

    if campaign["script_count"] > 0:
        recs.append("Campaign has inline or local script contracts. Migration must preserve script order and nonce behavior.")
    else:
        recs.append("Campaign template has no direct script tags by scan; external JS/CSP loading may be base-owned.")

    if campaign["footer_count"] > 0:
        recs.append("Campaign has its own footer. Preserve it inside the content block unless campaign_base already owns a campaign footer slot.")

    if static["campaign_css"]["exists"] and static["campaign_js"]["exists"]:
        recs.append("campaign.css and ff-campaign.js are present. Payment smoke remains the source of truth after migration.")
    else:
        recs.append("Static campaign assets are missing by scan; do not migrate until asset references are resolved.")

    recs.append("Next action after this planner: paste this report, then migrate campaign with a rollback-safe script only if readiness is clean.")
    return recs


def write_report(data: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "campaign-shell-readiness.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Campaign Shell Readiness Planner")
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
    lines.append("| Key | File | Extends | Owns doc | Blocks | Sets | Main | Footer | Scripts | CSS refs | data-ff hooks |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for key, scan in data["templates"].items():
        lines.append(
            f"| {key} | `{scan['path']}` | {', '.join(scan['extends']) or '-'} | {scan['owns_document']} | {len(scan['blocks'])} | {len(scan['sets'])} | {scan['main_count']} | {scan['footer_count']} | {scan['script_count']} | {len(scan['css_refs'])} | {len(scan['data_ff_hooks'])} |"
        )

    lines.append("")
    lines.append("## Campaign hook readiness")
    lines.append("")
    lines.append("| Group | Found? | Found hooks | Missing broad hooks |")
    lines.append("|---|---:|---|---|")
    for group, info in data["templates"]["campaign"]["hook_groups"].items():
        lines.append(
            f"| {group} | {info['found_any']} | {', '.join(info['found']) or '-'} | {', '.join(info['missing']) or '-'} |"
        )

    lines.append("")
    lines.append("## Campaign script inventory")
    lines.append("")
    lines.append("| # | id | type | src | defer | async | nonce | body chars | mentions |")
    lines.append("|---:|---|---|---|---:|---:|---:|---:|---|")
    for script in data["templates"]["campaign"]["scripts"]:
        lines.append(
            f"| {script['index']} | `{script['id'] or '-'}` | `{script['type']}` | `{script['src'] or '-'}` | {script['defer']} | {script['async']} | {script['nonce']} | {script['body_chars']} | {', '.join(script['mentions']) or '-'} |"
        )

    if not data["templates"]["campaign"]["scripts"]:
        lines.append("| - | - | - | - | - | - | - | - | No campaign script tags found in template. |")

    lines.append("")
    lines.append("## Important campaign strings")
    lines.append("")
    lines.append("| String | Count |")
    lines.append("|---|---:|")
    for s, count in data["templates"]["campaign"]["important_strings"].items():
        lines.append(f"| `{s}` | {count} |")

    lines.append("")
    lines.append("## Static asset scan")
    lines.append("")
    lines.append("| Asset | Exists | Lines | !important | campaign refs | checkout refs | sponsor refs | share refs |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for key, item in data["static"].items():
        lines.append(
            f"| {key} | {item['exists']} | {item['lines']} | {item['important_count']} | {item['campaign_refs']} | {item['checkout_refs']} | {item['sponsor_refs']} | {item['share_refs']} |"
        )

    lines.append("")
    lines.append("## Config snippets")
    lines.append("")
    snippets = data["templates"]["campaign"]["config_snippets"]
    if not snippets:
        lines.append("No `ffCampaignConfig` or `ffSponsorContract` snippets found by text scan.")
    for item in snippets:
        lines.append(f"Line {item['line']}")
        lines.append("```jinja")
        for row in item["context"]:
            marker = ">" if row["line"] == item["line"] else " "
            lines.append(f"{marker} {row['line']}: {row['text']}")
        lines.append("```")
        lines.append("")

    lines.append("")
    lines.append("## Checkout snippets")
    lines.append("")
    snippets = data["templates"]["campaign"]["checkout_snippets"]
    if not snippets:
        lines.append("No checkout snippets found by text scan.")
    for item in snippets[:4]:
        lines.append(f"Line {item['line']}")
        lines.append("```jinja")
        for row in item["context"]:
            marker = ">" if row["line"] == item["line"] else " "
            lines.append(f"{marker} {row['line']}: {row['text']}")
        lines.append("```")
        lines.append("")

    lines.append("")
    lines.append("## Migration guardrail")
    lines.append("")
    lines.append("Do not migrate campaign until this report is reviewed. After migration, required proof is:")
    lines.append("")
    lines.append("```bash")
    lines.append("scripts/demo/ff-fast-proof.sh")
    lines.append("FF_BASE_URL=\"http://127.0.0.1:5000\" FF_VISUAL_STRICT=1 node scripts/release/ff_visual_launch_gate.mjs 2>&1 | sed -E 's/(access_token=)[A-Za-z0-9_-]+/\\1<redacted>/g'")
    lines.append("python scripts/audit/ff_product_family_review.py")
    lines.append("```")
    lines.append("")

    (OUT / "campaign-shell-readiness.md").write_text("\n".join(lines), encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    shutil.copytree(OUT, LATEST)


def main() -> int:
    templates = {
        "site_base": scan_template("site_base", FILES["site_base"]),
        "campaign_base": scan_template("campaign_base", FILES["campaign_base"]),
        "campaign": scan_template("campaign", FILES["campaign"]),
    }

    static = {
        "ff_css": scan_static(FILES["ff_css"]),
        "campaign_css": scan_static(FILES["campaign_css"]),
        "campaign_js": scan_static(FILES["campaign_js"]),
    }

    data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "templates": templates,
        "static": static,
    }
    data["recommendations"] = recommendations(templates, static)

    write_report(data)

    print("FutureFunded campaign shell readiness planner complete")
    print(f"Report: {LATEST / 'campaign-shell-readiness.md'}")
    print(f"JSON:   {LATEST / 'campaign-shell-readiness.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
