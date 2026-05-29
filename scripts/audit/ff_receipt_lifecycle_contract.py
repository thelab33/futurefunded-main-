from __future__ import annotations

import json
import sys
from pathlib import Path

spool = Path("instance/email-spool")

if not spool.exists():
    print("FAIL: instance/email-spool does not exist.")
    sys.exit(1)

files = sorted(spool.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:40]

donor_receipts = []
sponsor_confirmations = []

for path in files:
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        data = {}

    subject = str(data.get("subject") or "").lower()
    name = path.name.lower()

    if "donor_receipt" in name or "thank you for supporting" in subject:
        donor_receipts.append(str(path))

    if "sponsor_confirmation" in name or "sponsor confirmation" in subject:
        sponsor_confirmations.append(str(path))

print("Recent donor receipts:")
for item in donor_receipts[:8]:
    print(f"- {item}")

print("\nRecent sponsor confirmations:")
for item in sponsor_confirmations[:8]:
    print(f"- {item}")

if not donor_receipts:
    print("\nFAIL: No donor receipt previews found in recent spool files.")
    sys.exit(1)

print("\nPASS: Donor receipt lifecycle previews exist.")
