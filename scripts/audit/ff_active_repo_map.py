#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
OUT_JSON = ROOT / "docs/release-proof/active-repo-map-latest.json"
OUT_MD = ROOT / "docs/release-proof/active-repo-map-latest.md"

IGNORE_DIRS = {
    # Active-map default: ignore non-runtime backup/noise directories.
    # Set FF_ACTIVE_MAP_INCLUDE_ARCHIVES=1 when intentionally auditing old backups.
    ".ff-backups",
    ".ff_backups",
    ".template-backups",
    ".local-artifacts",
    "_archive",
    "archive",
    "artifacts",
    "audit_outputs",
    "tmp",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    "dist",
    "build",
}


PRIVATE_RUNTIME_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    ".env.local.stripe-test",
    ".stripe-local-whsec",
}

def is_private_runtime_file(path: Path) -> bool:
    name = path.name
    return (
        name in PRIVATE_RUNTIME_FILE_NAMES
        or name.startswith(".env.")
        or name.endswith(".env")
    )

TEXT_EXTS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".html", ".jinja", ".j2", ".css", ".scss",
    ".sh", ".md", ".txt", ".json", ".yml", ".yaml",
    ".toml", ".ini", ".env", ".example",
}

ENTRY_FILES = [
    "ecosystem.config.cjs",
    "gunicorn.conf.py",
    "apps/web/wsgi.py",
    "apps/api/asgi.py",
    "Dockerfile.web",
    "Dockerfile.api",
    "docker-compose.yml",
    "alembic.ini",
    "pyproject.toml",
    "package.json",
]

SECRET_PATTERNS = {
    "stripe_secret_key": re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_]{12,}\b"),
    "stripe_webhook_secret": re.compile(r"\bwhsec_[A-Za-z0-9_]{12,}\b"),
    "stripe_publishable_key": re.compile(r"\bpk_(?:live|test)_[A-Za-z0-9_]{12,}\b"),
    "stripe_checkout_session": re.compile(r"\bcs_(?:live|test)_[A-Za-z0-9_]{12,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(secret|api[_-]?key|token|password)\b\s*[:=]\s*['\"][^'\"]{12,}['\"]"
    ),
}

ROUTE_RE = re.compile(r"@(?:[\w_]+\.)?(?:route|get|post|put|patch|delete)\((?P<args>[^)]*)\)")
BLUEPRINT_RE = re.compile(r"\bBlueprint\(\s*['\"](?P<name>[^'\"]+)['\"]")
URL_FOR_STATIC_RE = re.compile(
    r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"](?P<asset>[^'\"]+)['\"]"
)
STATIC_PATH_RE = re.compile(r"(?P<asset>/static/[^'\"\s>)]+)")
INCLUDE_RE = re.compile(r"{%\s*(?:include|extends)\s+['\"](?P<template>[^'\"]+)['\"]")
HTML_ATTR_ASSET_RE = re.compile(r"""(?:href|src)=["'](?P<asset>[^"']+\.(?:css|js|png|jpg|jpeg|webp|svg|ico))(?:\?[^"']*)?["']""")

PAYMENT_WORDS = ("stripe", "checkout", "payment", "paypal", "webhook", "ledger", "receipt", "donation")
SURFACE_WORDS = {
    "campaign": ("campaign", "/c/", "connect-atx", "donate", "sponsor"),
    "platform": ("platform", "homepage", "launch"),
    "login": ("login", "operator-login"),
    "dashboard": ("dashboard", "operator"),
    "onboarding": ("onboarding", "onboard"),
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run(cmd: list[str], timeout: int = 12) -> str:
    try:
        return subprocess.check_output(
            cmd,
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        ).strip()
    except Exception as exc:
        return f"__ERROR__ {type(exc).__name__}: {exc}"


def safe_read(path: Path, limit: int = 1_500_000) -> str:
    try:
        if path.stat().st_size > limit:
            return path.read_text(encoding="utf-8", errors="replace")[:limit]
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def sha256_short(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(64_000), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


def should_skip(path: Path) -> bool:
    parts = set(path.parts)

    if os.getenv("FF_ACTIVE_MAP_INCLUDE_ARCHIVES") == "1":
        archive_ignores = {
            ".ff-backups",
            ".ff_backups",
            ".template-backups",
            ".local-artifacts",
            "_archive",
            "archive",
            "artifacts",
            "audit_outputs",
            "tmp",
        }
        return bool(parts & (IGNORE_DIRS - archive_ignores))

    return bool(parts & IGNORE_DIRS)


def walk_text_files() -> list[Path]:
    files: list[Path] = []
    scan_private_env = os.getenv("FF_ACTIVE_MAP_SCAN_ENV_FILES") == "1"

    for path in ROOT.rglob("*"):
        if should_skip(path) or not path.is_file():
            continue

        if is_private_runtime_file(path) and not scan_private_env:
            continue

        if path.suffix.lower() in TEXT_EXTS or (scan_private_env and path.name.startswith(".env")):
            files.append(path)

    return sorted(files)


def parse_package_scripts() -> dict[str, str]:
    p = ROOT / "package.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(safe_read(p))
        return data.get("scripts", {}) or {}
    except Exception:
        return {}


def parse_pm2() -> list[dict[str, Any]]:
    raw = run(["pm2", "jlist"], timeout=8)
    if raw.startswith("__ERROR__") or not raw:
        return [{"error": raw}]
    try:
        data = json.loads(raw)
    except Exception:
        return [{"error": "Could not parse pm2 jlist output"}]

    rows = []
    for item in data:
        env = item.get("pm2_env", {}) or {}
        rows.append(
            {
                "name": item.get("name"),
                "status": env.get("status"),
                "script": env.get("pm_exec_path"),
                "cwd": env.get("pm_cwd"),
                "version": env.get("version"),
                "restart_count": env.get("restart_time"),
                "watching": env.get("watch"),
            }
        )
    return rows


def env_snapshot() -> dict[str, Any]:
    interesting = {}
    for key, value in sorted(os.environ.items()):
        k = key.upper()
        if (
            k.startswith("FF_")
            or "STRIPE" in k
            or "POSTMARK" in k
            or "MAIL" in k
            or "DATABASE" in k
            or "FLASK" in k
            or "PAYPAL" in k
        ):
            mode = "present"
            if "pk_live_" in value or "sk_live_" in value or "cs_live_" in value:
                mode = "LIVE"
            elif "pk_test_" in value or "sk_test_" in value or "cs_test_" in value:
                mode = "TEST"
            elif value.strip() == "":
                mode = "empty"

            interesting[key] = {
                "state": mode,
                "length": len(value),
                "redacted": value[:4] + "…" + value[-4:] if len(value) >= 10 else "***",
            }
    return interesting


def classify_surface(path: str) -> list[str]:
    lower = path.lower()
    found = []
    for surface, words in SURFACE_WORDS.items():
        if any(word in lower for word in words):
            found.append(surface)
    return found or ["shared/unknown"]


def scan_routes(files: list[Path]) -> list[dict[str, Any]]:
    routes = []
    for path in files:
        if path.suffix != ".py":
            continue
        text = safe_read(path)
        if "route(" not in text and ".get(" not in text and ".post(" not in text:
            continue

        blueprints = BLUEPRINT_RE.findall(text)
        for match in ROUTE_RE.finditer(text):
            args = match.group("args").strip().replace("\n", " ")
            routes.append(
                {
                    "file": rel(path),
                    "decorator_args": re.sub(r"\s+", " ", args)[:300],
                    "blueprints_in_file": blueprints,
                    "payment_sensitive": any(w in (rel(path) + " " + args).lower() for w in PAYMENT_WORDS),
                    "surfaces": classify_surface(rel(path) + " " + args),
                }
            )
    return routes


def scan_templates(files: list[Path]) -> dict[str, Any]:
    templates = []
    asset_refs = []
    include_refs = []

    for path in files:
        if path.suffix.lower() not in {".html", ".jinja", ".j2"}:
            continue
        if "templates" not in path.parts:
            continue

        text = safe_read(path)
        local_assets = set()
        local_includes = set()

        for m in URL_FOR_STATIC_RE.finditer(text):
            asset = "static/" + m.group("asset").lstrip("/")
            local_assets.add(asset)

        for m in STATIC_PATH_RE.finditer(text):
            local_assets.add(m.group("asset").lstrip("/"))

        for m in HTML_ATTR_ASSET_RE.finditer(text):
            asset = m.group("asset")
            if asset.startswith("/"):
                asset = asset.lstrip("/")
            local_assets.add(asset)

        for m in INCLUDE_RE.finditer(text):
            local_includes.add(m.group("template"))

        templates.append(
            {
                "file": rel(path),
                "surfaces": classify_surface(rel(path) + " " + text[:2000]),
                "asset_count": len(local_assets),
                "include_count": len(local_includes),
            }
        )

        for asset in sorted(local_assets):
            asset_refs.append({"template": rel(path), "asset": asset})
        for inc in sorted(local_includes):
            include_refs.append({"template": rel(path), "include": inc})

    return {
        "templates": templates,
        "asset_refs": asset_refs,
        "include_refs": include_refs,
    }


def static_inventory() -> dict[str, Any]:
    base = ROOT / "apps/web/app/static"
    rows = []
    if not base.exists():
        return {"exists": False, "files": []}

    for path in sorted(base.rglob("*")):
        if path.is_file() and not should_skip(path):
            rows.append(
                {
                    "file": rel(path),
                    "kind": path.suffix.lower().lstrip(".") or "unknown",
                    "size": path.stat().st_size,
                    "sha256": sha256_short(path),
                    "surfaces": classify_surface(rel(path)),
                }
            )
    return {"exists": True, "files": rows}


def active_launchers() -> list[dict[str, Any]]:
    candidates = []
    for item in ENTRY_FILES:
        p = ROOT / item
        if p.exists():
            candidates.append(
                {
                    "file": item,
                    "exists": True,
                    "size": p.stat().st_size,
                    "sha256": sha256_short(p),
                }
            )

    for pattern in [
        "scripts/run*.sh",
        "scripts/serve*.sh",
        "scripts/release/*.sh",
        "scripts/release/*.mjs",
        "scripts/release/*.py",
        "scripts/verify/*.mjs",
    ]:
        for p in sorted(ROOT.glob(pattern)):
            candidates.append(
                {
                    "file": rel(p),
                    "exists": True,
                    "size": p.stat().st_size,
                    "sha256": sha256_short(p),
                }
            )
    return candidates


def secret_scan(files: list[Path]) -> list[dict[str, Any]]:
    findings = []
    for path in files:
        # Keep artifacts/docs in scan because old terminal dumps can accidentally preserve secrets.
        text = safe_read(path, limit=700_000)
        if not text:
            continue

        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                severity = "high"
                if name in {"stripe_publishable_key", "stripe_checkout_session"}:
                    severity = "medium"

                findings.append(
                    {
                        "type": name,
                        "severity": severity,
                        "file": rel(path),
                        "line": line,
                        "redacted_match": match.group(0)[:6] + "…" + match.group(0)[-4:],
                    }
                )
                if len(findings) >= 250:
                    return findings
    return findings


def derive_active_assets(template_scan: dict[str, Any], static_inv: dict[str, Any]) -> dict[str, Any]:
    refs = template_scan["asset_refs"]
    static_files = {row["file"] for row in static_inv.get("files", [])}
    active = []
    missing = []

    for ref in refs:
        asset = ref["asset"].split("?")[0].lstrip("/")
        candidates = [asset]
        if asset.startswith("static/"):
            candidates.append("apps/web/app/" + asset)
        if asset.startswith("css/") or asset.startswith("js/") or asset.startswith("images/"):
            candidates.append("apps/web/app/static/" + asset)

        exists = next((c for c in candidates if c in static_files or (ROOT / c).exists()), None)
        row = {**ref, "normalized": exists or candidates[-1], "exists": bool(exists)}
        if exists:
            active.append(row)
        else:
            missing.append(row)

    return {"active_refs": active, "missing_refs": missing}


def main() -> int:
    files = walk_text_files()

    git = {
        "branch": run(["git", "branch", "--show-current"]),
        "head": run(["git", "rev-parse", "--short", "HEAD"]),
        "status_short": run(["git", "status", "--short"]),
        "remote": run(["git", "remote", "-v"]),
    }

    package_scripts = parse_package_scripts()
    pm2 = parse_pm2()
    env = env_snapshot()
    launchers = active_launchers()
    routes = scan_routes(files)
    templates = scan_templates(files)
    static_inv = static_inventory()
    asset_map = derive_active_assets(templates, static_inv)
    secrets = secret_scan(files)

    payment_routes = [r for r in routes if r["payment_sensitive"]]
    css_files = [f for f in static_inv.get("files", []) if f["kind"] == "css"]
    js_files = [f for f in static_inv.get("files", []) if f["kind"] in {"js", "mjs"}]

    report = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "repo": str(ROOT),
        "git": git,
        "pm2": pm2,
        "env_snapshot_redacted": env,
        "launchers": launchers,
        "package_scripts": package_scripts,
        "routes": routes,
        "payment_sensitive_routes": payment_routes,
        "templates": templates,
        "static_inventory_summary": {
            "total": len(static_inv.get("files", [])),
            "css": len(css_files),
            "js": len(js_files),
        },
        "css_files": css_files,
        "js_files": js_files,
        "asset_linkage": asset_map,
        "secret_scan_findings": secrets,
        "recommendations": [],
    }

    recs = report["recommendations"]

    if any(f["type"] == "stripe_webhook_secret" for f in secrets):
        recs.append("Rotate Stripe webhook signing secret before accepting real donations; matching values were found in repo-visible text/log files.")
    if any(f["type"] == "stripe_secret_key" for f in secrets):
        recs.append("Audit and remove Stripe secret key literals from repo-visible files; keep only environment variables.")
    if any(v.get("state") == "TEST" for v in env.values()):
        recs.append("Current shell environment includes TEST payment values. Confirm PM2 production env has live Stripe keys before launch.")
    if asset_map["missing_refs"]:
        recs.append("Fix missing static asset references before cleanup; missing linked files can break trust surfaces.")
    if not payment_routes:
        recs.append("No payment-sensitive routes detected by static scan; verify route registration manually.")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    def bullet(items: list[str], limit: int = 50) -> str:
        if not items:
            return "- None found\n"
        return "".join(f"- `{x}`\n" for x in items[:limit]) + (f"- …and {len(items)-limit} more\n" if len(items) > limit else "")

    md = []
    md.append("# FutureFunded Active Repo Authority Map\n")
    md.append(f"Generated: `{report['generated_at']}`\n")
    md.append("\n## Launch verdict\n")
    if recs:
        md.append("Status: **CHECK REQUIRED**\n\n")
        for rec in recs:
            md.append(f"- {rec}\n")
    else:
        md.append("Status: **No immediate static blockers found by this mapper.**\n")

    md.append("\n## Git\n")
    md.append(f"- Branch: `{git['branch']}`\n")
    md.append(f"- HEAD: `{git['head']}`\n")
    md.append(f"- Working tree:\n\n```text\n{git['status_short'] or 'clean'}\n```\n")

    md.append("\n## PM2 processes\n")
    for proc in pm2:
        md.append(f"- `{proc.get('name')}` — status `{proc.get('status')}`, script `{proc.get('script')}`\n")

    md.append("\n## Launcher / entry files\n")
    md.append(bullet([x["file"] for x in launchers], limit=80))

    md.append("\n## Payment-sensitive routes\n")
    if payment_routes:
        for r in payment_routes[:120]:
            md.append(f"- `{r['file']}` → `{r['decorator_args']}`\n")
    else:
        md.append("- None detected\n")

    md.append("\n## Template include graph\n")
    for inc in templates["include_refs"][:160]:
        md.append(f"- `{inc['template']}` includes/extends `{inc['include']}`\n")
    if len(templates["include_refs"]) > 160:
        md.append(f"- …and {len(templates['include_refs']) - 160} more\n")

    md.append("\n## Linked static assets\n")
    active_assets = sorted({x["normalized"] for x in asset_map["active_refs"]})
    md.append(bullet(active_assets, limit=120))

    md.append("\n## Missing linked assets\n")
    missing_assets = sorted({x["normalized"] for x in asset_map["missing_refs"]})
    md.append(bullet(missing_assets, limit=120))

    md.append("\n## CSS files\n")
    md.append(bullet([x["file"] for x in css_files], limit=120))

    md.append("\n## JS files\n")
    md.append(bullet([x["file"] for x in js_files], limit=120))

    md.append("\n## Secret scan findings — redacted\n")
    if secrets:
        for f in secrets[:120]:
            md.append(f"- **{f['severity']}** `{f['type']}` in `{f['file']}` line `{f['line']}` match `{f['redacted_match']}`\n")
        if len(secrets) > 120:
            md.append(f"- …and {len(secrets) - 120} more redacted findings\n")
    else:
        md.append("- No obvious key/session literals found by this mapper.\n")

    md.append("\n## JSON artifact\n")
    md.append(f"- `{rel(OUT_JSON)}`\n")

    OUT_MD.write_text("".join(md), encoding="utf-8")

    print(f"Wrote {rel(OUT_JSON)}")
    print(f"Wrote {rel(OUT_MD)}")
    print()
    print("Top recommendations:")
    for rec in recs or ["No immediate static blockers found by this mapper."]:
        print(f"- {rec}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
