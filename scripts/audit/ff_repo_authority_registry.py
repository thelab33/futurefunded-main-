from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
INV = ROOT / "audit_outputs" / "repo-authority" / "repo_authority_inventory.json"
DOC = ROOT / "docs" / "repo-authority.md"
RELEASE = ROOT / "docs" / "release-map.md"

CANONICAL = {
    "Platform homepage": {
        "route": "/platform/",
        "purpose": "Primary SaaS sales surface for FutureFunded.",
        "templates": ["apps/web/app/templates/platform/index.html"],
        "css": ["apps/web/app/static/css/platform-home.css", "apps/web/app/static/css/ff.css"],
        "js": [],
        "audits": ["scripts/audit/ff_visual_surface_board.mjs"],
    },
    "Campaign demo": {
        "route": "/c/connect-atx-elite",
        "purpose": "Flagship public donor/sponsor campaign surface.",
        "templates": [
            "apps/web/app/templates/campaign/index.html",
            "apps/web/app/templates/campaign_premium.html",
        ],
        "css": ["apps/web/app/static/css/ff.css"],
        "js": ["apps/web/app/static/js/ff-campaign.js"],
        "audits": ["scripts/audit/ff_visual_surface_board.mjs"],
    },
    "Launch workspace / onboarding": {
        "route": "/platform/onboarding",
        "purpose": "Launch setup workflow for team/campaign operators.",
        "templates": ["apps/web/app/templates/platform/onboarding.html"],
        "css": ["apps/web/app/static/css/ff.css"],
        "js": ["apps/web/app/static/js/islands/onboarding.js"],
        "audits": ["scripts/audit/ff_visual_surface_board.mjs"],
    },
    "Operator login": {
        "route": "/platform/login",
        "purpose": "Protected operator sign-in handoff.",
        "templates": ["apps/web/app/templates/platform/login.html"],
        "css": [
            "apps/web/app/static/css/login.css",
            "apps/web/app/static/css/ff-login-calm.css",
        ],
        "js": ["apps/web/app/static/js/ff-login.js"],
        "audits": ["scripts/audit/ff_visual_surface_board.mjs"],
    },
    "Protected dashboard": {
        "route": "/platform/dashboard",
        "purpose": "Private operator command center.",
        "templates": [
            "apps/web/app/templates/platform/dashboard.html",
            "apps/web/app/templates/platform/dashboard_locked.html",
            "apps/web/app/templates/_partials/ff_dashboard_launch_assistant.html",
        ],
        "css": [
            "apps/web/app/static/css/dashboard-modern.css",
            "apps/web/app/static/css/ff-dashboard-final.css",
            "apps/web/app/static/css/ff-dashboard-protected-exec.css",
            "apps/web/app/static/css/ff-fortune500-final.css",
            "apps/web/app/static/css/ff-launch-completion.css",
        ],
        "js": [
            "apps/web/app/static/js/ff-dashboard-protected-exec.js",
            "apps/web/app/static/js/ff-launch-completion.js",
        ],
        "audits": [
            "scripts/audit/ff_dashboard_protected_exec_audit.mjs",
            "scripts/audit/ff_dashboard_final_polish_audit.mjs",
            "scripts/audit/ff_visual_surface_board.mjs",
        ],
    },
    "Shared shell/components": {
        "route": "shared",
        "purpose": "Shared layout and reusable UI fragments.",
        "templates": [
            "apps/web/app/templates/_base/site_base.html",
            "apps/web/app/templates/_partials/ff_site_header.html",
            "apps/web/app/templates/shared/_button.html",
            "apps/web/app/templates/shared/_faq_item.html",
            "apps/web/app/templates/shared/_pill.html",
            "apps/web/app/templates/shared/_section_intro.html",
            "apps/web/app/templates/shared/_stat_card.html",
        ],
        "css": ["apps/web/app/static/css/ff.css"],
        "js": ["apps/web/app/static/js/csp-safe-init.js"],
        "audits": [],
    },
}

NO_TOUCH = [
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/platform-home.css",
    "apps/web/app/static/css/dashboard-modern.css",
    "apps/web/app/static/css/ff-dashboard-final.css",
    "apps/web/app/static/css/ff-dashboard-protected-exec.css",
    "apps/web/app/static/css/login.css",
    "apps/web/app/static/css/ff-login-calm.css",
    "apps/web/app/static/js/ff-campaign.js",
    "apps/web/app/static/js/ff-dashboard-protected-exec.js",
    "apps/web/app/templates/platform/index.html",
    "apps/web/app/templates/campaign/index.html",
    "apps/web/app/templates/campaign_premium.html",
    "apps/web/app/templates/platform/onboarding.html",
    "apps/web/app/templates/platform/login.html",
    "apps/web/app/templates/platform/dashboard.html",
    "apps/web/app/templates/platform/dashboard_locked.html",
]

REVIEW_ONLY = [
    "apps/web/app/static/css/campaign.css",
    "apps/web/app/static/css/ff-campaign-enterprise.css",
    "apps/web/app/static/css/ff-campaign-final-compression.css",
    "apps/web/app/static/css/ff.checkout.css",
    "apps/web/app/static/css/ff.cinematic.css",
    "apps/web/app/static/css/onboarding.css",
    "apps/web/app/static/css/ff-onboarding-executive.css",
    "apps/web/app/static/css/ff-homepage-executive.css",
    "apps/web/app/static/js/ff-embedded-checkout.js",
    "apps/web/app/static/js/ff-checkout-direct.js",
    "apps/web/app/static/js/ff-campaign-enterprise.js",
    "apps/web/app/static/js/ff-campaign-final-compression.js",
    "apps/web/app/static/js/ff-homepage-executive.js",
    "apps/web/app/static/js/ff-operator-dashboard.js",
    "apps/web/app/static/js/ff-payment-provider-status.js",
]

SAFE_QUARANTINE_CANDIDATE_DIRS = [
    "apps/web/app/templates/campaign/deprecated",
    "apps/web/app/static/css/_quarantine",
]

PATCH_SCRIPT_GLOBS = [
    "scripts/patches/*.py",
    "scripts/patch_*.py",
    "scripts/elite_patch_*.py",
]

def exists(path: str) -> bool:
    return (ROOT / path).exists()

def status_icon(path: str) -> str:
    return "✅" if exists(path) else "⚠️"

def load_inventory() -> dict:
    if INV.exists():
        return json.loads(INV.read_text(encoding="utf-8"))
    return {}

def write_repo_authority(inv: dict) -> None:
    lines = []
    lines.append("# FutureFunded Repo Authority\n")
    lines.append(f"Generated: `{datetime.now(timezone.utc).isoformat()}`\n")
    lines.append("## Production rule\n")
    lines.append("No new public pages should be added until this registry is intentionally updated. Future patches should target the canonical files below unless a migration plan says otherwise.\n")

    lines.append("## Canonical active surfaces\n")
    for surface, cfg in CANONICAL.items():
        lines.append(f"### {surface}")
        lines.append(f"- **Route:** `{cfg['route']}`")
        lines.append(f"- **Purpose:** {cfg['purpose']}")
        for group in ["templates", "css", "js", "audits"]:
            lines.append(f"- **{group.title()}:**")
            if cfg[group]:
                for p in cfg[group]:
                    lines.append(f"  - {status_icon(p)} `{p}`")
            else:
                lines.append("  - None")
        lines.append("")

    lines.append("## No-touch active authority files\n")
    lines.append("These files are considered production authority. Do not rename, delete, or quarantine without a deliberate migration.\n")
    for p in NO_TOUCH:
        lines.append(f"- {status_icon(p)} `{p}`")
    lines.append("")

    lines.append("## Review-only files\n")
    lines.append("These may be active, historical, or loaded indirectly. Do not quarantine until a reference audit confirms they are unused.\n")
    for p in REVIEW_ONLY:
        lines.append(f"- {status_icon(p)} `{p}`")
    lines.append("")

    lines.append("## Already quarantined / deprecated areas\n")
    for p in SAFE_QUARANTINE_CANDIDATE_DIRS:
        lines.append(f"- {status_icon(p)} `{p}`")
    lines.append("")

    lines.append("## Patch script policy\n")
    lines.append("Patch scripts are allowed during active development but should be moved to a timestamped archive once their changes are committed and audited.\n")
    for p in PATCH_SCRIPT_GLOBS:
        lines.append(f"- `{p}`")
    lines.append("")

    if inv:
        counts = inv.get("counts", {})
        lines.append("## Latest inventory counts\n")
        for k, v in counts.items():
            lines.append(f"- **{k}:** `{v}`")
        lines.append("")

        status = inv.get("git_status", [])
        lines.append("## Git status when inventory was generated\n")
        if status:
            for item in status:
                lines.append(f"- `{item}`")
        else:
            lines.append("- Clean")
        lines.append("")

    DOC.write_text("\n".join(lines), encoding="utf-8")

def write_release_map() -> None:
    lines = []
    lines.append("# FutureFunded Release Map\n")
    lines.append(f"Generated: `{datetime.now(timezone.utc).isoformat()}`\n")
    lines.append("## Release surfaces\n")
    lines.append("| Surface | Route | Status | Required audits |")
    lines.append("|---|---:|---|---|")
    lines.append("| Platform homepage | `/platform/` | Active | visual surface board |")
    lines.append("| Campaign demo | `/c/connect-atx-elite` | Active | visual surface board, payment smoke where needed |")
    lines.append("| Launch workspace | `/platform/onboarding` | Active | visual surface board |")
    lines.append("| Operator login | `/platform/login` | Active | visual surface board |")
    lines.append("| Protected dashboard | `/platform/dashboard` | Active/private | protected exec, final polish, visual surface board |")
    lines.append("| Locked dashboard | `/platform/dashboard` without token | Active/403 | protected exec, visual surface board |")
    lines.append("")

    lines.append("## Current release gate command set\n")
    lines.append("```bash")
    lines.append('FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_dashboard_protected_exec_audit.mjs')
    lines.append('FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_dashboard_final_polish_audit.mjs')
    lines.append('FF_BASE_URL="https://getfuturefunded.com" node scripts/audit/ff_visual_surface_board.mjs')
    lines.append("```")
    lines.append("")

    lines.append("## Freeze rule\n")
    lines.append("Do not add new pages, duplicate CSS authorities, or duplicate JS authorities until the registry is updated and the release gate remains green.\n")

    RELEASE.write_text("\n".join(lines), encoding="utf-8")

def main() -> None:
    inv = load_inventory()
    write_repo_authority(inv)
    write_release_map()
    print(f"Wrote {DOC}")
    print(f"Wrote {RELEASE}")

if __name__ == "__main__":
    main()
