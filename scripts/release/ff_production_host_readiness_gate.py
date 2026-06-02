#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


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


def is_https_url(url):
    try:
        return urlparse(url).scheme.lower() == "https"
    except Exception:
        return False


def is_local_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
    except Exception:
        return True

    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local")


def health(url):
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/healthz", timeout=10) as response:
            return 200 <= int(response.status) < 500
    except Exception:
        return False


def url_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return 200 <= int(response.status) < 500
    except Exception:
        return False


def git_tracked(path):
    return run(["git", "ls-files", "--error-unmatch", path]).returncode == 0


def git_status(paths):
    cp = run(["git", "status", "--short", "--", *paths])
    if cp.returncode != 0:
        return []
    return [x for x in cp.stdout.splitlines() if x.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--env-file", default=os.environ.get("FF_ENV_FILE", ".env"))
    parser.add_argument("--out", default=os.environ.get("FF_PRODUCTION_HOST_OUT", f"audit_outputs/production-host-readiness-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"))
    parser.add_argument("--strict", action="store_true", default=os.environ.get("FF_REQUIRE_PRODUCTION_HOST", "0") == "1")
    args = parser.parse_args()

    root = repo_root()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    env_values = parse_env(Path(args.env_file))
    result = Result()

    section("FutureFunded Production Host / Deploy Readiness Gate")
    print(f"ROOT={root}")
    print(f"BASE_URL={args.base_url}")
    print(f"ENV_FILE={args.env_file}")
    print(f"STRICT={args.strict}")
    print(f"OUT={out}")

    section("1. Required docs")
    required_docs = [
        "docs/release/futurefunded-production-host-deploy-readiness.md",
        "docs/release/futurefunded-private-config-handoff.md",
        "docs/release/futurefunded-managed-db-backup-readiness.md",
    ]

    for doc in required_docs:
        if Path(doc).exists():
            result.ok(f"{doc} exists")
        else:
            result.fail(f"Missing {doc}")

    section("2. Local/current health checks")
    if health(args.base_url):
        result.ok("Health endpoint reachable")
    else:
        result.warn(f"Health endpoint not reachable at {args.base_url.rstrip('/')}/healthz")

    for route in ["/platform/", "/c/connect-atx-elite"]:
        full_url = args.base_url.rstrip("/") + route
        if url_ok(full_url):
            result.ok(f"Route reachable: {route}")
        else:
            result.warn(f"Route not reachable: {route}")

    section("3. Production host metadata")

    provider = val("FF_PRODUCTION_HOST_PROVIDER", env_values)
    app_url = val("FF_PRODUCTION_APP_URL", env_values)
    domain = val("FF_PRODUCTION_DOMAIN", env_values)
    tls = val("FF_PRODUCTION_TLS_ENABLED", env_values)
    deploy_cmd = val("FF_DEPLOY_COMMAND", env_values)
    rollback_cmd = val("FF_ROLLBACK_COMMAND", env_values)
    owner = val("FF_DEPLOY_OWNER", env_values)

    values = {
        "FF_PRODUCTION_HOST_PROVIDER": provider,
        "FF_PRODUCTION_APP_URL": app_url,
        "FF_PRODUCTION_DOMAIN": domain,
        "FF_PRODUCTION_TLS_ENABLED": tls,
        "FF_DEPLOY_COMMAND": deploy_cmd,
        "FF_ROLLBACK_COMMAND": rollback_cmd,
        "FF_DEPLOY_OWNER": owner,
    }

    for key, value in values.items():
        print(f"{key}_present={bool(value)}")

    required = [
        ("FF_PRODUCTION_HOST_PROVIDER", provider, "Production host provider"),
        ("FF_PRODUCTION_APP_URL", app_url, "Production app URL"),
        ("FF_PRODUCTION_DOMAIN", domain, "Production domain"),
        ("FF_PRODUCTION_TLS_ENABLED", tls, "TLS metadata"),
        ("FF_DEPLOY_COMMAND", deploy_cmd, "Deploy command"),
        ("FF_ROLLBACK_COMMAND", rollback_cmd, "Rollback command"),
        ("FF_DEPLOY_OWNER", owner, "Deploy owner"),
    ]

    for key, value, label in required:
        if value:
            result.ok(f"{label} present")
        elif args.strict:
            result.fail(f"Strict mode requires {key}")
        else:
            result.warn(f"{label} not configured yet")

    if app_url:
        if is_https_url(app_url):
            result.ok("Production app URL uses HTTPS")
        elif args.strict:
            result.fail("Strict mode requires FF_PRODUCTION_APP_URL to use HTTPS")
        else:
            result.warn("Production app URL should use HTTPS")

        if is_local_url(app_url):
            if args.strict:
                result.fail("Strict mode forbids local production app URL")
            else:
                result.warn("Production app URL appears local; acceptable only before hosted deploy")
        else:
            result.ok("Production app URL is not local-only")

    if tls:
        normalized_tls = tls.strip().lower()
        if normalized_tls in {"1", "true", "yes", "enabled"}:
            result.ok("TLS metadata indicates enabled")
        elif args.strict:
            result.fail("Strict mode requires FF_PRODUCTION_TLS_ENABLED=true")
        else:
            result.warn("TLS metadata does not indicate enabled")

    section("4. Git safety")

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

    section("5. Final verdict")
    summary = {
        "strict": args.strict,
        "base_url": args.base_url,
        "passes": result.passes,
        "warnings": result.warnings,
        "failures": result.failures,
        "pass_count": len(result.passes),
        "warning_count": len(result.warnings),
        "failure_count": len(result.failures),
    }

    (out / "production-host-readiness-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if result.failures:
        print("❌ PRODUCTION_HOST_READINESS_GATE=FAIL")
        print(f"Failures: {len(result.failures)}")
        print(f"Warnings: {len(result.warnings)}")
        return 1

    if result.warnings:
        print("✅ PRODUCTION_HOST_READINESS_GATE=PASS_WITH_BOUNDARIES")
        print(f"Warnings: {len(result.warnings)}")
        return 0

    print("✅ PRODUCTION_HOST_READINESS_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
