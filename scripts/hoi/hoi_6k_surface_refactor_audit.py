#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path.cwd()
STAMP = time.strftime("%Y%m%d-%H%M%S")
OUT_ROOT = ROOT / "audit_outputs" / "hoi-6k-surface-refactor"
RUN_DIR = OUT_ROOT / STAMP
LATEST_DIR = OUT_ROOT / "latest"

ACTIVE_SURFACES = {
    "platform_home": {
        "route": "/platform/",
        "role": "Public SaaS sales page",
        "template": "apps/web/app/templates/platform/index.html",
        "keep": True,
        "target": "Short, premium product narrative that sells teams, schools, clubs, and nonprofits.",
    },
    "campaign": {
        "route": "/c/connect-atx-elite",
        "role": "Public donor/sponsor money funnel",
        "template": "apps/web/app/templates/campaign/index.html",
        "keep": True,
        "target": "Flagship donor page with one dominant giving path and clean sponsor support.",
    },
    "login": {
        "route": "/platform/login",
        "role": "Protected organizer access",
        "template": "apps/web/app/templates/platform/login.html",
        "keep": True,
        "target": "Premium auth state that feels intentional, not like an error.",
    },
    "onboarding": {
        "route": "/platform/onboarding",
        "role": "Private launch setup workspace",
        "template": "apps/web/app/templates/platform/onboarding.html",
        "keep": True,
        "target": "Essential setup only: basics, brand kit, giving readiness, sponsor packages, handoff.",
    },
    "dashboard": {
        "route": "/platform/dashboard",
        "role": "Private operator command center",
        "template": "apps/web/app/templates/platform/dashboard.html",
        "keep": True,
        "target": "Command center for readiness, ledger, sponsor review, follow-up, and launch activity.",
    },
}

STATIC_FILES = [
    "apps/web/app/static/css/ff.css",
    "apps/web/app/static/css/campaign.css",
    "apps/web/app/static/js/ff-campaign.js",
    "apps/web/app/static/js/ff-onboarding.js",
    "apps/web/app/static/js/ff-operator-dashboard.js",
]

HEADER_CLASS_PATTERNS = [
    "ff-siteHeader",
    "ff-loginAuthority__topbar",
    "ffOnboardV2__topbar",
    "ff-dashboardModern__topbar",
    "ff-campaignHeader",
]

REQUIRED_CONTRACTS = {
    "all": ["data-ff-header", "data-ff-header-mode", "data-ff-brand-context"],
    "campaign": ["data-ff-open-checkout", "data-ff-open-sponsor", "data-ff-share-trigger"],
    "onboarding": ["data-ff-onboard-root", "data-ff-theme-picker", "data-ff-save-onboarding"],
    "dashboard": ["data-ff-operator-root", "data-ff-dashboard-root"],
}

def read(path: Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""

def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def extract_blocks(text: str, tag: str) -> list[str]:
    pattern = re.compile(rf"<{tag}\b.*?</{tag}>", re.I | re.S)
    return pattern.findall(text)

def extract_opening_tags(text: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}\b[^>]*>", text, flags=re.I)

def extract_attrs(tag: str) -> dict[str, str]:
    attrs = {}
    for match in re.finditer(r"""([:\w-]+)(?:\s*=\s*["']([^"']*)["'])?""", tag):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else ""
        if key not in {"header", "section", "main", "a", "button", "div", "input", "select", "textarea", "form"}:
            attrs[key] = value
    return attrs

def classify_header(text: str) -> dict:
    headers = extract_blocks(text, "header")
    opening = extract_opening_tags(text, "header")

    found_classes = sorted({p for p in HEADER_CLASS_PATTERNS if p in text})
    data_contracts = sorted(set(re.findall(r"data-ff-[\w-]+", text)))

    return {
        "header_count": len(headers),
        "opening_tags": opening[:4],
        "header_classes": found_classes,
        "has_data_ff_header": "data-ff-header" in text,
        "has_header_mode": "data-ff-header-mode" in text,
        "has_brand_context": "data-ff-brand-context" in text,
        "data_contracts_sample": data_contracts[:80],
    }

def analyze_template(name: str, cfg: dict) -> dict:
    path = ROOT / cfg["template"]
    text = read(path)

    headers = classify_header(text)
    links = re.findall(r"<a\b[^>]*>(.*?)</a>", text, flags=re.I | re.S)
    buttons = re.findall(r"<button\b[^>]*>(.*?)</button>", text, flags=re.I | re.S)
    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", text, flags=re.I | re.S)
    h2s = re.findall(r"<h2\b[^>]*>(.*?)</h2>", text, flags=re.I | re.S)
    sections = extract_opening_tags(text, "section")
    forms = extract_opening_tags(text, "form")
    css_refs = re.findall(r"""href=["']([^"']+\.css[^"']*)["']""", text)
    js_refs = re.findall(r"""src=["']([^"']+\.js[^"']*)["']""", text)

    controls = [clean(strip_tags(x)) for x in links + buttons]
    controls = [x for x in controls if x]

    contracts = REQUIRED_CONTRACTS.get("all", []) + REQUIRED_CONTRACTS.get(name, [])
    missing_contracts = [token for token in contracts if token not in text]

    copy_text = clean(strip_tags(text))
    words = copy_text.split()

    flags = []

    if not headers["has_data_ff_header"]:
        flags.append("Header missing shared data-ff-header contract.")
    if not headers["has_header_mode"]:
        flags.append("Header missing data-ff-header-mode.")
    if not headers["has_brand_context"] and name != "dashboard":
        flags.append("Header missing data-ff-brand-context.")
    if len(headers["header_classes"]) > 1:
        flags.append("Multiple header class systems appear in this template.")
    if len(controls) > 24 and name in {"campaign", "platform_home"}:
        flags.append("High CTA/control count; review hierarchy on mobile.")
    if len(sections) > 8 and name != "campaign":
        flags.append("Many sections for a non-campaign page; consider compression.")
    if missing_contracts:
        flags.append(f"Missing expected contracts: {', '.join(missing_contracts)}")

    return {
        "name": name,
        "route": cfg["route"],
        "role": cfg["role"],
        "target": cfg["target"],
        "template": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "line_count": len(text.splitlines()),
        "word_count_estimate": len(words),
        "header": headers,
        "h1": [clean(strip_tags(x)) for x in h1s[:4]],
        "h2_sample": [clean(strip_tags(x)) for x in h2s[:10]],
        "section_count": len(sections),
        "form_count": len(forms),
        "control_count": len(controls),
        "controls_sample": controls[:32],
        "css_refs": css_refs,
        "js_refs": js_refs,
        "missing_contracts": missing_contracts,
        "flags": flags,
    }

def analyze_static() -> dict:
    out = {}

    for rel in STATIC_FILES:
        path = ROOT / rel
        text = read(path)

        out[rel] = {
            "exists": path.exists(),
            "line_count": len(text.splitlines()),
            "hoi_markers": sorted(set(re.findall(r"hoi-[\w.-]+", text)))[:80],
            "header_selectors": sorted({p for p in HEADER_CLASS_PATTERNS if p in text}),
            "data_contracts_sample": sorted(set(re.findall(r"data-ff-[\w-]+", text)))[:80],
        }

    return out

def build_recommendations(results: list[dict]) -> list[dict]:
    return [
        {
            "priority": 1,
            "title": "Create one FutureFunded shell/header partial",
            "files": [
                "apps/web/app/templates/_partials/ff_shell_header.html",
                "apps/web/app/static/css/ff.css",
            ],
            "reason": "All active pages should use the same logo mark, brand lockup, nav rhythm, and mobile behavior.",
            "contract": "data-ff-header data-ff-header-mode data-ff-brand-context",
        },
        {
            "priority": 2,
            "title": "Adopt three nav modes only",
            "modes": {
                "marketing": "Product, Campaigns, Sponsors, Proof, FAQ, View fundraiser, Start campaign",
                "campaign": "Impact, Sponsors, Team, Help, Share, Give securely",
                "operator": "Setup, Public page, Sponsors, Dashboard",
            },
            "reason": "Consistency without forcing donor pages to look like admin pages.",
        },
        {
            "priority": 3,
            "title": "Create shared section/card primitives",
            "files": [
                "apps/web/app/templates/_partials/ff_surface_section.html",
                "apps/web/app/static/css/ff.css",
            ],
            "reason": "Hero, proof strip, card grid, metric card, package card, and CTA rail should not be reinvented per page.",
        },
        {
            "priority": 4,
            "title": "Compress non-campaign pages",
            "targets": {
                "platform_home": "Keep to product story, campaign proof, sponsor value, launch path, FAQ.",
                "onboarding": "Keep only essentials; no public donor clutter.",
                "dashboard": "Keep all operator modules, but group cards into command lanes.",
                "login": "Keep one hero + one access card.",
            },
            "reason": "Shorter pages feel more premium when each page has one clear job.",
        },
        {
            "priority": 5,
            "title": "Formalize backend-ready brand kit contract",
            "fields": [
                "brand_preset",
                "primary_color",
                "accent_color",
                "soft_color",
                "logo_url",
                "text_to_donate_enabled",
            ],
            "reason": "Current frontend preview contract should become server-rendered campaign configuration later.",
        },
    ]

def write_report(report: dict) -> str:
    lines = [
        "# FutureFunded HOI 6K — Full Surface Refactor Audit",
        "",
        f"**Generated:** {report['generated_at']}",
        "",
        "## Executive decision",
        "",
        "**Do not remove the main pages.** Keep platform, campaign, login, onboarding, and dashboard. Refactor shared shell/header/components and shorten page-specific content instead.",
        "",
        "## Active surfaces",
        "",
        "| Surface | Route | Role | Lines | Sections | Controls | Header mode ready | Findings |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]

    for surface in report["surfaces"]:
        header_ok = "yes" if surface["header"]["has_data_ff_header"] and surface["header"]["has_header_mode"] else "no"
        findings = "<br>".join(surface["flags"]) if surface["flags"] else "None"
        lines.append(
            f"| `{surface['name']}` | `{surface['route']}` | {surface['role']} | {surface['line_count']} | {surface['section_count']} | {surface['control_count']} | {header_ok} | {findings} |"
        )

    lines += [
        "",
        "## Per-page review",
        "",
    ]

    for surface in report["surfaces"]:
        lines += [
            f"### {surface['name']} — {surface['route']}",
            "",
            f"**Target:** {surface['target']}",
            "",
            f"- Template: `{surface['template']}`",
            f"- H1: `{surface['h1'][0] if surface['h1'] else 'none'}`",
            f"- Sections: `{surface['section_count']}`",
            f"- Forms: `{surface['form_count']}`",
            f"- Controls: `{surface['control_count']}`",
            f"- Header classes: `{', '.join(surface['header']['header_classes']) or 'none'}`",
            f"- CSS refs: `{', '.join(surface['css_refs']) or 'none'}`",
            f"- JS refs: `{', '.join(surface['js_refs']) or 'none'}`",
            "",
            "**Top controls:**",
            "",
        ]

        for control in surface["controls_sample"][:16]:
            lines.append(f"- {control}")

        if surface["flags"]:
            lines += ["", "**Findings:**", ""]
            for flag in surface["flags"]:
                lines.append(f"- {flag}")

        lines.append("")

    lines += [
        "## Recommended refactor plan",
        "",
    ]

    for rec in report["recommendations"]:
        lines += [
            f"### {rec['priority']}. {rec['title']}",
            "",
            f"{rec['reason']}",
            "",
        ]

        for key, value in rec.items():
            if key in {"priority", "title", "reason"}:
                continue
            lines.append(f"- **{key}:** `{json.dumps(value, ensure_ascii=False)}`")

        lines.append("")

    lines += [
        "## Next implementation wave",
        "",
        "Recommended next wave:",
        "",
        "```txt",
        "HOI 6L — Shared Shell Partial + Page Composition Refactor",
        "```",
        "",
        "Scope:",
        "",
        "- Create `_partials/ff_shell_header.html`",
        "- Convert all active pages to the same shell/header contract",
        "- Keep three nav modes: marketing, campaign, operator",
        "- Keep all current hooks and payment/dashboard behavior",
        "- Compress onboarding/platform copy without deleting core pages",
        "- Re-run visual, payment, onboarding/operator, and brand-kit gates",
        "",
    ]

    return "\n".join(lines)

def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    surfaces = [analyze_template(name, cfg) for name, cfg in ACTIVE_SURFACES.items()]

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "surfaces": surfaces,
        "static": analyze_static(),
        "recommendations": build_recommendations(surfaces),
    }

    (RUN_DIR / "report.json").write_text(json.dumps(report, indent=2))
    (RUN_DIR / "report.md").write_text(write_report(report))

    if LATEST_DIR.exists() or LATEST_DIR.is_symlink():
        if LATEST_DIR.is_symlink():
            LATEST_DIR.unlink()
        else:
            import shutil
            shutil.rmtree(LATEST_DIR)

    import shutil
    shutil.copytree(RUN_DIR, LATEST_DIR)

    print("FutureFunded HOI 6K refactor audit complete.")
    print(f"Report: {LATEST_DIR / 'report.md'}")
    print(f"JSON:   {LATEST_DIR / 'report.json'}")

if __name__ == "__main__":
    main()
