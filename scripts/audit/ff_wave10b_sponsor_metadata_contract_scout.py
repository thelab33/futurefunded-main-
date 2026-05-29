#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "audit_outputs"
OUT.mkdir(exist_ok=True)

FILES = {
    "campaign_routes": ROOT / "apps/web/app/blueprints/campaign/routes.py",
    "campaign_js": ROOT / "apps/web/app/static/js/ff-campaign.js",
    "lifecycle_messages": ROOT / "apps/web/app/services/ff_lifecycle_messages.py",
    "lifecycle_dispatch": ROOT / "apps/web/app/services/ff_lifecycle_dispatch.py",
    "transactional_email": ROOT / "apps/web/app/services/ff_transactional_email.py",
    "dashboard_locked": ROOT / "apps/web/app/templates/platform/dashboard_locked.html",
    "campaign_premium": ROOT / "apps/web/app/templates/campaign_premium.html",
}

PATTERNS = {
    "checkout_session_route": r"checkout/session|/checkout/session|def .*checkout|stripe\.checkout\.Session",
    "request_json": r"request\.get_json|request\.json",
    "stripe_session_create": r"stripe\.checkout\.Session\.create|checkout\.Session\.create",
    "metadata_usage": r"\bmetadata\s*=|metadata\[|\.metadata|metadata\.get",
    "session_status": r"session-status|session_status|retrieve\(.*session",
    "ledger_function": r"ledger|_ff_checkout_session_to_ledger|payment_ledger",
    "sponsor_lifecycle": r"sponsor_confirmation|operator_sponsor_alert|dispatch_sponsor",
    "email_subject": r"subject|operator_sponsor_alert|Sponsor confirmation",
    "sponsor_form_frontend": r"data-ff-sponsor-sales-flow|data-ff-sponsor-package-select|data-ff-sponsor-continue",
    "fetch_checkout": r"fetch\(|checkout/session|createCheckout|openSponsor|data-ff-open-sponsor",
}

def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")

def line_no(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1

def snippets(path: Path, pattern: str, radius: int = 3) -> list[dict]:
    text = read(path)
    if not text:
        return []
    lines = text.splitlines()
    out = []
    for m in re.finditer(pattern, text, re.I):
        ln = line_no(text, m.start())
        start = max(1, ln - radius)
        end = min(len(lines), ln + radius)
        out.append({
            "line": ln,
            "match": m.group(0)[:160],
            "context": "\n".join(f"{i:04d}: {lines[i-1]}" for i in range(start, end + 1)),
        })
    return out[:12]

def main() -> int:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files": {k: str(v) for k, v in FILES.items()},
        "findings": {},
        "recommendation": [],
    }

    for key, path in FILES.items():
        report["findings"][key] = {}
        for pname, pattern in PATTERNS.items():
            hits = snippets(path, pattern)
            if hits:
                report["findings"][key][pname] = hits

    # Simple inferred readiness.
    routes = report["findings"].get("campaign_routes", {})
    js = report["findings"].get("campaign_js", {})
    messages = report["findings"].get("lifecycle_messages", {})

    report["recommendation"] = [
        "Patch frontend sponsor intake fields into checkout/session request payload.",
        "Patch campaign checkout route to accept sponsor_intake fields and store them as Stripe metadata.",
        "Patch session-status/ledger extraction to preserve sponsor metadata.",
        "Patch sponsor lifecycle/operator email copy to include business name, recognition name, package, website, and note.",
        "Add a dashboard/review panel that shows pending sponsor recognition from latest sponsor metadata."
    ]

    checks = {
        "has_checkout_route": bool(routes.get("checkout_session_route")),
        "has_request_json": bool(routes.get("request_json")),
        "has_stripe_session_create": bool(routes.get("stripe_session_create")),
        "has_metadata_usage": bool(routes.get("metadata_usage")),
        "has_ledger_function": bool(routes.get("ledger_function")),
        "has_frontend_sponsor_form": bool(js.get("sponsor_form_frontend")),
        "has_frontend_checkout_fetch": bool(js.get("fetch_checkout")),
        "has_sponsor_lifecycle": bool(messages.get("sponsor_lifecycle")),
    }

    report["checks"] = checks

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = OUT / f"ff_wave10b_sponsor_metadata_contract_scout_{stamp}.json"
    md_path = OUT / f"ff_wave10b_sponsor_metadata_contract_scout_{stamp}.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Wave 10B Sponsor Metadata Contract Scout")
    lines.append("")
    lines.append(f"- **Generated:** `{report['generated_at']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Result |")
    lines.append("| --- | --- |")
    for k, v in checks.items():
        lines.append(f"| `{k}` | {'✅' if v else '❌'} |")

    lines.append("")
    lines.append("## Key snippets")
    lines.append("")

    for file_key, file_findings in report["findings"].items():
        if not file_findings:
            continue
        lines.append(f"### {file_key}")
        lines.append("")
        for pattern_name, hits in file_findings.items():
            lines.append(f"#### {pattern_name}")
            lines.append("")
            for hit in hits[:4]:
                lines.append(f"- Line `{hit['line']}` match `{hit['match']}`")
                lines.append("```text")
                lines.append(hit["context"])
                lines.append("```")
            lines.append("")

    lines.append("## Recommended Wave 10B-B patch path")
    lines.append("")
    for item in report["recommendation"]:
        lines.append(f"- {item}")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"✅ Wave 10B sponsor metadata scout: {md_path}")
    print(f"JSON: {json_path}")
    print("")
    for k, v in checks.items():
        print(f"{'✅' if v else '❌'} {k}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
