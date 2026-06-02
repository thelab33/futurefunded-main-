#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


DB_SECRET_RE = re.compile(
    r"(?:postgresql|postgres|mysql|mariadb)(?:\+[A-Za-z0-9_]+)?://[^@\s:/]+:[^@\s]+@",
    re.I,
)

SKIP_PREFIXES = (
    "node_modules/",
    ".venv/",
    "venv/",
    "audit_outputs/",
    ".ff_backups/",
    ".rollback/",
    "instance/",
)

PLACEHOLDER_DB_URL_RE = re.compile(
    r"("
    r"<[^>]+>"
    r"|\$\{[^}]+\}"
    r"|\{\{[^}]+\}\}"
    r"|user:pass(?:word)?@"
    r"|username:pass(?:word)?@"
    r"|db_user:db_pass(?:word)?@"
    r"|example:example@"
    r"|postgres:postgres@localhost"
    r"|postgres:password@"
    r"|USER:PASSWORD@"
    r"|USERNAME:PASSWORD@"
    r"|REPLACE_ME"
    r"|CHANGE_ME"
    r"|CHANGEME"
    r"|redacted"
    r"|xxxxx"
    r"|\*\*\*"
    r")",
    re.I,
)


def is_placeholder_db_url_context(rel: str, line: str, match_text: str) -> bool:
    haystack = f"{rel}\n{line}\n{match_text}"

    if PLACEHOLDER_DB_URL_RE.search(haystack):
        return True

    # Docs and templates often include examples. Only allow these when they are
    # clearly non-real placeholders. Real-looking passwords in docs still fail.
    if rel.startswith(("docs/", "scripts/", "README", "examples/", "deploy/", "infra/")):
        placeholder_words = (
            "example",
            "placeholder",
            "sample",
            "template",
            "change_me",
            "changeme",
            "replace",
            "your_",
            "<password>",
            "<user>",
            "<host>",
            "${",
            "{{",
        )
        return any(word.lower() in haystack.lower() for word in placeholder_words)

    return False


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)


def section(title):
    print()
    print(f"== {title} ==")


class Result:
    def __init__(self):
        self.passes = []
        self.warnings = []
        self.failures = []

    def ok(self, msg):
        self.passes.append(msg)
        print(f"✅ PASS: {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"⚠️ WARN: {msg}")

    def fail(self, msg):
        self.failures.append(msg)
        print(f"❌ FAIL: {msg}")


def repo_root():
    cp = run(["git", "rev-parse", "--show-toplevel"])
    if cp.returncode != 0:
        print("❌ Not inside a git repo.")
        sys.exit(2)
    root = Path(cp.stdout.strip()).resolve()
    os.chdir(root)
    return root


def parse_env(path: Path):
    values = {}
    if not path.exists():
        return values

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def val(key, env_values):
    return os.environ.get(key) or env_values.get(key, "")


def scheme(url):
    try:
        return urlparse(url).scheme.lower()
    except Exception:
        return ""


def host(url):
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_sqlite(url):
    low = (url or "").lower()
    return low.startswith("sqlite:") or low.endswith("/app.db") or (low.endswith(".db") and ("/instance/" in low or "/data/" in low))


def is_local(url):
    h = host(url)
    low = (url or "").lower()
    return h in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"} or "localhost" in low or "127.0.0.1" in low


def is_managed_style(url):
    s = scheme(url)
    return s in {"postgres", "postgresql", "mysql", "mariadb"} or s.startswith(("postgres+", "postgresql+", "mysql+", "mariadb+"))


def health(base_url):
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/healthz", timeout=8) as response:
            return 200 <= int(response.status) < 500
    except Exception:
        return False


def git_tracked(path):
    cp = run(["git", "ls-files", "--error-unmatch", path])
    return cp.returncode == 0


def git_status(paths):
    cp = run(["git", "status", "--short", "--", *paths])
    if cp.returncode != 0:
        return []
    return [x for x in cp.stdout.splitlines() if x.strip()]


def tracked_files():
    cp = run(["git", "ls-files"])
    if cp.returncode != 0:
        return []
    return [x.strip() for x in cp.stdout.splitlines() if x.strip()]


def scan_tracked_db_urls(root: Path):
    findings = []
    for rel in tracked_files():
        if rel.startswith(SKIP_PREFIXES):
            continue

        p = root / rel
        if not p.is_file():
            continue

        try:
            if p.stat().st_size > 2_000_000:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for idx, line in enumerate(text.splitlines(), 1):
            matches = list(DB_SECRET_RE.finditer(line))
            if not matches:
                continue

            real_matches = []
            for match in matches:
                match_text = match.group(0)
                if is_placeholder_db_url_context(rel, line, match_text):
                    continue
                real_matches.append(match_text)

            if real_matches:
                findings.append(f"{rel}:{idx}: possible real DB credential URL")
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--env-file", default=os.environ.get("FF_ENV_FILE", ".env"))
    parser.add_argument("--out", default=os.environ.get("FF_MANAGED_DB_BACKUP_OUT", f"audit_outputs/managed-db-backup-readiness-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"))
    parser.add_argument("--strict", action="store_true", default=os.environ.get("FF_REQUIRE_MANAGED_DB", "0") == "1")
    args = parser.parse_args()

    root = repo_root()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    env_values = parse_env(Path(args.env_file))
    result = Result()

    section("FutureFunded Managed DB / Backup Readiness Gate")
    print(f"ROOT={root}")
    print(f"BASE_URL={args.base_url}")
    print(f"ENV_FILE={args.env_file}")
    print(f"STRICT={args.strict}")
    print(f"OUT={out}")

    section("1. Required docs")
    if Path("docs/release/futurefunded-managed-db-backup-readiness.md").exists():
        result.ok("Managed DB backup readiness doc exists")
    else:
        result.fail("Missing managed DB backup readiness doc")

    if Path("docs/release/futurefunded-private-config-handoff.md").exists():
        result.ok("Private config handoff doc exists")
    else:
        result.warn("Private config handoff doc missing")

    section("2. Health smoke")
    if health(args.base_url):
        result.ok("Health endpoint reachable")
    else:
        result.warn(f"Health endpoint not reachable at {args.base_url.rstrip('/')}/healthz")

    section("3. Database URL boundary")
    database_url = val("DATABASE_URL", env_values)

    print(f"DATABASE_URL_present={bool(database_url)}")
    print(f"DATABASE_URL_scheme={scheme(database_url) or '<missing>'}")
    print(f"DATABASE_URL_is_sqlite={is_sqlite(database_url)}")
    print(f"DATABASE_URL_is_local={is_local(database_url)}")
    print(f"DATABASE_URL_is_managed_style={is_managed_style(database_url)}")

    if args.strict:
        if not database_url:
            result.fail("Strict mode requires DATABASE_URL")
        elif is_sqlite(database_url):
            result.fail("Strict mode forbids SQLite DATABASE_URL")
        elif is_local(database_url):
            result.fail("Strict mode forbids local-only database URL")
        elif not is_managed_style(database_url):
            result.fail("Strict mode DATABASE_URL is not recognized as managed PostgreSQL/MySQL style")
        else:
            result.ok("Strict mode DATABASE_URL appears managed-style")
    else:
        if not database_url:
            result.warn("DATABASE_URL missing; acceptable only before production DB setup")
        elif is_sqlite(database_url):
            result.ok("Local SQLite accepted for demo/dev boundary mode")
            result.warn("Managed production DB still required before live users")
        elif is_local(database_url):
            result.warn("Local DB URL detected; acceptable only before live users")
        elif is_managed_style(database_url):
            result.ok("DATABASE_URL appears managed-style")
        else:
            result.warn("DATABASE_URL present but provider style is unrecognized")

    section("4. Backup metadata")

    provider = val("FF_DB_BACKUP_PROVIDER", env_values)
    policy = val("FF_DB_BACKUP_POLICY", env_values)
    retention = val("FF_DB_BACKUP_RETENTION_DAYS", env_values)
    restored = val("FF_DB_RESTORE_TESTED_AT", env_values)
    owner = val("FF_DB_MIGRATION_OWNER", env_values)
    pitr = val("FF_DB_PITR_ENABLED", env_values)

    metadata = [
        ("FF_DB_BACKUP_PROVIDER", provider, "Backup provider metadata"),
        ("FF_DB_BACKUP_POLICY", policy, "Backup policy metadata"),
        ("FF_DB_RESTORE_TESTED_AT", restored, "Restore drill metadata"),
        ("FF_DB_MIGRATION_OWNER", owner, "Migration owner metadata"),
    ]

    for key, value, label in metadata:
        print(f"{key}_present={bool(value)}")
        if value:
            result.ok(f"{label} present")
        elif args.strict:
            result.fail(f"Strict mode requires {key}")
        else:
            result.warn(f"{label} not configured yet")

    print(f"FF_DB_BACKUP_RETENTION_DAYS_present={bool(retention)}")
    if retention:
        try:
            days = int(retention)
        except Exception:
            days = 0
        if days >= 7:
            result.ok("Backup retention is at least 7 days")
        elif args.strict:
            result.fail("Strict mode requires FF_DB_BACKUP_RETENTION_DAYS >= 7")
        else:
            result.warn("Backup retention should be at least 7 days")
    elif args.strict:
        result.fail("Strict mode requires FF_DB_BACKUP_RETENTION_DAYS")
    else:
        result.warn("Backup retention metadata not configured yet")

    print(f"FF_DB_PITR_ENABLED_present={bool(pitr)}")
    if pitr:
        result.ok("PITR metadata present")
    else:
        result.warn("PITR metadata not configured yet; recommended if provider supports it")

    section("5. Git safety")

    if git_tracked(".env"):
        result.fail(".env is tracked; secrets must not be committed")
    else:
        result.ok(".env is not tracked")

    generated = git_status(["audit_outputs", ".ff_backups", ".rollback"])
    if generated:
        result.fail("Generated local output appears in git status")
        for item in generated[:20]:
            print(item)
    else:
        result.ok("No generated local output staged/modified in git status")

    section("6. Tracked DB credential scan")
    findings = scan_tracked_db_urls(root)
    scan_path = out / "tracked-db-secret-scan.txt"

    if findings:
        scan_path.write_text("\n".join(findings) + "\n", encoding="utf-8")
        result.fail(f"Possible tracked DB credential URL found. See {scan_path}")
    else:
        scan_path.write_text("No obvious tracked DB credential URLs found.\n", encoding="utf-8")
        result.ok("No obvious tracked DB credential URLs found")

    section("7. Final verdict")
    summary = {
        "strict": args.strict,
        "passes": result.passes,
        "warnings": result.warnings,
        "failures": result.failures,
        "pass_count": len(result.passes),
        "warning_count": len(result.warnings),
        "failure_count": len(result.failures),
    }
    (out / "managed-db-backup-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if result.failures:
        print("❌ MANAGED_DB_BACKUP_GATE=FAIL")
        print(f"Failures: {len(result.failures)}")
        print(f"Warnings: {len(result.warnings)}")
        return 1

    if result.warnings:
        print("✅ MANAGED_DB_BACKUP_GATE=PASS_WITH_BOUNDARIES")
        print(f"Warnings: {len(result.warnings)}")
        return 0

    print("✅ MANAGED_DB_BACKUP_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
