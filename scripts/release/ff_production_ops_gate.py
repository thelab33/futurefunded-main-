#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
OUT = Path(os.environ.get("FF_PRODUCTION_OPS_OUT", "audit_outputs/production-ops-pack-manual"))
OUT.mkdir(parents=True, exist_ok=True)

failures = 0
warnings = 0

def passed(label: str) -> None:
    print(f"✅ PASS: {label}")

def warn(label: str) -> None:
    global warnings
    warnings += 1
    print(f"⚠️ WARN: {label}")

def fail(label: str) -> None:
    global failures
    failures += 1
    print(f"❌ FAIL: {label}")

def run_capture(label: str, cmd: list[str], outfile: Path, env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=merged_env)
    outfile.write_text(proc.stdout, encoding="utf-8", errors="replace")

    if proc.returncode == 0:
        passed(label)
    else:
        fail(label)

    lines = proc.stdout.splitlines()
    for line in lines[-45:]:
        print(line)

def http_ok(path: str) -> bool:
    try:
        with urllib.request.urlopen(BASE_URL + path, timeout=20) as response:
            return 200 <= response.status < 400
    except Exception:
        return False

def load_env_file(path: Path = Path(".env")) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            data[key] = value
    return data

print("== FutureFunded Production Ops Gate ==")
print(f"BASE_URL={BASE_URL}")
print()

print("== 1. Required release docs ==")
required_docs = [
    "docs/release/futurefunded-platform-live-readiness-lock.md",
    "docs/release/futurefunded-money-ops-status.md",
    "docs/release/futurefunded-money-ops-pass-1a-ledger-proof.md",
    "docs/release/futurefunded-money-ops-pass-1b-stripe-webhook-proof.md",
    "docs/release/futurefunded-money-ops-pass-2-email-delivery-readiness.md",
    "docs/release/futurefunded-private-config-handoff.md",
]
for name in required_docs:
    if Path(name).exists():
        passed(name)
    else:
        warn(f"Missing recommended release doc: {name}")

print()
print("== 2. Core health and readiness gates ==")
if http_ok("/healthz"):
    passed("Health endpoint")
else:
    fail("Health endpoint")

if Path("scripts/release/ff_platform_live_readiness_gate.sh").exists():
    run_capture(
        "Platform live readiness gate",
        ["bash", "scripts/release/ff_platform_live_readiness_gate.sh"],
        OUT / "platform-live-readiness.txt",
        {"FF_BASE_URL": BASE_URL, "FF_LIVE_READINESS_OUT": str(OUT / "platform-live-readiness")},
    )
else:
    fail("Missing platform live readiness gate")

print()
print("== 3. Secret scanner for tracked files ==")
tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
binary_ext = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".webm", ".zip", ".sqlite", ".db"
}
fail_patterns = [
    ("live_stripe_secret", re.compile(r"\b(?:sk_live|rk_live|pk_live)_[A-Za-z0-9]{24,}\b")),
    ("private_key_block", re.compile(r"BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY")),
]
warn_patterns = [
    ("test_stripe_secret", re.compile(r"\bsk_test_[A-Za-z0-9]{24,}\b")),
    ("stripe_webhook_secret", re.compile(r"\bwhsec_[A-Za-z0-9]{24,}\b")),
]

secret_failures = []
secret_warnings = []

for name in tracked:
    path = Path(name)
    if path.suffix.lower() in binary_ext:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    for label, pattern in fail_patterns:
        for match in pattern.finditer(text):
            secret_failures.append((label, name, match.group(0)[:20] + "<redacted>"))

    for label, pattern in warn_patterns:
        for match in pattern.finditer(text):
            token = match.group(0)
            if "REPLACE_ME" in token or "example" in name.lower():
                continue
            secret_warnings.append((label, name, token[:16] + "<redacted>"))

secret_report = OUT / "secret-scan.txt"
secret_report.write_text(
    "\n".join(
        [f"tracked_file_secret_failures={len(secret_failures)}"]
        + [f"FAIL {item}" for item in secret_failures[:20]]
        + [f"tracked_file_secret_warnings={len(secret_warnings)}"]
        + [f"WARN {item}" for item in secret_warnings[:20]]
    )
    + "\n",
    encoding="utf-8",
)

print(secret_report.read_text())
if secret_failures:
    fail("Tracked secret scan has blocking findings")
else:
    passed("Tracked secret scan has no blocking findings")

print()
print("== 4. Runtime env production boundaries ==")
env = load_env_file()
checks = {
    "DATABASE_URL_present": bool(env.get("DATABASE_URL")),
    "DATABASE_URL_is_local_sqlite": env.get("DATABASE_URL") == "sqlite:///instance/futurefunded-dev.db",
    "FORBID_LIVE_KEYS_enabled": env.get("FF_FORBID_LIVE_KEYS") == "1",
    "LIVE_STRIPE_ENFORCEMENT_disabled_for_local": env.get("FF_STRIPE_ENFORCE_LIVE_KEYS", "") in {"", "0"},
    "STRIPE_test_key_present": env.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"),
    "STRIPE_webhook_secret_present": env.get("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"),
    "EMAIL_dry_run_enabled": env.get("FF_EMAIL_DRY_RUN") == "1",
    "SMTP_configured": bool(env.get("FF_SMTP_HOST") and env.get("FF_SMTP_USERNAME") and env.get("FF_SMTP_PASSWORD")),
    "PAYPAL_disabled_or_missing": env.get("PAYPAL_MODE", "") in {"", "disabled"},
}

runtime_lines = []
for key, value in checks.items():
    line = f"{key}={value}"
    runtime_lines.append(line)
    print(line)

print()
print("PRODUCTION_BOUNDARIES:")
boundary_lines = []
if checks["DATABASE_URL_is_local_sqlite"]:
    boundary_lines.append("- Managed production DB still required before live users.")
if checks["FORBID_LIVE_KEYS_enabled"]:
    boundary_lines.append("- Live Stripe keys are intentionally blocked locally.")
if not checks["SMTP_configured"]:
    boundary_lines.append("- Real SMTP/provider email delivery still requires private credentials.")
if checks["PAYPAL_disabled_or_missing"]:
    boundary_lines.append("- PayPal is disabled/not configured; keep out of launch scope unless explicitly added.")

for line in boundary_lines:
    print(line)

(OUT / "runtime-boundaries.txt").write_text(
    "\n".join(runtime_lines + ["", "PRODUCTION_BOUNDARIES:"] + boundary_lines) + "\n",
    encoding="utf-8",
)

if checks["DATABASE_URL_present"]:
    passed("Database URL present")
else:
    fail("Database URL missing")

if checks["FORBID_LIVE_KEYS_enabled"]:
    passed("Live payment kill switch enabled locally")
else:
    fail("Live payment kill switch not enabled")

if checks["SMTP_configured"]:
    passed("SMTP configured")
else:
    warn("SMTP not configured; real email delivery remains a production boundary")

print()
print("== 5. Git safety ==")
git_status = subprocess.check_output(["git", "status", "--short"], text=True)
(OUT / "git-status.txt").write_text(git_status, encoding="utf-8")
print(git_status, end="")

if re.search(r"^.. \.env$|^\?\? \.env$|^.. \.env\.email\.local$|^\?\? \.env\.email\.local$|audit_outputs/|\.ff_backups/", git_status, re.M):
    warn("Local/generated files are present. Do not commit them.")
else:
    passed("No obvious local/generated files in git status")

print()
print("== 6. Final production ops verdict ==")
if failures == 0:
    print("✅ PRODUCTION_OPS_GATE=PASS_WITH_BOUNDARIES")
    print(f"Warnings: {warnings}")
else:
    print("❌ PRODUCTION_OPS_GATE=FAIL")
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")
    raise SystemExit(1)
