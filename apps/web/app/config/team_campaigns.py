"""
FutureFunded team campaign configs.

Contract:
- Image paths are Flask static filenames, not filesystem paths.
- Keep values relative to app.static_folder, e.g. "images/program-proof/6th-grade.jpg".
- The campaign template resolves them with url_for('static', filename=...).
- Existing/current image path support is preserved first; canonical production paths are noted below.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


CURRENT_PROOF_BASE = "images/program-proof"
CANONICAL_CAMPAIGN_BASE = "images/campaigns/connect-atx-elite"

CONNECT_ATX_ELITE: Dict[str, Any] = {
    "theme": "dark",
    "team_name": "Connect ATX Elite",
    "campaign_title": "Fuel the season. Fund the future.",
    "campaign_slug": "connect-atx-elite",
    "campaign_url": "/c/connect-atx-elite",
    "page_title": "Connect ATX Elite — Fuel the season. Fund the future.",
    "page_description": (
        "Support Connect ATX Elite with a secure donation or sponsor package. "
        "Your gift helps cover travel, tournaments, meals, uniforms, and season costs."
    ),
    "raised": "$11,869",
    "goal": "$20,000",
    "remaining": "$8,131",
    "supporters": 135,
    "percent": "59%",
    "donation_amounts": [25, 50, 100, 250],
    "impact_chips": [
        {"amount": "$25", "label": "Meal or hydration support"},
        {"amount": "$75", "label": "Practice day support"},
        {"amount": "$150", "label": "Travel support"},
        {"amount": "$250", "label": "Tournament fees"},
    ],
    # These point at the image paths your current template already expects.
    # Once the files exist in the canonical folder, change these to:
    # f"{CANONICAL_CAMPAIGN_BASE}/squad/6th-grade-gold.webp", etc.
    "squad_cards": [
        {
            "title": "6th Grade Gold",
            "note": "Travel + tournament support",
            "image": f"{CURRENT_PROOF_BASE}/6th-grade.jpg",
        },
        {
            "title": "6th Grade Gold",
            "note": "Meals + hydration",
            "image": f"{CURRENT_PROOF_BASE}/6th-grade.jpg",
        },
        {
            "title": "7th Grade Black",
            "note": "Entry fees + gear",
            "image": f"{CURRENT_PROOF_BASE}/7th-grade.jpg",
        },
        {
            "title": "8th Grade Gold",
            "note": "Hotels + team meals",
            "image": f"{CURRENT_PROOF_BASE}/8th-grade.jpg",
        },
        {
            "title": "Connect ATX Elite",
            "note": "Season essentials",
            "image": f"{CURRENT_PROOF_BASE}/7th-grade.jpg",
        },
        {
            "title": "7th Grade Gold",
            "note": "Player development",
            "image": f"{CURRENT_PROOF_BASE}/7th-grade.jpg",
        },
    ],
    "team_cards": [
        {
            "eyebrow": "6th Grade Gold",
            "title": "Elite kids. Big standards. Community.",
            "cta": "Support 6th Grade Gold",
            "image": f"{CURRENT_PROOF_BASE}/6th-grade.jpg",
        },
        {
            "eyebrow": "7th Grade Gold",
            "title": "School, travel, gym, growth.",
            "cta": "Support 7th Grade Gold",
            "image": f"{CURRENT_PROOF_BASE}/7th-grade.jpg",
        },
    ],
    "sponsor_tiers": [
        {
            "eyebrow": "Community",
            "title": "Community",
            "price": "$100+",
            "copy": "Thank-you recognition for families and local supporters.",
            "benefits": ["Thank-you note", "Name listed on page"],
        },
        {
            "eyebrow": "Recommended",
            "title": "Partner",
            "price": "$250+",
            "copy": "Logo and sponsor wall recognition.",
            "benefits": ["Logo on sponsor wall", "Sponsor thank-you"],
            "featured": True,
        },
        {
            "eyebrow": "Premium",
            "title": "Champion",
            "price": "$500+",
            "copy": "Featured placement and sponsor spotlight.",
            "benefits": ["Large logo placement", "Featured mention"],
        },
        {
            "eyebrow": "VIP",
            "title": "VIP",
            "price": "$1,000+",
            "copy": "Top sponsor recognition with VIP placement.",
            "benefits": ["VIP sponsor section", "Custom thank-you post"],
        },
    ],
}

TEAM_CAMPAIGN_CONFIGS: Dict[str, Dict[str, Any]] = {
    "connect-atx-elite": CONNECT_ATX_ELITE,
    "connect_atx_elite": CONNECT_ATX_ELITE,
}


def get_team_campaign_context(slug: str = "connect-atx-elite") -> Dict[str, Any]:
    """Return a template-safe copy of the campaign context for a team slug."""
    key = (slug or "connect-atx-elite").strip().lower().replace("_", "-")
    config = TEAM_CAMPAIGN_CONFIGS.get(key, CONNECT_ATX_ELITE)
    context = deepcopy(config)
    context["team_config"] = deepcopy(config)
    return context
