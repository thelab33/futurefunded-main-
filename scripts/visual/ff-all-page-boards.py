#!/usr/bin/env python3
"""
Compatibility wrapper.

The old all-page board mixed canonical launch pages with aliases/support routes.
For product review, forward to the canonical launch surface board.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts/visual/ff-launch-surface-board.py"

raise SystemExit(
    subprocess.call([sys.executable, str(TARGET), *sys.argv[1:]], cwd=str(ROOT))
)
