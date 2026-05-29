#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
INVENTORY_SCRIPT = ROOT / "scripts" / "audit" / "backend_inventory.py"
INVENTORY_JSON = ROOT / "docs" / "audits" / "backend-inventory" / "backend-inventory.json"
OUT_DIR = ROOT / "docs" / "audits" / "release-gate"
OUT_JSON = OUT_DIR / "release-gate-summary.json"


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"⚠️  Ignoring invalid {name}={raw!r}; using {default}.")
        return default


def fail(message: str, details: list[str] | None = None) -> int:
    print()
    print("🚫 FutureFunded release gate failed")
    print("=" * 42)
    print(message)
    if details:
        print()
        for item in details:
            print(f" - {item}")
    print()
    return 1


def load_inventory() -> dict[str, Any]:
    if not INVENTORY_JSON.exists():
        raise FileNotFoundError(f"Missing inventory JSON: {INVENTORY_JSON}")
    return json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))


def finding_label(item: dict[str, Any]) -> str:
    location = ""
    if item.get("file"):
        location = f" ({item.get('file')}:{item.get('line') or ''})"
    return f"[{item.get('severity')}] {item.get('title')}{location} — {item.get('detail')}"


def main() -> int:
    if not INVENTORY_SCRIPT.exists():
        return fail(f"Missing inventory script: {INVENTORY_SCRIPT}")

    print()
    print("🚀 FutureFunded release gate")
    print("=" * 42)
    print("Running backend inventory...")

    result = subprocess.run(
        [sys.executable, str(INVENTORY_SCRIPT)],
        cwd=ROOT,
        text=True,
    )

    try:
        data = load_inventory()
    except Exception as exc:
        return fail(f"Could not load backend inventory JSON: {exc}")

    findings = data.get("findings", [])
    severity_counts = Counter(item.get("severity", "unknown") for item in findings)

    error_findings = [item for item in findings if item.get("severity") == "error"]
    warning_findings = [item for item in findings if item.get("severity") == "warning"]

    route_total = int(data.get("flask", {}).get("route_counts", {}).get("total") or 0)
    blueprint_total = len(data.get("flask", {}).get("blueprints", []) or [])
    model_total = len(data.get("models", []) or [])
    active_python_files = int(data.get("files", {}).get("active_python_files") or data.get("files", {}).get("python_files") or 0)

    min_routes = env_int("FF_GATE_MIN_ROUTES", 40)
    min_blueprints = env_int("FF_GATE_MIN_BLUEPRINTS", 4)
    min_models = env_int("FF_GATE_MIN_MODELS", 10)

    strict = env_bool("FF_GATE_STRICT", False)
    require_clean_tree = env_bool("FF_GATE_REQUIRE_CLEAN_TREE", False)
    require_live_stack = env_bool("FF_GATE_REQUIRE_LIVE_STACK", False)

    live_stack_blocker_titles = {
        "Production-like env uses SQLite",
        "Production-like env uses Stripe test key",
        "Production-like env has MAIL_ENABLED=false",
    }

    strict_warning_findings = [
        item for item in warning_findings
        if item.get("title") not in live_stack_blocker_titles
    ]

    blockers: list[str] = []

    if result.returncode != 0:
        blockers.append(f"backend_inventory.py exited with status {result.returncode}")

    if error_findings:
        blockers.extend(finding_label(item) for item in error_findings)

    if active_python_files <= 0:
        blockers.append("No active Python files detected.")

    if route_total < min_routes:
        blockers.append(f"Route count below release minimum: {route_total} < {min_routes}")

    if blueprint_total < min_blueprints:
        blockers.append(f"Blueprint count below release minimum: {blueprint_total} < {min_blueprints}")

    if model_total < min_models:
        blockers.append(f"Model/schema count below release minimum: {model_total} < {min_models}")

    if strict and strict_warning_findings:
        blockers.extend(f"Strict mode warning blocker: {finding_label(item)}" for item in strict_warning_findings)

    if require_clean_tree and data.get("git", {}).get("status_short"):
        blockers.append("Working tree is not clean. Commit or stash changes before release.")

    if require_live_stack:
        for item in findings:
            if item.get("title") in live_stack_blocker_titles:
                blockers.append(f"Live-stack blocker: {finding_label(item)}")

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": not blockers,
        "branch": data.get("git", {}).get("branch"),
        "commit": data.get("git", {}).get("commit"),
        "severity_counts": dict(severity_counts),
        "routes": route_total,
        "blueprints": blueprint_total,
        "models": model_total,
        "active_python_files": active_python_files,
        "strict": strict,
        "require_clean_tree": require_clean_tree,
        "require_live_stack": require_live_stack,
        "blockers": blockers,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if blockers:
        return fail(
            "Release gate found blocking issues.",
            blockers,
        )

    print()
    print("✅ FutureFunded release gate passed")
    print("=" * 42)
    print(f"Branch:              {summary['branch']}")
    print(f"Commit:              {summary['commit']}")
    print(f"Active Python files: {active_python_files}")
    print(f"Routes:              {route_total}")
    print(f"Blueprints:          {blueprint_total}")
    print(f"Models/schemas:      {model_total}")
    print(f"Findings:            {dict(severity_counts)}")
    print(f"Summary:             {OUT_JSON}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
