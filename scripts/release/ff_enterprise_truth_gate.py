#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d%H%M%S")
OUT = Path(os.environ.get("FF_ENTERPRISE_TRUTH_OUT", f"audit_outputs/enterprise-truth-gate-{STAMP}"))
BASE_URL = os.environ.get("FF_BASE_URL", "http://127.0.0.1:5000")
STRICT = os.environ.get("FF_ENTERPRISE_TRUTH_STRICT", "0") == "1"
FAST = os.environ.get("FF_ENTERPRISE_TRUTH_FAST", "1") == "1"
OUT.mkdir(parents=True, exist_ok=True)

GREEN = "GREEN"
YELLOW = "YELLOW"
RED = "RED"

def run(cmd, timeout=35):
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": p.returncode,
            "stdout": p.stdout[-8000:],
            "stderr": p.stderr[-8000:],
        }
    except Exception as exc:
        return {
            "cmd": " ".join(cmd),
            "returncode": 99,
            "stdout": "",
            "stderr": str(exc),
        }

def exists(path):
    return (ROOT / path).exists()

def env_present(name):
    return bool(os.environ.get(name))

def status_from_rc(rc, yellow_ok=True):
    if rc == 0:
        return GREEN
    return YELLOW if yellow_ok else RED

checks = []

def add(name, status, weight, evidence, recommendation=""):
    checks.append({
        "name": name,
        "status": status,
        "weight": weight,
        "evidence": evidence,
        "recommendation": recommendation,
    })

def run_gate(name, cmd, weight, yellow_ok=True, recommendation=""):
    result = run(cmd)
    log_name = name.lower().replace(" ", "-").replace("/", "-") + ".log"
    (OUT / log_name).write_text(
        f"$ {' '.join(cmd)}\n\nSTDOUT:\n{result['stdout']}\n\nSTDERR:\n{result['stderr']}\n",
        encoding="utf-8",
    )
    add(
        name,
        status_from_rc(result["returncode"], yellow_ok=yellow_ok),
        weight,
        f"rc={result['returncode']} log={OUT / log_name}",
        recommendation,
    )

print("== FutureFunded Enterprise Truth Gate ==")
print(f"ROOT={ROOT}")
print(f"BASE_URL={BASE_URL}")
print(f"STRICT={STRICT}")
print(f"FAST={FAST}")
print(f"OUT={OUT}")
print()

# Core runnable gates
if exists("scripts/release/ff_platform_live_readiness_gate.sh"):
    run_gate(
        "Platform live readiness",
        ["bash", "scripts/release/ff_platform_live_readiness_gate.sh"],
        10,
        yellow_ok=False if STRICT else True,
        recommendation="Fix platform live readiness failures before production launch.",
    )
else:
    add("Platform live readiness", RED, 10, "missing ff_platform_live_readiness_gate.sh")

if exists("scripts/release/ff_money_ops_current_gate.sh"):
    run_gate(
        "Money ops current gate",
        ["bash", "scripts/release/ff_money_ops_current_gate.sh"],
        12,
        yellow_ok=False if STRICT else True,
        recommendation="Money ops must be green before real donor traffic.",
    )
else:
    add("Money ops current gate", RED, 12, "missing ff_money_ops_current_gate.sh")

if exists("scripts/release/ff_production_ops_gate.sh"):
    if FAST:
        add(
            "Production ops gate",
            YELLOW,
            10,
            "present but skipped in FAST mode",
            "Run bash scripts/release/ff_production_ops_gate.sh directly for full proof.",
        )
    else:
        run_gate(
            "Production ops gate",
            ["bash", "scripts/release/ff_production_ops_gate.sh"],
            10,
            yellow_ok=True,
            recommendation="Resolve production boundary warnings before public launch.",
        )
else:
    add("Production ops gate", RED, 10, "missing ff_production_ops_gate.sh")

if exists("scripts/release/ff_production_host_readiness_gate.py"):
    run_gate(
        "Production host readiness",
        [
            sys.executable,
            "scripts/release/ff_production_host_readiness_gate.py",
            "--base-url",
            BASE_URL,
            "--out",
            str(OUT / "host-readiness"),
        ],
        10,
        yellow_ok=True,
        recommendation="Configure production host provider, app URL, domain, TLS, deploy, rollback, and owner.",
    )
else:
    add("Production host readiness", RED, 10, "missing ff_production_host_readiness_gate.py")

if exists("scripts/release/ff_managed_db_backup_gate.py"):
    run_gate(
        "Managed database backup readiness",
        [sys.executable, "scripts/release/ff_managed_db_backup_gate.py"],
        8,
        yellow_ok=True,
        recommendation="Move from local SQLite/demo DB to managed Postgres with backup evidence.",
    )
else:
    add("Managed database backup readiness", RED, 8, "missing ff_managed_db_backup_gate.py")

if exists("scripts/release/ff_email_delivery_readiness_gate.py"):
    run_gate(
        "Email delivery readiness",
        [sys.executable, "scripts/release/ff_email_delivery_readiness_gate.py"],
        8,
        yellow_ok=True,
        recommendation="Configure SMTP/provider and controlled real-send proof.",
    )
else:
    add("Email delivery readiness", RED, 8, "missing ff_email_delivery_readiness_gate.py")

# Static truth checks
deploy_files = [p for p in ["render.yaml", "Procfile", "Dockerfile", "docker-compose.yml", "railway.json", "fly.toml"] if exists(p)]
add(
    "Deploy artifact presence",
    GREEN if deploy_files else RED,
    6,
    ", ".join(deploy_files) if deploy_files else "No deploy artifacts found",
    "Add render.yaml/Procfile/Dockerfile or selected host deploy config.",
)

domain_env = [
    "FF_PRODUCTION_HOST_PROVIDER",
    "FF_PRODUCTION_APP_URL",
    "FF_PRODUCTION_DOMAIN",
    "FF_PRODUCTION_TLS_ENABLED",
    "FF_DEPLOY_COMMAND",
    "FF_ROLLBACK_COMMAND",
    "FF_DEPLOY_OWNER",
]
present = [k for k in domain_env if env_present(k)]
add(
    "Production metadata configured",
    GREEN if len(present) == len(domain_env) else YELLOW if present else RED,
    8,
    f"{len(present)}/{len(domain_env)} present: {', '.join(present) if present else 'none'}",
    "Set production host metadata in private env before strict launch.",
)

monitoring_env = ["SENTRY_DSN", "FF_UPTIME_MONITOR_URL", "BETTER_STACK_SOURCE_TOKEN", "LOGTAIL_SOURCE_TOKEN"]
monitoring_present = [k for k in monitoring_env if env_present(k)]
monitoring_docs = any(exists(p) for p in [
    "docs/release/futurefunded-monitoring-readiness.md",
    "docs/release/futurefunded-incident-response-lite.md",
])
add(
    "Monitoring configured",
    GREEN if monitoring_present else YELLOW if monitoring_docs else RED,
    8,
    f"env={monitoring_present or 'none'} docs={'yes' if monitoring_docs else 'no'}",
    "Add Sentry and uptime monitoring proof before public launch.",
)

restore_docs = any(exists(p) for p in [
    "docs/release/futurefunded-db-restore-proof.md",
    "docs/release/futurefunded-managed-db-backup-readiness.md",
])
restore_script = any(exists(p) for p in [
    "scripts/release/ff_db_restore_drill.py",
    "scripts/release/ff_managed_db_restore_gate.py",
])
add(
    "Restore drill proof",
    GREEN if restore_script else YELLOW if restore_docs else RED,
    8,
    f"restore_script={'yes' if restore_script else 'no'} restore_docs={'yes' if restore_docs else 'no'}",
    "Build and run a non-destructive restore drill against managed Postgres backup.",
)

onboarding_files = list(ROOT.glob("**/*onboarding*"))
onboarding_files = [p for p in onboarding_files if ".git" not in p.parts and "node_modules" not in p.parts and "audit_outputs" not in p.parts]
add(
    "Customer onboarding surface",
    GREEN if len(onboarding_files) >= 5 else YELLOW if onboarding_files else RED,
    7,
    f"{len(onboarding_files)} onboarding-related files",
    "Verify customer-zero org creation can happen without code edits.",
)

billing_terms = []
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix.lower() in {".py", ".js", ".ts", ".md", ".html", ".sh"} and "node_modules" not in p.parts and ".git" not in p.parts:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
        if "subscription" in txt or "billing portal" in txt or "stripe_price" in txt or "price_id" in txt:
            billing_terms.append(str(p.relative_to(ROOT)))
add(
    "Subscription billing evidence",
    GREEN if len(set(billing_terms)) >= 5 else YELLOW if billing_terms else RED,
    5,
    f"{len(set(billing_terms))} billing/subscription files",
    "Add SaaS subscription/customer billing gate if not yet runnable.",
)

score_total = sum(c["weight"] for c in checks)
score_got = 0
for c in checks:
    if c["status"] == GREEN:
        score_got += c["weight"]
    elif c["status"] == YELLOW:
        score_got += c["weight"] * 0.5

score = round((score_got / score_total) * 100) if score_total else 0

if score >= 90 and not any(c["status"] == RED for c in checks):
    classification = "PRODUCTION_READY_CANDIDATE"
elif score >= 75:
    classification = "PRE_PRODUCTION_READY"
elif score >= 55:
    classification = "DEMO_READY_WITH_ENTERPRISE_GAPS"
else:
    classification = "NOT_LAUNCH_READY"

report = {
    "stamp": STAMP,
    "root": str(ROOT),
    "base_url": BASE_URL,
    "strict": STRICT,
    "score": score,
    "classification": classification,
    "checks": checks,
}

(OUT / "enterprise-truth-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

md = []
md.append("# FutureFunded Enterprise Truth Board")
md.append("")
md.append(f"- Score: **{score}/100**")
md.append(f"- Classification: **{classification}**")
md.append(f"- Base URL: `{BASE_URL}`")
md.append(f"- Strict: `{STRICT}`")
md.append("")
md.append("| Area | Status | Weight | Evidence |")
md.append("|---|---:|---:|---|")
for c in checks:
    md.append(f"| {c['name']} | **{c['status']}** | {c['weight']} | `{c['evidence']}` |")
md.append("")
md.append("## Recommendations")
for c in checks:
    if c["status"] != GREEN and c["recommendation"]:
        md.append(f"- **{c['name']}**: {c['recommendation']}")
(OUT / "enterprise-truth-board.md").write_text("\n".join(md) + "\n", encoding="utf-8")

print("====================================")
print("FutureFunded Enterprise Truth Board")
print("====================================")
for c in checks:
    print(f"{c['name']:<38} {c['status']:<6} weight={c['weight']} evidence={c['evidence']}")
print()
print(f"FINAL_SCORE={score}/100")
print(f"LAUNCH_CLASSIFICATION={classification}")
print(f"REPORT={OUT / 'enterprise-truth-board.md'}")

if STRICT and (classification != "PRODUCTION_READY_CANDIDATE" or any(c["status"] == RED for c in checks)):
    sys.exit(1)
