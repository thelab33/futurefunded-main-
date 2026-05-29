#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT = ROOT / "audit_outputs" / "css-specificity-map" / STAMP
LATEST = ROOT / "audit_outputs" / "css-specificity-map" / "latest"

FILES = [
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/campaign.css",
]

def nearest_selector(lines, idx):
    for i in range(idx, max(-1, idx - 30), -1):
        line = lines[i].strip()
        if "{" in line and not line.startswith("@"):
            return line.split("{", 1)[0].strip()
    return "(selector not found nearby)"

def main():
    findings = []
    grouped = defaultdict(int)

    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        for idx, line in enumerate(lines):
            if "!important" not in line:
                continue

            selector = nearest_selector(lines, idx)
            prop = line.strip().split(":", 1)[0].strip() if ":" in line else line.strip()

            findings.append({
                "file": rel,
                "line": idx + 1,
                "selector": selector,
                "property": prop,
                "text": line.strip(),
            })

            grouped[(rel, prop)] += 1

    OUT.mkdir(parents=True, exist_ok=True)

    top_props = [
        {"file": file, "property": prop, "count": count}
        for (file, prop), count in Counter(grouped).most_common(40)
    ]

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_important": len(findings),
        "top_properties": top_props,
        "findings": findings,
    }

    (OUT / "css-specificity-map.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = ["# FutureFunded CSS Specificity Map", ""]
    md.append(f"Generated: `{report['generated_at']}`")
    md.append(f"Total `!important`: **{len(findings)}**")
    md.append("")
    md.append("## Top pressure properties")
    md.append("")
    md.append("| File | Property | Count |")
    md.append("|---|---:|---:|")
    for row in top_props[:30]:
        md.append(f"| `{row['file']}` | `{row['property']}` | {row['count']} |")

    md.append("")
    md.append("## First 160 important declarations")
    md.append("")
    md.append("| File | Line | Property | Selector |")
    md.append("|---|---:|---|---|")
    for item in findings[:160]:
        selector = item["selector"].replace("|", "\\|")
        md.append(f"| `{item['file']}` | {item['line']} | `{item['property']}` | `{selector}` |")

    (OUT / "css-specificity-map.md").write_text("\n".join(md), encoding="utf-8")

    if LATEST.exists() or LATEST.is_symlink():
        if LATEST.is_dir() and not LATEST.is_symlink():
            import shutil
            shutil.rmtree(LATEST)
        else:
            LATEST.unlink()

    import shutil
    shutil.copytree(OUT, LATEST)

    print(f"CSS specificity map complete: {len(findings)} !important declaration(s)")
    print(f"Report: {LATEST / 'css-specificity-map.md'}")

if __name__ == "__main__":
    main()
