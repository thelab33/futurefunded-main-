#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
OUT_MD = ROOT / "docs/release-proof/release-proof-docs-audit-latest.md"
OUT_JSON = ROOT / "docs/release-proof/release-proof-docs-audit-latest.json"

KEEP = {
    "active-repo-map-latest.json",
    "active-repo-map-latest.md",
    "repo-quarantine-plan-latest.json",
    "repo-quarantine-plan-latest.md",
    "secret-hygiene-latest.md",
    "futurefunded-production-closeout-v1.md",
}

def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as exc:
        return exc.output.strip()

def git_grep(pattern: str) -> list[str]:
    out = run([
        "git", "grep", "-n", pattern, "--", ".",
        ":!docs/release-proof/**",
        ":!repo-quarantine/**",
        ":!.git/**",
        ":!node_modules/**",
        ":!.venv/**",
    ])
    if not out:
        return []
    return [line for line in out.splitlines() if line.strip()]

tracked = run(["git", "ls-files", "docs/release-proof"]).splitlines()

rows = []
for file in tracked:
    path = ROOT / file
    name = path.name
    refs = git_grep(name)
    if name in KEEP:
        decision = "keep"
        reason = "current release/security/quarantine proof"
    elif refs:
        decision = "review"
        reason = "referenced outside docs/release-proof"
    else:
        decision = "quarantine-candidate"
        reason = "tracked proof snapshot with no active external references"

    rows.append({
        "file": file,
        "name": name,
        "size": path.stat().st_size if path.exists() else 0,
        "decision": decision,
        "reason": reason,
        "refs": refs[:20],
    })

OUT_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")

md = []
md.append("# FutureFunded Release Proof Docs Audit\n\n")
md.append("## Summary\n\n")
for decision in ["keep", "review", "quarantine-candidate"]:
    md.append(f"- `{decision}`: `{sum(1 for r in rows if r['decision'] == decision)}`\n")

md.append("\n## Files\n\n")
md.append("| Decision | Size | File | Reason |\n")
md.append("|---|---:|---|---|\n")
for row in rows:
    md.append(f"| `{row['decision']}` | `{row['size']}` | `{row['file']}` | {row['reason']} |\n")

md.append("\n## Referenced files needing review\n\n")
for row in rows:
    if row["refs"]:
        md.append(f"\n### `{row['file']}`\n\n")
        for ref in row["refs"]:
            md.append(f"- `{ref}`\n")

OUT_MD.write_text("".join(md), encoding="utf-8")

print(f"Wrote {OUT_JSON}")
print(f"Wrote {OUT_MD}")
print(json.dumps({
    "keep": sum(1 for r in rows if r["decision"] == "keep"),
    "review": sum(1 for r in rows if r["decision"] == "review"),
    "quarantine_candidate": sum(1 for r in rows if r["decision"] == "quarantine-candidate"),
}, indent=2))
