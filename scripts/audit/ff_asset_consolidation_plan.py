from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
MANIFEST = ROOT / "audit_outputs" / "repo-authority" / "live_route_asset_manifest.json"
OUT = ROOT / "audit_outputs" / "repo-authority" / "asset_consolidation_plan.md"

if not MANIFEST.exists():
    raise SystemExit("Missing live_route_asset_manifest.json. Run scripts/audit/ff_live_route_asset_manifest.py first.")

data = json.loads(MANIFEST.read_text(encoding="utf-8"))

ROUTE_TARGETS = {
    "Platform homepage": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/platform-home.css"],
        "merge_into": "apps/web/app/static/css/platform-home.css",
        "keep_js": ["apps/web/app/static/js/ff-homepage-executive.js"],
        "notes": "Homepage should keep ff.css global plus platform-home.css as route authority.",
    },
    "Campaign demo": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/campaign.css"],
        "merge_into": "apps/web/app/static/css/campaign.css",
        "keep_js": ["apps/web/app/static/js/ff-campaign.js"],
        "notes": "Campaign is money surface. Consolidate last after selector/payment smoke.",
    },
    "Launch workspace / onboarding": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/onboarding.css"],
        "merge_into": "apps/web/app/static/css/onboarding.css",
        "keep_js": ["apps/web/app/static/js/ff-launch-completion.js"],
        "notes": "Onboarding currently does not load islands/onboarding.js in live manifest.",
    },
    "Operator login": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/login.css"],
        "merge_into": "apps/web/app/static/css/login.css",
        "keep_js": ["apps/web/app/static/js/ff-login.js"],
        "notes": "Merge ff-login-calm.css into login.css after audit.",
    },
    "Protected dashboard": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/dashboard-modern.css"],
        "merge_into": "apps/web/app/static/css/dashboard-modern.css",
        "keep_js": ["apps/web/app/static/js/ff-dashboard-protected-exec.js"],
        "notes": "Merge dashboard-final/protected-exec/launch-completion dashboard CSS into dashboard-modern.css.",
    },
    "Locked dashboard": {
        "keep_css": ["apps/web/app/static/css/ff.css", "apps/web/app/static/css/login.css"],
        "merge_into": "apps/web/app/static/css/login.css",
        "keep_js": [],
        "notes": "Locked dashboard should share login.css and avoid separate JS.",
    },
}

def unique(items):
    out = []
    seen = set()
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out

lines = []
lines.append("# FutureFunded Asset Consolidation Plan\n")
lines.append(f"Generated: `{datetime.now(timezone.utc).isoformat()}`\n")
lines.append("Goal: reduce each live surface to global `ff.css` plus one surface CSS authority where possible. No files moved by this plan.\n")

for route in data["routes"]:
    name = route["name"]
    target = ROUTE_TARGETS.get(name, {})
    css = unique([x["local_path"] for x in route.get("stylesheets", [])])
    js = unique([x["local_path"] for x in route.get("scripts", [])])

    keep_css = target.get("keep_css", [])
    keep_js = target.get("keep_js", [])

    extra_css = [x for x in css if x not in keep_css]
    extra_js = [x for x in js if x not in keep_js]

    lines.append(f"## {name}")
    lines.append(f"- **Route:** `{route['path']}`")
    lines.append(f"- **Template hints:** `{', '.join(route.get('template_hints', [])) or 'none'}`")
    lines.append(f"- **CSS now:** `{len(css)}` unique")
    lines.append(f"- **JS now:** `{len(js)}` unique")
    lines.append(f"- **Target CSS authority:** `{target.get('merge_into', 'TBD')}`")
    lines.append(f"- **Notes:** {target.get('notes', 'TBD')}")
    lines.append("")
    lines.append("### Keep CSS")
    for x in keep_css:
        lines.append(f"- `{x}`")
    lines.append("")
    lines.append("### Merge or retire CSS candidates")
    if extra_css:
        for x in extra_css:
            lines.append(f"- `{x}`")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("### Keep JS")
    if keep_js:
        for x in keep_js:
            lines.append(f"- `{x}`")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("### Merge or retire JS candidates")
    if extra_js:
        for x in extra_js:
            lines.append(f"- `{x}`")
    else:
        lines.append("- None")
    lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT.relative_to(ROOT)}")
