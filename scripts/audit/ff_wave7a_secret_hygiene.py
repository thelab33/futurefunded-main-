#!/usr/bin/env python3
"""
FutureFunded • Wave 7A Secret Hygiene Audit

Safe:
- Does not print secret values
- Scans tracked files, important local env files, and PM2 env
- Reports masked counts and likely rotation targets
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "audit_outputs"
OUT_DIR.mkdir(exist_ok=True)

SECRET_PATTERNS = {
    "stripe_secret_key": re.compile(r"sk_(test|live)_[A-Za-z0-9_]+"),
    "stripe_publishable_key": re.compile(r"pk_(test|live)_[A-Za-z0-9_]+"),
    "stripe_webhook_secret": re.compile(r"whsec_[A-Za-z0-9_]+"),
    "cloudflare_api_token": re.compile(r"cfut_[A-Za-z0-9_-]+"),
    "uuid_like_token": re.compile(r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", re.I),
    "cloudflare_tunnel_secret_label": re.compile(r"TunnelSecret|TunnelID|AccountTag"),
    "generic_secret_assignment": re.compile(r"(?i)(SECRET|TOKEN|PASSWORD|API_KEY|WEBHOOK_SECRET)\s*=\s*['\"]?[^'\"\n ]{12,}"),
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "audit_outputs",
    ".ff-backups",
    ".local-artifacts",
    "instance/email-spool",
}

TEXT_EXTS = {
    ".py", ".sh", ".js", ".mjs", ".ts", ".tsx", ".html", ".css",
    ".json", ".toml", ".yaml", ".yml", ".md", ".txt", ".env",
    ".cjs", ".ini", ".cfg"
}


def masked(value: str) -> str:
    value = str(value)
    if not value:
        return ""
    return f"len:{len(value)} last4:{value[-4:]}"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & SKIP_DIRS)


def scan_text(label: str, text: str) -> list[dict]:
    findings = []
    for name, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({
                "source": label,
                "type": name,
                "line": text[:match.start()].count("\n") + 1,
                "masked": masked(match.group(0)),
            })
    return findings


def scan_tracked_files() -> list[dict]:
    try:
        files = subprocess.check_output(
            ["git", "ls-files"],
            text=True,
            cwd=ROOT,
            timeout=10,
        ).splitlines()
    except Exception:
        files = []

    findings = []
    for item in files:
        path = ROOT / item
        if not path.exists() or path.is_dir() or should_skip(path):
            continue
        if path.suffix not in TEXT_EXTS and path.name not in {"requirements.txt", "package.json", "package-lock.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        findings.extend(scan_text(f"tracked:{item}", text))
    return findings


def scan_local_files() -> list[dict]:
    candidates = [
        ROOT / ".env",
        ROOT / ".env.local",
        Path.home() / ".config/futurefunded/postmark.env",
        Path.home() / ".config/futurefunded/cloudflare.env",
        Path.home() / ".cloudflared/config.yml",
    ]

    candidates.extend(Path.home().glob(".cloudflared/*.json"))

    findings = []
    for path in candidates:
        if not path.exists() or path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        findings.extend(scan_text(f"local:{path}", text))
    return findings


def scan_pm2_env() -> list[dict]:
    try:
        raw = subprocess.check_output(["pm2", "jlist"], text=True, timeout=10)
        data = json.loads(raw)
    except Exception as exc:
        return [{"source": "pm2", "type": "pm2_read_error", "line": 0, "masked": type(exc).__name__}]

    findings = []
    for proc in data:
        name = proc.get("name", "unknown")
        env = proc.get("pm2_env", {}) or {}
        for key, value in env.items():
            text = f"{key}={value}"
            if re.search(r"(?i)(SECRET|TOKEN|PASSWORD|STRIPE|POSTMARK|CLOUDFLARE|SMTP)", key):
                findings.append({
                    "source": f"pm2:{name}",
                    "type": f"env:{key}",
                    "line": 0,
                    "masked": masked(str(value)),
                })
            findings.extend(scan_text(f"pm2:{name}:{key}", str(value)))
    return findings


def main() -> int:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tracked_findings": scan_tracked_files(),
        "local_findings": scan_local_files(),
        "pm2_findings": scan_pm2_env(),
        "rotation_targets": [
            "Postmark Server API Token",
            "Cloudflare API Token used for CLI setup",
            "Cloudflare Tunnel credential because TunnelSecret was printed",
            "Stripe test secret key and webhook secret if terminal logs/screenshots are shared",
        ],
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT_DIR / f"ff_wave7a_secret_hygiene_{stamp}.json"
    md_path = OUT_DIR / f"ff_wave7a_secret_hygiene_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 7A Secret Hygiene Audit")
    lines.append("")
    lines.append(f"- **Generated:** `{report['generated_at']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Area | Findings |")
    lines.append("| --- | ---: |")
    lines.append(f"| Tracked files | {len(report['tracked_findings'])} |")
    lines.append(f"| Local env/config files | {len(report['local_findings'])} |")
    lines.append(f"| PM2 runtime env | {len(report['pm2_findings'])} |")
    lines.append("")
    lines.append("## Tracked file findings")
    lines.append("")
    if report["tracked_findings"]:
        lines.append("| Source | Type | Line | Masked |")
        lines.append("| --- | --- | ---: | --- |")
        for f in report["tracked_findings"][:80]:
            lines.append(f"| `{f['source']}` | `{f['type']}` | {f['line']} | `{f['masked']}` |")
    else:
        lines.append("✅ No obvious secret values found in tracked files.")
    lines.append("")
    lines.append("## Local/PM2 note")
    lines.append("")
    lines.append("Local env files and PM2 are expected to contain secrets. The goal is to rotate exposed values and avoid printing them.")
    lines.append("")
    lines.append("## Rotation targets")
    lines.append("")
    for target in report["rotation_targets"]:
        lines.append(f"- {target}")
    lines.append("")
    lines.append("## Next action")
    lines.append("")
    lines.append("Rotate external provider tokens, update local env files, restart PM2 with masked verification only.")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 7A secret hygiene report: {md_path}")
    print(f"JSON: {json_path}")
    print("")
    print("Tracked findings:", len(report["tracked_findings"]))
    print("Local findings:", len(report["local_findings"]))
    print("PM2 findings:", len(report["pm2_findings"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
