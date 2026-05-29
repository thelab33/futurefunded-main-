#!/usr/bin/env python3
"""
FutureFunded Signal Strip Audit Contract Fix

The UI was intentionally changed from:
- Campaign Momentum
- Live proof, without the noise.

To:
- Live campaign signal
- Momentum is building.

This patch updates older audits so they validate the new signal-strip contract.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

FILES = [
    ROOT / "scripts/final_campaign_momentum_premium_audit.py",
    ROOT / "scripts/final_campaign_momentum_os_audit.py",
    ROOT / "scripts/final_campaign_public_sponsor_leak_audit.py",
]

REPLACEMENTS = {
    '"Campaign Momentum"': '"Live campaign signal"',
    '"Live proof, without the noise."': '"Momentum is building."',
    "rendered campaign contains Campaign Momentum": "rendered campaign contains Live campaign signal",
    "rendered campaign contains Live proof, without the noise.": "rendered campaign contains Momentum is building.",
    "required public contract present: Campaign Momentum": "required public contract present: Live campaign signal",
    "required public contract missing: Campaign Momentum": "required public contract missing: Live campaign signal",
    "premium momentum missing: Campaign Momentum": "premium momentum missing: Live campaign signal",
    "premium momentum contains: Campaign Momentum": "premium momentum contains: Live campaign signal",
}


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-signal-contract-{stamp}")
    shutil.copy2(path, dst)
    print(f"Backup: {dst}")


def patch_file(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing: {path}")
        return

    text = path.read_text(encoding="utf-8", errors="ignore")
    original = text

    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)

    if text == original:
        print(f"No change: {path}")
        return

    backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path}")


def main() -> int:
    print("\nFutureFunded signal strip audit contract fix")
    print("=" * 72)

    for path in FILES:
        patch_file(path)

    print("\n✅ Audit contracts updated for signal strip.")
    print("\nNext run:")
    print("  python scripts/final_campaign_momentum_signal_strip_audit.py")
    print("  python scripts/final_campaign_momentum_premium_audit.py")
    print("  python scripts/final_campaign_momentum_os_audit.py")
    print("  python scripts/final_campaign_public_sponsor_leak_audit.py")
    print("  python scripts/final_sponsor_signal_strip_removed_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
