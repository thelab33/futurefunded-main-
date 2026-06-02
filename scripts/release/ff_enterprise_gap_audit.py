#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d%H%M%S")
OUT = ROOT / "audit_outputs" / f"enterprise-gap-audit-{STAMP}"
OUT.mkdir(parents=True, exist_ok=True)

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", "audit_outputs", ".ff_backups", ".rollback", "dist", "build"
}

TEXT_EXTS = {
    ".py", ".sh", ".md", ".txt", ".env", ".example", ".template", ".toml",
    ".yml", ".yaml", ".json", ".js", ".jsx", ".ts", ".tsx", ".html",
    ".css", ".ini", ".cfg", ".conf", ".service", ".dockerfile"
}

CHECKS = {
    "production_hosting": [
        "railway", "render.com", "fly.io", "digitalocean", "app platform",
        "heroku", "aws", "elastic beanstalk", "ecs", "ec2", "vercel",
        "gunicorn", "procfile", "nixpacks", "render.yaml", "railway.json",
        "fly.toml", "Dockerfile", "docker-compose", "FF_PRODUCTION_HOST_PROVIDER",
    ],
    "production_domain_tls": [
        "FF_PRODUCTION_APP_URL", "FF_PRODUCTION_DOMAIN", "FF_PRODUCTION_TLS_ENABLED",
        "https://getfuturefunded.com", "ssl", "tls", "certificate", "certbot",
        "cloudflare", "cname", "dns"
    ],
    "managed_database": [
        "postgres", "postgresql", "DATABASE_URL", "SQLALCHEMY_DATABASE_URI",
        "supabase", "neon", "railway postgres", "render postgres",
        "managed db", "backup", "restore", "pg_dump", "pg_restore"
    ],
    "deploy_rollback": [
        "FF_DEPLOY_COMMAND", "FF_ROLLBACK_COMMAND", "deploy", "rollback",
        "release", "migration", "gunicorn", "systemd", "pm2",
        "github actions", ".github/workflows", "CI", "CD"
    ],
    "monitoring_observability": [
        "sentry", "SENTRY_DSN", "uptimerobot", "better stack", "betterstack",
        "healthcheck", "healthz", "statuspage", "logtail", "datadog",
        "prometheus", "grafana", "alert", "incident"
    ],
    "customer_onboarding": [
        "onboarding", "organization", "tenant", "workspace", "team setup",
        "create campaign", "campaign creation", "org_slug", "customer",
        "subscription", "stripe connect", "connect account"
    ],
    "subscription_billing": [
        "stripe subscription", "checkout session", "price_id", "STRIPE_PRICE",
        "billing portal", "customer portal", "subscription", "plan",
        "monthly", "trial"
    ],
    "donor_journey": [
        "donate", "checkout", "webhook", "ledger", "receipt", "sponsor",
        "thank you", "donation", "payment_intent", "checkout.session.completed"
    ],
}

def is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)

def is_text_candidate(path: Path) -> bool:
    if is_ignored(path):
        return False
    if path.name in {"Dockerfile", "Procfile", "Makefile"}:
        return True
    if path.suffix.lower() in TEXT_EXTS:
        return True
    if path.name.startswith(".env"):
        return True
    return False

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def git_status() -> str:
    try:
        return subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout
    except Exception as exc:
        return f"git status unavailable: {exc}"

files = [p for p in ROOT.rglob("*") if p.is_file() and is_text_candidate(p)]
results = {}

for area, terms in CHECKS.items():
    hits = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = read_text(path)
        hay = f"{rel}\n{text}".lower()
        for term in terms:
            if term.lower() in hay:
                line_no = None
                sample = ""
                for i, line in enumerate(text.splitlines(), start=1):
                    if term.lower() in line.lower():
                        line_no = i
                        sample = line.strip()[:220]
                        break
                hits.append({
                    "term": term,
                    "file": rel,
                    "line": line_no,
                    "sample": sample,
                })
                break
    results[area] = hits

summary = {}
for area, hits in results.items():
    unique_files = sorted({h["file"] for h in hits})
    if len(unique_files) >= 5:
        status = "LIKELY_PRESENT"
    elif len(unique_files) >= 2:
        status = "PARTIAL"
    elif len(unique_files) == 1:
        status = "THIN"
    else:
        status = "MISSING"
    summary[area] = {
        "status": status,
        "hit_count": len(hits),
        "file_count": len(unique_files),
        "files": unique_files[:25],
    }

report = {
    "stamp": STAMP,
    "root": str(ROOT),
    "git_status_short": git_status(),
    "summary": summary,
    "hits": results,
}

json_path = OUT / "enterprise-gap-audit.json"
md_path = OUT / "enterprise-gap-audit.md"

json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

lines = []
lines.append("# FutureFunded Enterprise Gap Audit")
lines.append("")
lines.append(f"- Root: `{ROOT}`")
lines.append(f"- Stamp: `{STAMP}`")
lines.append("")
lines.append("## Summary")
lines.append("")
lines.append("| Area | Status | Files | Hits |")
lines.append("|---|---:|---:|---:|")
for area, data in summary.items():
    lines.append(f"| `{area}` | **{data['status']}** | {data['file_count']} | {data['hit_count']} |")

lines.append("")
lines.append("## Detail")
for area, hits in results.items():
    lines.append("")
    lines.append(f"### {area}")
    if not hits:
        lines.append("")
        lines.append("No evidence found.")
        continue
    for h in hits[:40]:
        loc = f"{h['file']}"
        if h["line"]:
            loc += f":{h['line']}"
        sample = h["sample"].replace("|", "\\|") if h["sample"] else ""
        lines.append(f"- `{h['term']}` → `{loc}`")
        if sample:
            lines.append(f"  - `{sample}`")

lines.append("")
lines.append("## Git status")
lines.append("")
lines.append("```text")
lines.append(report["git_status_short"].strip() or "clean")
lines.append("```")

md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("== FutureFunded Enterprise Gap Audit ==")
print(f"OUT={OUT}")
print()
for area, data in summary.items():
    print(f"{area}: {data['status']} files={data['file_count']} hits={data['hit_count']}")
print()
print(f"Markdown: {md_path}")
print(f"JSON:     {json_path}")
