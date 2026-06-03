#!/usr/bin/env python3
"""
FutureFunded served URL audit helper.

This Python entrypoint intentionally delegates to the stable shell audit:
  scripts/audit/ff-served-url-lite.sh

Reason:
- Keeps the committed helper executable.
- Keeps Python syntax/compile checks green.
- Avoids duplicating audit logic while the shell version is the source of truth.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    audit_script = repo_root / "scripts" / "audit" / "ff-served-url-lite.sh"

    if not audit_script.exists():
        print(f"❌ Missing audit script: {audit_script}", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["bash", str(audit_script)],
        cwd=str(repo_root),
        check=False,
    )
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
