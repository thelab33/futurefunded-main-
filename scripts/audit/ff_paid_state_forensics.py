from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / "audit_outputs" / "paid-state-forensics"
OUT.mkdir(parents=True, exist_ok=True)

SECRET_PATTERNS = [
    (re.compile(r"sk_(test|live)_[A-Za-z0-9_]+"), r"sk_\1_…MASKED"),
    (re.compile(r"pk_(test|live)_[A-Za-z0-9_]+"), r"pk_\1_…MASKED"),
    (re.compile(r"whsec_[A-Za-z0-9_]+"), "whsec_…MASKED"),
    (re.compile(r"cs_(test|live)_[A-Za-z0-9]+"), r"cs_\1_…MASKED"),
]

def scrub(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

def latest(pattern: str) -> Path | None:
    files = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def flatten(obj, prefix="$"):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            rows.extend(flatten(v, f"{prefix}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            rows.extend(flatten(v, f"{prefix}[{i}]"))
    else:
        rows.append((prefix, obj))
    return rows

def scan_text(name: str, text: str) -> dict:
    low = text.lower()
    return {
        "source": name,
        "has_checkout_completed": "checkout.session.completed" in low,
        "has_checkout_expired": "checkout.session.expired" in low,
        "has_paid": bool(re.search(r"\bpaid\b|payment_status.*paid|state.*paid|verified", low)),
        "has_unpaid": "unpaid" in low,
        "has_donor_receipt": "donor_receipt" in low,
        "has_operator_alert": "operator_donation_alert" in low or "operator_donation" in low,
        "has_ledger": "ledger" in low,
        "has_webhook": "webhook" in low,
        "has_checkout_session": "cs_test_" in text or "cs_live_" in text,
    }

reports = []

wave5c_json = latest("audit_outputs/ff_wave5c_stripe_checkout_smoke_*.json")
wave5c_md = latest("audit_outputs/ff_wave5c_stripe_checkout_smoke_*.md")
release_log = latest("audit_outputs/release-gate/*-release-gate.log")
test_gate_log = latest("audit_outputs/test-donation-readiness/*-test-donation-readiness.log")

sources = []

for path in [wave5c_json, wave5c_md, release_log, test_gate_log]:
    if path and path.exists():
        text = path.read_text(encoding="utf-8", errors="replace")
        sources.append((str(path.relative_to(ROOT)), text))
        reports.append(scan_text(str(path.relative_to(ROOT)), text))

spool = ROOT / "instance" / "email-spool"
donor_receipts = sorted(spool.glob("*donor_receipt.json")) if spool.exists() else []
operator_alerts = sorted(spool.glob("*operator_donation_alert.json")) if spool.exists() else []

spool_evidence = {
    "donor_receipt_count": len(donor_receipts),
    "operator_alert_count": len(operator_alerts),
    "latest_donor_receipt": str(donor_receipts[-1].relative_to(ROOT)) if donor_receipts else None,
    "latest_operator_alert": str(operator_alerts[-1].relative_to(ROOT)) if operator_alerts else None,
}

has_completed = any(r["has_checkout_completed"] for r in reports)
has_paid = any(r["has_paid"] for r in reports)
has_receipt = any(r["has_donor_receipt"] for r in reports) or spool_evidence["donor_receipt_count"] > 0
has_operator_alert = any(r["has_operator_alert"] for r in reports) or spool_evidence["operator_alert_count"] > 0
has_ledger = any(r["has_ledger"] for r in reports)
has_unpaid = any(r["has_unpaid"] for r in reports)

if has_completed and has_paid and has_receipt and has_operator_alert and has_ledger:
    verdict = "FULL_PAID_STATE_PROOF_FOUND"
elif has_receipt and has_operator_alert and has_ledger:
    verdict = "LIFECYCLE_EVIDENCE_FOUND_BUT_COMPLETED_PAYMENT_NOT_CONFIRMED"
elif has_unpaid:
    verdict = "CHECKOUT_CREATION_PROVEN_BUT_LATEST_SESSION_UNPAID"
else:
    verdict = "INSUFFICIENT_PAID_STATE_EVIDENCE"

payload = {
    "generated": datetime.utcnow().isoformat() + "Z",
    "verdict": verdict,
    "latest_files": {
        "wave5c_json": str(wave5c_json.relative_to(ROOT)) if wave5c_json else None,
        "wave5c_md": str(wave5c_md.relative_to(ROOT)) if wave5c_md else None,
        "release_log": str(release_log.relative_to(ROOT)) if release_log else None,
        "test_gate_log": str(test_gate_log.relative_to(ROOT)) if test_gate_log else None,
    },
    "report_scans": reports,
    "spool_evidence": spool_evidence,
}

stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
json_path = OUT / f"{stamp}-paid-state-forensics.json"
md_path = OUT / f"{stamp}-paid-state-forensics.md"

json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

md = [
    "# FutureFunded Paid-State Forensics",
    "",
    f"Generated: `{payload['generated']}`",
    f"Verdict: **{verdict}**",
    "",
    "## Latest files",
]
for k, v in payload["latest_files"].items():
    md.append(f"- `{k}`: `{v}`")

md += [
    "",
    "## Spool evidence",
    f"- Donor receipts: `{spool_evidence['donor_receipt_count']}`",
    f"- Operator alerts: `{spool_evidence['operator_alert_count']}`",
    f"- Latest donor receipt: `{spool_evidence['latest_donor_receipt']}`",
    f"- Latest operator alert: `{spool_evidence['latest_operator_alert']}`",
    "",
    "## Report scans",
]

for r in reports:
    md.append("")
    md.append(f"### `{r['source']}`")
    for k, v in r.items():
        if k != "source":
            md.append(f"- `{k}`: `{v}`")

md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

print(f"Verdict: {verdict}")
print(f"Report: {md_path}")
print(f"JSON:   {json_path}")

if verdict == "FULL_PAID_STATE_PROOF_FOUND":
    raise SystemExit(0)

if verdict == "LIFECYCLE_EVIDENCE_FOUND_BUT_COMPLETED_PAYMENT_NOT_CONFIRMED":
    raise SystemExit(2)

if verdict == "CHECKOUT_CREATION_PROVEN_BUT_LATEST_SESSION_UNPAID":
    raise SystemExit(3)

raise SystemExit(4)
