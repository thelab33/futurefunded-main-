#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
OUT = ROOT / "docs/release-proof/money-flow-script-inventory-latest.json"

SCRIPT_ROOTS = [
    ROOT / "scripts",
]

BUCKETS = {
    "money_flow_checkout": [
        "stripe", "paypal", "checkout", "payment", "donation", "donate",
        "session", "capture", "provider", "money loop", "amount"
    ],
    "sponsor_flow": [
        "sponsor", "package", "recognition", "lead", "queue", "publishing"
    ],
    "share_qr_conversion": [
        "share", "qr", "copy link", "clipboard", "referral", "attribution"
    ],
    "ledger_operator": [
        "ledger", "dashboard", "operator", "records", "export", "payout"
    ],
    "email_notifications": [
        "email", "postmark", "smtp", "notification", "receipt"
    ],
    "visual_surface": [
        "visual", "screenshot", "overflow", "surface", "homepage", "campaign"
    ],
    "release_gate": [
        "enterprise", "release", "gate", "readiness", "prod", "live"
    ],
    "legacy_or_backup": [
        ".bak", "__pycache__", "archive", "cinematic", "deprecated"
    ],
}

IMPORTANT_HINTS = [
    "ff_campaign_v1_authority_money_loop",
    "ff_real_stripe_money_loop_hybrid",
    "verify-stripe-test-checkout",
    "verify-checkout-flow-stability",
    "verify-conversion-behavior",
    "verify-stripe-network",
    "ff_test_donation_readiness_gate",
    "ff_live_donation_readiness_gate",
    "ff_payment_mode_audit",
    "ff_wave5c_stripe_checkout_smoke",
    "ff_wave5d_paid_checkout_verify",
    "ff_checkout_continue_ux_audit",
    "qa_payment_contracts",
    "verify-campaign-payments",
    "verify-campaign-modals",
    "campaign-payment-smoke",
    "ff_campaign_conversion_contract_audit",
    "ff-postmark-smtp-smoke",
    "payment_notification_drill",
]


def safe_read(path: Path, limit: int = 80_000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"READ_ERROR: {exc}"
    return data[:limit]


def score_script(path: Path, text: str) -> dict:
    rel = str(path.relative_to(ROOT))
    haystack = f"{rel}\n{text[:12000]}".lower()

    buckets = {}
    for bucket, terms in BUCKETS.items():
        hits = sorted({term for term in terms if term.lower() in haystack})
        if hits:
            buckets[bucket] = hits

    priority = 0
    for hint in IMPORTANT_HINTS:
        if hint.lower() in rel.lower():
            priority += 5

    if "money_flow_checkout" in buckets:
        priority += 4
    if "release_gate" in buckets:
        priority += 2
    if "legacy_or_backup" in buckets:
        priority -= 5
    if path.suffix in {".mjs", ".js", ".py", ".sh"}:
        priority += 1

    commands = []
    if path.suffix == ".mjs":
        commands.append(f"node {rel}")
    elif path.suffix == ".py":
        commands.append(f"python {rel}")
    elif path.suffix == ".sh":
        commands.append(f"bash {rel}")

    return {
        "path": rel,
        "suffix": path.suffix,
        "priority": priority,
        "buckets": buckets,
        "suggestedCommands": commands,
        "firstLines": "\n".join(text.splitlines()[:8]),
    }


def main() -> None:
    scripts = []
    for root in SCRIPT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".mjs", ".js", ".py", ".sh"}:
                continue
            if "__pycache__" in path.parts:
                continue

            text = safe_read(path)
            item = score_script(path, text)
            if item["buckets"]:
                scripts.append(item)

    scripts.sort(key=lambda x: (x["priority"], x["path"]), reverse=True)

    by_bucket = {}
    for item in scripts:
        for bucket in item["buckets"]:
            by_bucket.setdefault(bucket, []).append(item["path"])

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(scripts),
        "byBucket": by_bucket,
        "topMoneyFlowCandidates": [
            item for item in scripts
            if "money_flow_checkout" in item["buckets"]
        ][:30],
        "topSponsorCandidates": [
            item for item in scripts
            if "sponsor_flow" in item["buckets"]
        ][:30],
        "topEmailCandidates": [
            item for item in scripts
            if "email_notifications" in item["buckets"]
        ][:20],
        "allMatches": scripts,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote {OUT}")
    print()
    print("=== TOP MONEY-FLOW / CHECKOUT CANDIDATES ===")
    for item in report["topMoneyFlowCandidates"][:25]:
        print(f"{item['priority']:>3}  {item['path']}")
        if item["suggestedCommands"]:
            print(f"     run: {item['suggestedCommands'][0]}")
    print()
    print("=== TOP SPONSOR CANDIDATES ===")
    for item in report["topSponsorCandidates"][:20]:
        print(f"{item['priority']:>3}  {item['path']}")
    print()
    print("=== TOP EMAIL / NOTIFICATION CANDIDATES ===")
    for item in report["topEmailCandidates"][:15]:
        print(f"{item['priority']:>3}  {item['path']}")


if __name__ == "__main__":
    main()
