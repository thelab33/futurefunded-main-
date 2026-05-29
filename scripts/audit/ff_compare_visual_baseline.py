from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path.cwd()

BASELINE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "audit_outputs/visual-baselines/stable-before-css-consolidation-v1-20260519"
CURRENT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "audit_outputs/visual-board/latest"

PNG_NAMES = [
    "platform-desktop.png",
    "platform-mobile.png",
    "campaign-desktop.png",
    "campaign-mobile.png",
    "onboarding-desktop.png",
    "onboarding-mobile.png",
    "login-desktop.png",
    "login-mobile.png",
    "dashboard-locked-desktop.png",
    "dashboard-locked-mobile.png",
    "dashboard-private-desktop.png",
    "dashboard-private-mobile.png",
]

# Conservative thresholds. We are not blocking tiny rendering noise.
MAX_DIMENSION_DELTA = 8
MAX_RMS = 18.0

def rms_diff(a: Image.Image, b: Image.Image) -> float:
    a = a.convert("RGB")
    b = b.convert("RGB")

    if a.size != b.size:
        w = min(a.width, b.width)
        h = min(a.height, b.height)
        a = a.crop((0, 0, w, h))
        b = b.crop((0, 0, w, h))

    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    sq = sum((value ** 2 for value in stat.rms)) / len(stat.rms)
    return math.sqrt(sq)

def main() -> None:
    results = []

    for name in PNG_NAMES:
        before = BASELINE / name
        after = CURRENT / name

        if not before.exists() or not after.exists():
            results.append({
                "file": name,
                "ok": False,
                "reason": "missing",
                "baseline_exists": before.exists(),
                "current_exists": after.exists(),
            })
            continue

        with Image.open(before) as img_a, Image.open(after) as img_b:
            width_delta = abs(img_a.width - img_b.width)
            height_delta = abs(img_a.height - img_b.height)
            rms = rms_diff(img_a, img_b)

        ok = width_delta <= MAX_DIMENSION_DELTA and height_delta <= MAX_DIMENSION_DELTA and rms <= MAX_RMS

        results.append({
            "file": name,
            "ok": ok,
            "width_delta": width_delta,
            "height_delta": height_delta,
            "rms": round(rms, 3),
        })

    passed = sum(1 for row in results if row["ok"])
    total = len(results)

    print(f"Visual baseline comparison: {passed}/{total} passed")
    print(f"Baseline: {BASELINE}")
    print(f"Current:  {CURRENT}")
    print("")

    for row in results:
        status = "PASS" if row["ok"] else "CHECK"
        print(f"{status} {row['file']} {json.dumps(row, sort_keys=True)}")

    if passed != total:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
