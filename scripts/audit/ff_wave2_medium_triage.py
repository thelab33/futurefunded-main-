#!/usr/bin/env python3
"""
FutureFunded • Wave 2 Medium Triage

Reads the latest ff_launch_contract_audit_*.json and creates a grouped,
founder-friendly Wave 2 action plan.

Read-only.
"""

from __future__ import annotations

import json
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime


ROOT = Path(".").resolve()
AUDIT_DIR = ROOT / "audit_outputs"


def latest_json() -> Path:
    files = sorted(AUDIT_DIR.glob("ff_launch_contract_audit_*.json"))
    if not files:
        raise SystemExit("No audit JSON files found in audit_outputs/. Run ff_launch_contract_audit.py first.")
    return files[-1]


def classify(issue: dict) -> str:
    area = issue.get("area", "").lower()
    loc = issue.get("location", "").lower()
    msg = issue.get("message", "").lower()

    if "lifecycle" in area or "email" in loc or "receipt" in msg or "outbox" in msg:
        return "Wave 2A — Lifecycle messaging"
    if "cta hierarchy" in area:
        return "Wave 2B — Campaign CTA hierarchy"
    if "css authority" in area or loc.endswith(".css") or "/static/css/" in loc:
        return "Wave 2C — CSS authority cleanup"
    if "js selector" in area or loc.endswith(".js") or "/static/js/" in loc:
        return "Wave 2D — JS contract verification"
    if "stale" in area or "placeholder" in msg or "stub" in msg or "rescue" in msg or "fake" in msg:
        if "deprecated" in loc or "/scripts/" in loc or loc.startswith("scripts/"):
            return "Wave 2E — Quarantine/audit noise"
        return "Wave 2F — Public source cleanup"
    return "Wave 2Z — Manual review"


def severity_rank(sev: str) -> int:
    return {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(sev, 9)


def main() -> int:
    src = latest_json()
    data = json.loads(src.read_text())

    issues = data.get("issues", [])
    grouped = defaultdict(list)

    for issue in issues:
        if issue.get("severity") not in {"MEDIUM", "LOW"}:
            continue
        grouped[classify(issue)].append(issue)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = AUDIT_DIR / f"ff_wave2_medium_triage_{stamp}.md"

    lines = []
    lines.append("# FutureFunded Wave 2 Medium Triage")
    lines.append("")
    lines.append(f"- **Source audit:** `{src.name}`")
    lines.append(f"- **Generated:** `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append("")
    lines.append("## Executive Priority")
    lines.append("")
    lines.append("1. **Lifecycle messaging** — donor receipt, sponsor confirmation, operator notification.")
    lines.append("2. **Campaign CTA hierarchy** — reduce duplicate Donate/Share noise.")
    lines.append("3. **Public source cleanup** — remove launch-risk placeholder/stub/rescue wording from public templates/assets.")
    lines.append("4. **CSS authority cleanup** — confirm what CSS is canonical before final design polish.")
    lines.append("5. **JS selector verification** — confirm any stale selectors are non-breaking.")
    lines.append("")

    counts = Counter(classify(i) for i in issues if i.get("severity") in {"MEDIUM", "LOW"})
    lines.append("## Group Counts")
    lines.append("")
    lines.append("| Group | Count |")
    lines.append("| --- | ---: |")
    for group, count in counts.most_common():
        lines.append(f"| {group} | {count} |")
    lines.append("")

    for group in sorted(grouped):
        rows = sorted(grouped[group], key=lambda x: (severity_rank(x.get("severity", "")), x.get("location", ""), x.get("line") or 0))
        lines.append(f"## {group}")
        lines.append("")
        lines.append("| # | Severity | Area | Location | Line | Finding | Recommendation |")
        lines.append("| ---: | --- | --- | --- | ---: | --- | --- |")

        for idx, issue in enumerate(rows, start=1):
            loc = str(issue.get("location", "")).replace("|", "\\|")
            msg = str(issue.get("message", "")).replace("|", "\\|")
            rec = str(issue.get("recommendation", "")).replace("|", "\\|")
            lines.append(
                f"| {idx} | {issue.get('severity','')} | {issue.get('area','')} | `{loc}` | "
                f"{issue.get('line') or ''} | {msg} | {rec} |"
            )
        lines.append("")

    lines.append("## Recommended Build Order")
    lines.append("")
    lines.append("### Patch 1 — Lifecycle messaging contract")
    lines.append("- Confirm production email provider behavior.")
    lines.append("- Add branded donor thank-you copy.")
    lines.append("- Add branded sponsor confirmation copy.")
    lines.append("- Add operator notification copy.")
    lines.append("")
    lines.append("### Patch 2 — Campaign CTA hierarchy")
    lines.append("- Keep one primary Donate action per visual zone.")
    lines.append("- Turn repeated Share buttons into lower-weight utility actions.")
    lines.append("- Ensure Sponsor path is clear but not noisy.")
    lines.append("")
    lines.append("### Patch 3 — Public placeholder cleanup")
    lines.append("- Replace public-facing placeholder/stub/rescue language.")
    lines.append("- Leave technical comments only where they are not user-visible and still useful.")
    lines.append("")
    lines.append("### Patch 4 — CSS authority plan")
    lines.append("- Decide whether `ff.css` remains the single authority.")
    lines.append("- Keep `ff.checkout.css` only for checkout-specific layout.")
    lines.append("- Either merge or intentionally scope `platform-home.css`.")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 2 triage written: {out}")
    print("")
    print("Top groups:")
    for group, count in counts.most_common():
        print(f"  {count:>3}  {group}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
