from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd().resolve()
APP = ROOT / "apps/web/app"

OUT_JSON = ROOT / "artifacts/audit/ff_active_repo_inventory.json"
OUT_MD = ROOT / "artifacts/audit/ff_active_repo_inventory.md"
REGISTRY = ROOT / "docs/active-surface-registry.md"

IGNORE_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "artifacts/frontend-screenshots/archive",
}

ACTIVE_SURFACES = {
    "platform_home": {
        "route": "/platform/",
        "template": "apps/web/app/templates/platform/index.html",
        "purpose": "Public SaaS platform homepage / sales surface",
    },
    "campaign_demo": {
        "route": "/c/connect-atx-elite",
        "template": "apps/web/app/templates/campaign/index.html",
        "purpose": "Flagship donor/sponsor campaign demo",
    },
    "onboarding": {
        "route": "/platform/onboarding",
        "template": "apps/web/app/templates/platform/onboarding.html",
        "purpose": "Launch workspace / campaign setup",
    },
    "login": {
        "route": "/platform/login",
        "template": "apps/web/app/templates/platform/login.html",
        "purpose": "Operator access gate",
    },
    "dashboard": {
        "route": "/platform/dashboard?operator_token=...",
        "template": "apps/web/app/templates/platform/dashboard.html",
        "purpose": "Protected operator dashboard",
    },
    "dashboard_locked": {
        "route": "/platform/dashboard",
        "template": "apps/web/app/templates/platform/dashboard_locked.html",
        "purpose": "403 protected access fallback",
    },
}

CANONICAL_STATIC = {
    "global_design": [
        "apps/web/app/static/css/ff.css",
        "apps/web/app/static/css/ff-fortune500-final.css",
    ],
    "platform_home": [
        "apps/web/app/static/css/platform-home.css",
        "apps/web/app/static/css/ff-homepage-executive.css",
        "apps/web/app/static/js/ff-homepage-executive.js",
    ],
    "campaign": [
        "apps/web/app/static/css/ff-campaign-enterprise.css",
        "apps/web/app/static/css/ff-launch-completion.css",
        "apps/web/app/static/css/ff-campaign-enterprise.css",
        "apps/web/app/static/js/ff-campaign.js",
        "apps/web/app/static/js/ff-campaign-enterprise.js",
        "apps/web/app/static/js/ff-launch-completion.js",
    ],
    "onboarding": [
        "apps/web/app/static/css/onboarding.css",
        "apps/web/app/static/css/ff-onboarding-executive.css",
        "apps/web/app/static/js/islands/onboarding.js",
    ],
    "login": [
        "apps/web/app/static/css/login.css",
        "apps/web/app/static/css/ff-login-calm.css",
    ],
    "dashboard": [
        "apps/web/app/static/css/dashboard-modern.css",
        "apps/web/app/static/css/ff-dashboard-final.css",
        "apps/web/app/static/css/ff-dashboard-protected-exec.css",
        "apps/web/app/static/js/ff-dashboard-protected-exec.js",
        "apps/web/app/static/js/ff-operator-dashboard.js",
    ],
}

CANONICAL_AUDITS = [
    "scripts/audit/ff_visual_surface_board.mjs",
    "scripts/audit/ff_fortune500_final_polish_audit.mjs",
    "scripts/audit/ff_homepage_contract_audit.mjs",
    "scripts/audit/ff_homepage_executive_restructure_audit.mjs",
    "scripts/audit/ff_campaign_paint_rhythm_audit.mjs",
    "scripts/audit/ff_campaign_conversion_trim_audit.mjs",
    "scripts/audit/ff_text_to_donate_launch_audit.mjs",
    "scripts/audit/ff_onboarding_modern_audit.mjs",
    "scripts/audit/ff_onboarding_runtime_contract.mjs",
    "scripts/audit/ff_onboarding_executive_audit.mjs",
    "scripts/audit/ff_login_runtime_contract.mjs",
    "scripts/audit/ff_login_operator_calm_audit.mjs",
    "scripts/audit/ff_dashboard_command_center_audit.mjs",
    "scripts/audit/ff_dashboard_final_polish_audit.mjs",
    "scripts/audit/ff_dashboard_protected_exec_audit.mjs",
    "scripts/audit/ff_dashboard_first_paint_trace.mjs",
    "scripts/audit/ff_dashboard_flash_root_cause_audit.py",
]

SUSPICIOUS_NAME_PATTERNS = [
    ".bak",
    "backup",
    "old",
    "broken",
    "tmp",
    "temp",
    "scratch",
    "deprecated",
    "quarantine",
    "wave",
    "patch",
]

STATIC_REF_RE = re.compile(
    r"""(?:url_for\(\s*['"]static['"]\s*,\s*filename\s*=\s*['"]([^'"]+)['"]|/static/([^'")?\s]+)|static/(css/[^'")?\s]+|js/[^'")?\s]+))""",
    re.I,
)

TEMPLATE_REF_RE = re.compile(
    r"""\{%\s*(?:include|extends|import|from)\s+['"]([^'"]+)['"]""",
    re.I,
)

RENDER_TEMPLATE_RE = re.compile(
    r"""render_template\(\s*['"]([^'"]+)['"]""",
    re.I,
)

ROUTE_RE = re.compile(
    r"""@\w+(?:\.\w+)*\.route\(\s*['"]([^'"]+)['"]""",
    re.I,
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def should_skip(path: Path) -> bool:
    text = rel(path)
    return any(part in text for part in IGNORE_PARTS)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def safe_exists(path: Path) -> bool:
    """Path.exists(), but safe against malformed scanner candidates."""
    try:
        return path.exists()
    except OSError:
        return False


def normalize_static_asset(raw: str) -> str | None:
    """Normalize a static asset reference discovered by regex.

    The source scanner can see iframe URLs, Stripe/hCaptcha fragments,
    source maps, browser-extension URLs, or long query/hash strings.
    Only return plausible local static assets.
    """
    original = (raw or "").strip().strip("'\"")
    if not original:
        return None

    lowered = original.lower()

    # Reject external/protocol-style values immediately.
    if (
        "://" in lowered
        or lowered.startswith(("data:", "mailto:", "tel:", "javascript:", "//"))
        or "b.stripecdn.com" in lowered
        or "hcaptcha.com" in lowered
        or "recaptcha" in lowered
    ):
        return None

    # Reject very long raw candidates before Path construction/stat.
    if len(original) > 260:
        return None

    # Fragments like hcaptcha.html#frame=challenge are not local app assets.
    if "#" in original and any(x in lowered for x in ("frame=", "host=", "origin=", "sitekey=", "sentry=")):
        return None

    asset = original.split("?", 1)[0].split("#", 1)[0].strip()
    asset = asset.removeprefix("/static/")
    asset = asset.removeprefix("static/")

    if not asset or len(asset) > 180:
        return None

    if "\x00" in asset or ".." in asset or asset.startswith(("/", "\")):
        return None

    # Keep only normal static asset shapes used by this project.
    if not re.search(r"\.(css|js|mjs|png|jpg|jpeg|webp|svg|gif|ico|json|txt|xml|woff2?|ttf|map)$", asset, re.I):
        return None

    return asset


def all_files() -> list[Path]:
    return [
        p for p in ROOT.rglob("*")
        if p.is_file() and not should_skip(p)
    ]


def text_files() -> list[Path]:
    keep = {".py", ".html", ".jinja", ".j2", ".css", ".js", ".mjs", ".md", ".txt", ".json", ".toml", ".yml", ".yaml"}
    return [p for p in all_files() if p.suffix.lower() in keep]


def collect_refs() -> dict[str, Any]:
    static_refs: dict[str, set[str]] = defaultdict(set)
    template_refs: dict[str, set[str]] = defaultdict(set)
    render_templates: dict[str, set[str]] = defaultdict(set)
    routes: list[dict[str, str]] = []

    for path in text_files():
        txt = read(path)

        for match in STATIC_REF_RE.finditer(txt):
            raw_asset = next((g for g in match.groups() if g), "")
            asset = normalize_static_asset(raw_asset)
            if asset:
                static_refs[asset].add(rel(path))

        for match in TEMPLATE_REF_RE.finditer(txt):
            template_refs[match.group(1)].add(rel(path))

        for match in RENDER_TEMPLATE_RE.finditer(txt):
            render_templates[match.group(1)].add(rel(path))

        if path.suffix == ".py":
            for match in ROUTE_RE.finditer(txt):
                routes.append({"route": match.group(1), "source": rel(path)})

    return {
        "static_refs": {k: sorted(v) for k, v in sorted(static_refs.items())},
        "template_refs": {k: sorted(v) for k, v in sorted(template_refs.items())},
        "render_templates": {k: sorted(v) for k, v in sorted(render_templates.items())},
        "routes": sorted(routes, key=lambda x: (x["route"], x["source"])),
    }


def classify_files(refs: dict[str, Any]) -> dict[str, Any]:
    active_paths = set()

    for surface in ACTIVE_SURFACES.values():
        active_paths.add(surface["template"])

    for group in CANONICAL_STATIC.values():
        active_paths.update(group)

    active_paths.update(CANONICAL_AUDITS)

    # Add rendered templates and included templates as active-ish.
    for template, sources in refs["render_templates"].items():
        p = APP / "templates" / template
        if safe_exists(p):
            active_paths.add(rel(p))

    for template, sources in refs["template_refs"].items():
        p = APP / "templates" / template
        if safe_exists(p):
            active_paths.add(rel(p))

    # Add referenced static assets.
    for asset, sources in refs["static_refs"].items():
        p = APP / "static" / asset
        if safe_exists(p):
            active_paths.add(rel(p))

    important_dirs = [
        APP / "templates",
        APP / "static/css",
        APP / "static/js",
        ROOT / "scripts/audit",
        ROOT / "scripts/verify",
        ROOT / "scripts/release",
    ]

    inventory = []
    for base in important_dirs:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or should_skip(path):
                continue

            r = rel(path)
            lower = r.lower()
            active = r in active_paths
            suspicious = any(pat in lower for pat in SUSPICIOUS_NAME_PATTERNS)
            generated = lower.startswith(("artifacts/", "audit_outputs/"))
            patch_script = "/scripts/patches/" in f"/{lower}"

            status = "active" if active else "review"
            if suspicious and not active:
                status = "quarantine_candidate"
            if patch_script:
                status = "patch_script_review"

            inventory.append({
                "path": r,
                "status": status,
                "active": active,
                "suspicious_name": suspicious,
                "patch_script": patch_script,
                "size": path.stat().st_size,
            })

    return {
        "active_paths": sorted(active_paths),
        "inventory": inventory,
        "quarantine_candidates": [i for i in inventory if i["status"] in {"quarantine_candidate", "patch_script_review"}],
        "review_candidates": [i for i in inventory if i["status"] == "review"],
    }


def write_reports(refs: dict[str, Any], classified: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()

    report = {
        "generated_at": now,
        "root": str(ROOT),
        "active_surfaces": ACTIVE_SURFACES,
        "canonical_static": CANONICAL_STATIC,
        "canonical_audits": CANONICAL_AUDITS,
        "routes": refs["routes"],
        "render_templates": refs["render_templates"],
        "template_refs": refs["template_refs"],
        "static_refs": refs["static_refs"],
        "active_paths": classified["active_paths"],
        "quarantine_candidates": classified["quarantine_candidates"],
        "review_candidates": classified["review_candidates"],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# FutureFunded Active Repo Inventory")
    lines.append("")
    lines.append(f"Generated: `{now}`")
    lines.append("")
    lines.append("## Canonical active surfaces")
    lines.append("")
    lines.append("| Surface | Route | Template | Purpose |")
    lines.append("|---|---|---|---|")
    for name, item in ACTIVE_SURFACES.items():
        lines.append(f"| `{name}` | `{item['route']}` | `{item['template']}` | {item['purpose']} |")

    lines.append("")
    lines.append("## Canonical static ownership")
    lines.append("")
    for group, files in CANONICAL_STATIC.items():
        lines.append(f"### {group}")
        for file in files:
            exists = "✅" if (ROOT / file).exists() else "⚠️ missing"
            lines.append(f"- {exists} `{file}`")
        lines.append("")

    lines.append("## Canonical audit scripts")
    lines.append("")
    for file in CANONICAL_AUDITS:
        exists = "✅" if (ROOT / file).exists() else "⚠️ missing"
        lines.append(f"- {exists} `{file}`")

    lines.append("")
    lines.append("## Routes found by source scan")
    lines.append("")
    if refs["routes"]:
        lines.append("| Route | Source |")
        lines.append("|---|---|")
        for item in refs["routes"]:
            lines.append(f"| `{item['route']}` | `{item['source']}` |")
    else:
        lines.append("_No decorator routes found by regex scan._")

    lines.append("")
    lines.append("## Rendered templates found by source scan")
    lines.append("")
    if refs["render_templates"]:
        for template, sources in refs["render_templates"].items():
            lines.append(f"- `{template}`")
            for source in sources[:8]:
                lines.append(f"  - `{source}`")
    else:
        lines.append("_No render_template references found._")

    lines.append("")
    lines.append("## Quarantine candidates — review before moving")
    lines.append("")
    candidates = classified["quarantine_candidates"]
    if candidates:
        lines.append("| Status | Path | Size |")
        lines.append("|---|---|---:|")
        for item in candidates[:300]:
            lines.append(f"| `{item['status']}` | `{item['path']}` | {item['size']} |")
    else:
        lines.append("_No obvious quarantine candidates found._")

    lines.append("")
    lines.append("## Review candidates")
    lines.append("")
    lines.append("These are not declared canonical and were not detected as directly referenced. Review before keeping, quarantining, or deleting.")
    lines.append("")
    review = classified["review_candidates"]
    if review:
        lines.append("| Path | Size |")
        lines.append("|---|---:|")
        for item in review[:300]:
            lines.append(f"| `{item['path']}` | {item['size']} |")
    else:
        lines.append("_No review candidates found._")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    registry = []
    registry.append("# FutureFunded Active Surface Registry")
    registry.append("")
    registry.append("This file is the production source-of-truth for active public/operator surfaces.")
    registry.append("")
    registry.append("## Do not add new pages without updating this registry")
    registry.append("")
    registry.append("| Surface | Route | Template | CSS/JS authority |")
    registry.append("|---|---|---|---|")
    for name, item in ACTIVE_SURFACES.items():
        ownership = []
        for group, files in CANONICAL_STATIC.items():
            if name in group or (name == "platform_home" and group == "platform_home"):
                ownership.extend(files)
        if name in {"campaign_demo"}:
            ownership.extend(CANONICAL_STATIC["campaign"])
        if name in {"dashboard", "dashboard_locked"}:
            ownership.extend(CANONICAL_STATIC["dashboard"])
        if name == "login":
            ownership.extend(CANONICAL_STATIC["login"])
        if name == "onboarding":
            ownership.extend(CANONICAL_STATIC["onboarding"])

        ownership_text = "<br>".join(f"`{x}`" for x in dict.fromkeys(ownership)) or "`ff.css`"
        registry.append(f"| `{name}` | `{item['route']}` | `{item['template']}` | {ownership_text} |")

    registry.append("")
    registry.append("## Product policy")
    registry.append("")
    registry.append("- No new pages until the active set above is clean.")
    registry.append("- Public legal/contact links should use existing canonical routes only.")
    registry.append("- Patch scripts are temporary and should be removed after their commit lands.")
    registry.append("- Backups and experiments should move to `_archive/` or `artifacts/backups/`, never stay mixed with active source.")
    registry.append("- `ff.css` remains the shared global authority. Page-specific CSS must be scoped by `html[data-ff-page]` or body class.")
    registry.append("")

    REGISTRY.write_text("\n".join(registry) + "\n", encoding="utf-8")


def main() -> None:
    refs = collect_refs()
    classified = classify_files(refs)
    write_reports(refs, classified)

    print("FutureFunded active repo inventory complete.")
    print(f"- JSON: {rel(OUT_JSON)}")
    print(f"- MD:   {rel(OUT_MD)}")
    print(f"- Registry: {rel(REGISTRY)}")
    print()
    print(f"Active paths: {len(classified['active_paths'])}")
    print(f"Quarantine candidates: {len(classified['quarantine_candidates'])}")
    print(f"Review candidates: {len(classified['review_candidates'])}")


if __name__ == "__main__":
    main()
