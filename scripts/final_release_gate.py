#!/usr/bin/env python3
"""
FutureFunded Release Gate v1

Single command for launch-surface validation.

Runs the current trusted audit stack:
- deprecated template quarantine
- active white-label boundary
- provider readiness v2
- provider readiness legacy compatibility
- minimal FAQ
- momentum visual console
- sponsor package behavior
- campaign profile
- platform smoke
- functional funnel

Warnings inside individual audits are allowed when those audits exit 0.
Any non-zero audit exits the release gate with failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AUDITS = [
    ("White-label identity boundaries", "scripts/final_white_label_identity_boundaries_audit.py"),
    ("Provider readiness v2", "scripts/final_provider_readiness_v2_audit.py"),
    ("Provider readiness compatibility", "scripts/final_provider_readiness_polish_audit.py"),
    ("Minimal FAQ", "scripts/final_faq_minimal_audit.py"),
    ("Campaign momentum visual console", "scripts/final_campaign_momentum_visual_audit.py"),
    ("Sponsor package behavior", "scripts/final_sponsor_package_behavior_audit.py"),
    ("Campaign profile", "scripts/final_campaign_profile_audit.py"),
    ("Platform smoke", "scripts/final_platform_smoke.py"),
    ("Functional funnel", "scripts/final_funnel_functional_audit.py"),
]


def ensure_operator_token(env: dict[str, str]) -> None:
    if env.get("FF_OPERATOR_ACCESS_TOKEN", "").strip():
        return

    token_file = Path("/tmp/ff_operator_token")
    if token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            env["FF_OPERATOR_ACCESS_TOKEN"] = token


def run_audit(label: str, script: str, env: dict[str, str]) -> tuple[bool, float]:
    path = ROOT / script

    print("\n" + "=" * 88)
    print(f"FutureFunded release gate: {label}")
    print("=" * 88)

    if not path.exists():
        print(f"❌ Missing audit script: {script}")
        return False, 0.0

    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=env,
        text=True,
    )
    elapsed = time.perf_counter() - started

    if result.returncode == 0:
        print(f"\n✅ {label} passed in {elapsed:.1f}s")
        return True, elapsed

    print(f"\n❌ {label} failed in {elapsed:.1f}s with exit code {result.returncode}")
    return False, elapsed


def main() -> int:
    print("\nFutureFunded Release Gate v1")
    print("=" * 88)

    env = os.environ.copy()
    ensure_operator_token(env)

    passed: list[tuple[str, float]] = []
    failed: list[tuple[str, float]] = []

    for label, script in AUDITS:
        ok, elapsed = run_audit(label, script, env)
        if ok:
            passed.append((label, elapsed))
        else:
            failed.append((label, elapsed))

    print("\n" + "=" * 88)
    print("FutureFunded Release Gate Summary")
    print("=" * 88)

    for label, elapsed in passed:
        print(f"✅ {label:<42} {elapsed:>6.1f}s")

    for label, elapsed in failed:
        print(f"❌ {label:<42} {elapsed:>6.1f}s")

    print("-" * 88)
    print(f"PASS: {len(passed)}  FAIL: {len(failed)}")

    if failed:
        print("\n❌ RELEASE GATE FAILED")
        return 1

    print("\n✅ RELEASE GATE PASSED")
    print("FutureFunded active launch surfaces are clean. Remaining env warnings are non-blocking unless an audit exits non-zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
