#!/usr/bin/env python3
"""
FutureFunded • Wave 2C Public Stale Marker Scout

Reads the latest launch audit JSON and separates:
- public-facing stale/demo/fake markers that should be fixed
- internal/tooling markers that can be ignored or quarantined later

Read-only.
"""

from __future__ import annotations

import json
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(".").resolve()
AUDIT_DIR = ROOT / "audit_outputs"
OUT_DIR = AUDIT_DIR


PUBLIC_HINTS = (
    "apps/web/app/templates/",
    "apps/web/app/static/js/",
    "apps/web/app/static/css/",
)

INTERNAL_HINTS = (
    "scripts/",
    "tests/",
    "docs/",
    "apps/api/",
)

HIGH_VALUE_PUBLIC = (
    "campaign_premium.html",
    "platform/index.html",
    "platform/onboarding.html",
    "platform/dashboard.html",
    "ff.css",
    "platform-home.css",
    "ff-campaign.js",
    "ff-embedded-checkout.js",
)


def latest_audit_json() -> Path:
    files = sorted(AUDIT_DIR.glob("ff_launch_contract_audit_*.json"))
    if not files:
        raise SystemExit("No launch audit JSON found. Run ff_launch_contract_audit.py first.")
    return files[-1]


def classify(issue: dict) -> str:
    loc = issue.get("location", "")
    msg = issue.get("message", "").lower()

    if not any(loc.startswith(prefix) for prefix in PUBLIC_HINTS):
        return "Internal/tooling marker"

    if any(name in loc for name in HIGH_VALUE_PUBLIC):
        if any(word in msg for word in ("placeholder", "fake", "stub", "not-wired", "coming-soon", "rescue", "emergency")):
            return "Public cleanup — priority"
        return "Public cleanup — review"

    if loc.startswith("apps/web/app/templates/"):
        return "Public template cleanup — review"

    if loc.startswith("apps/web/app/static/"):
        return "Public asset cleanup — review"

    return "Manual review"


def main() -> int:
    src = latest_audit_json()
    data = json.loads(src.read_text(encoding="utf-8"))

    issues = [
        i for i in data.get("issues", [])
        if i.get("area") == "Stale/demo/fake marker"
    ]

    grouped = defaultdict(list)
    for issue in issues:
        grouped[classify(issue)].append(issue)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_DIR / f"ff_wave2c_stale_public_scout_{stamp}.md"

    lines = []
    lines.append("# FutureFunded Wave 2C Public Stale Marker Scout")
    lines.append("")
    lines.append(f"- **Source audit:** `{src.name}`")
    lines.append(f"- **Generated:** `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"- **Total stale/demo/fake findings:** `{len(issues)}`")
    lines.append("")

    counts = Counter(classify(i) for i in issues)
    lines.append("## Group counts")
    lines.append("")
    lines.append("| Group | Count |")
    lines.append("| --- | ---: |")
    for group, count in counts.most_common():
        lines.append(f"| {group} | {count} |")
    lines.append("")

    lines.append("## Recommended order")
    lines.append("")
    lines.append("1. Fix public campaign/platform template markers first.")
    lines.append("2. Fix public JS/CSS markers that could leak into product semantics or version names.")
    lines.append("3. Leave internal scripts/tests/docs alone unless they affect audit noise.")
    lines.append("4. Do not delete useful engineering comments blindly; relabel or quarantine instead.")
    lines.append("")

    for group in sorted(grouped):
        lines.append(f"## {group}")
        lines.append("")
        lines.append("| # | Severity | Location | Line | Finding | Recommendation |")
        lines.append("| ---: | --- | --- | ---: | --- | --- |")

        for idx, issue in enumerate(grouped[group], start=1):
            loc = str(issue.get("location", "")).replace("|", "\\|")
            msg = str(issue.get("message", "")).replace("|", "\\|")
            rec = str(issue.get("recommendation", "")).replace("|", "\\|")
            line = issue.get("line") or ""
            sev = issue.get("severity", "")
            lines.append(f"| {idx} | {sev} | `{loc}` | {line} | {msg} | {rec} |")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 2C stale marker scout written: {out}")
    print("")
    for group, count in counts.most_common():
        print(f"{count:>3}  {group}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
