#!/usr/bin/env python3
"""
FutureFunded lifecycle message drill.

Default writes preview JSON files to instance/email-spool.
Use --send with FF_EMAIL_DRY_RUN=0 and SMTP env vars for live delivery.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.web.app.services.ff_lifecycle_messages import render_all_samples, sample_payload
from apps.web.app.services.ff_transactional_email import provider_status, send_lifecycle_email


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Attempt SMTP send when configured.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    args = parser.parse_args()

    messages = render_all_samples(sample_payload())
    status = provider_status()

    results = [
        send_lifecycle_email(message, dry_run=not args.send)
        for message in messages
    ]

    payload = {"provider": status, "results": results}

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("FutureFunded lifecycle message drill")
    print("===================================")
    print(f"SMTP ready: {status['smtp_ready']}")
    print(f"Dry run:    {not args.send}")
    print(f"Preview:    {status['preview_dir']}")
    print("")

    for result in results:
        print(f"- {result.get('category')}: {result.get('mode')} → {result.get('to')}")
        if result.get("path"):
            print(f"  {result['path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
