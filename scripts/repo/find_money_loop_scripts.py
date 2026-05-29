#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import re

ROOT = Path.cwd()
OUT = ROOT / "docs/release-proof/money-loop-script-map.md"
OUT_JSON = ROOT / "docs/release-proof/money-loop-script-map.json"

KEYWORDS = [
    "stripe",
    "paypal",
    "checkout",
    "payment",
    "webhook",
    "ledger",
    "receipt",
    "donation",
    "paid",
    "lifecycle",
    "notification",
    "provider",
    "capture",
    "session",
    "invoice",
]

SAFE_EXTS = {".py", ".mjs", ".js", ".sh", ".md"}

matches = []

for root in [ROOT / "scripts", ROOT / "docs"]:
    if not root.exists():
        continue

    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in SAFE_EXTS:
            continue

        rel = p.relative_to(ROOT).as_posix()

        if "_quarantine" in rel:
            continue

        text = p.read_text(encoding="utf-8", errors="replace")
        haystack = (rel + "\n" + text[:12000]).lower()

        hits = sorted({kw for kw in KEYWORDS if kw in haystack})

        if hits:
            executable = p.suffix in {".py", ".mjs", ".js", ".sh"}
            matches.append({
                "path": rel,
                "ext": p.suffix,
                "executable_candidate": executable,
                "hits": hits,
            })

matches.sort(key=lambda x: (
    0 if "payment" in x["hits"] or "checkout" in x["hits"] or "stripe" in x["hits"] else 1,
    x["path"],
))

lines = [
    "# FutureFunded Money Loop Script Map",
    "",
    "Generated from filename/content scan.",
    "",
    "## High-priority candidates",
    "",
    "| Script | Signals |",
    "|---|---|",
]

for item in matches:
    if item["executable_candidate"]:
        lines.append(f"| `{item['path']}` | {', '.join(item['hits'])} |")

lines += [
    "",
    "## Non-executable/reference docs",
    "",
]

for item in matches:
    if not item["executable_candidate"]:
        lines.append(f"- `{item['path']}` — {', '.join(item['hits'])}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
OUT_JSON.write_text(json.dumps(matches, indent=2), encoding="utf-8")

print("Wrote:", OUT)
print("Wrote:", OUT_JSON)
print("Matches:", len(matches))

print()
print("Top candidates:")
for item in matches[:30]:
    print("-", item["path"], "::", ", ".join(item["hits"]))
