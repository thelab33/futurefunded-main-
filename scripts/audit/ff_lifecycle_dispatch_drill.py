#!/usr/bin/env python3
"""
FutureFunded lifecycle dispatch drill.

Tests the exact bridge functions that checkout/sponsor routes will call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.web.app.services.ff_lifecycle_dispatch import (
    dispatch_donation_lifecycle,
    dispatch_sponsor_lifecycle,
)


payload = {
    "public_base_url": "https://getfuturefunded.com",
    "campaign_slug": "connect-atx-elite",
    "campaign_name": "Spring Fundraiser",
    "team_name": "Connect ATX Elite",
    "supporter_name": "Jordan Supporter",
    "supporter_email": "supporter@example.com",
    "donor_email": "supporter@example.com",
    "sponsor_name": "Austin Community Partner",
    "business_name": "Austin Community Partner",
    "sponsor_email": "sponsor@example.com",
    "sponsor_tier": "Community Partner",
    "amount_cents": 5000,
    "operator_email": "arodgps@gmail.com",
    "reply_to": "arodgps@gmail.com",
}

result = {
    "donation": dispatch_donation_lifecycle(payload),
    "sponsor": dispatch_sponsor_lifecycle(payload),
}

print(json.dumps(result, indent=2))
