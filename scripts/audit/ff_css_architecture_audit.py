from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
STATIC_CSS = ROOT / "apps/web/app/static/css"
TEMPLATES = ROOT / "apps/web/app/templates"
OUT_DIR = ROOT / "audit_outputs/css-architecture"
OUT_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
report_path = OUT_DIR / f"{timestamp}-css-architecture-report.md"
latest_path = OUT_DIR / "latest-css-architecture-report.md"
json_path = OUT_DIR / f"{timestamp}-css-architecture-report.json"

css_files = sorted(STATIC_CSS.glob("*.css"))
template_files = sorted(TEMPLATES.rglob("*.html"))

css_include_re = re.compile(
    r"""(?:url_for\(['"]static['"],\s*filename=['"](?P<urlfor>css/[^'"]+\.css)['"]\)|(?P<direct>/static/css/[^"')\s]+\.css)|(?P<plain>css/[^"')\s]+\.css))"""
)

marker_re = re.compile(r"/\*\s*(FF_[A-Z0-9_ -]+?)(?:_START|_END)?(?:\s|\*/)")
layer_re = re.compile(r"@layer\s+([^;{]+)[;{]")
selector_re = re.compile(r"(?m)^\s*([^@{}\n][^{]+)\s*\{")

template_css_refs: dict[str, list[str]] = {}
all_refs: Counter[str] = Counter()

for template in template_files:
    text = template.read_text(encoding="utf-8", errors="ignore")
    refs = []
    for m in css_include_re.finditer(text):
        ref = m.group("urlfor") or m.group("direct") or m.group("plain")
        if not ref:
            continue
        ref = ref.replace("/static/", "")
        refs.append(ref)
        all_refs[ref] += 1
    if refs:
        template_css_refs[str(template.relative_to(ROOT))] = sorted(set(refs))

css_inventory = {}
global_risk_terms = [
    "dashboard",
    "onboarding",
    "login",
    "platform-home",
    "homepage",
    "campaign",
    "operator",
    "checkout",
    "sponsor",
]

for css in css_files:
    text = css.read_text(encoding="utf-8", errors="ignore")
    rel = str(css.relative_to(ROOT))
    basename_ref = f"css/{css.name}"

    markers = sorted(set(marker_re.findall(text)))
    layers = sorted(set(s.strip() for s in layer_re.findall(text)))

    class_hits = Counter()
    for term in global_risk_terms:
        class_hits[term] = len(re.findall(term, text, flags=re.I))

    important_count = text.count("!important")
    media_count = text.count("@media")
    layer_count = text.count("@layer")
    line_count = text.count("\n") + 1

    selectors = []
    for sm in selector_re.finditer(text):
        selector = " ".join(sm.group(1).strip().split())
        if len(selector) < 220:
            selectors.append(selector)

    duplicate_selectors = [
        item for item, count in Counter(selectors).most_common()
        if count >= 3
    ][:30]

    css_inventory[rel] = {
        "basename_ref": basename_ref,
        "is_referenced": all_refs[basename_ref] > 0,
        "reference_count": all_refs[basename_ref],
        "line_count": line_count,
        "important_count": important_count,
        "media_count": media_count,
        "layer_count": layer_count,
        "layers": layers,
        "marker_count": len(markers),
        "markers": markers[:120],
        "risk_hits": dict(class_hits),
        "duplicate_selectors_top": duplicate_selectors,
    }

# Identify missing CSS refs.
existing_refs = {f"css/{p.name}" for p in css_files}
missing_refs = sorted(ref for ref in all_refs if ref.startswith("css/") and ref not in existing_refs)
unreferenced_css = sorted(
    rel for rel, info in css_inventory.items()
    if not info["is_referenced"] and not Path(rel).name.startswith("_")
)

# Surface/page mapping expectations.
expected_pages = {
    "platform/index.html": ["css/ff.css", "css/platform-home.css"],
    "campaign/index.html": ["css/ff.css"],
    "platform/dashboard.html": ["css/ff.css", "css/dashboard-modern.css"],
    "platform/onboarding.html": ["css/ff.css", "css/onboarding.css"],
    "platform/login.html": ["css/ff.css", "css/login.css"],
}

findings = []

ff_rel = "apps/web/app/static/css/ff.css"
ff_info = css_inventory.get(ff_rel)
if ff_info:
    if ff_info["important_count"] > 500:
        findings.append({
            "severity": "high",
            "area": "ff.css",
            "finding": f"ff.css has {ff_info['important_count']} !important rules. This usually means multiple emergency layers are fighting.",
            "fix": "Move page-specific overrides into page authority files and reduce ff.css to foundation tokens/primitives.",
        })
    if ff_info["marker_count"] > 25:
        findings.append({
            "severity": "high",
            "area": "ff.css",
            "finding": f"ff.css contains {ff_info['marker_count']} FF marker blocks.",
            "fix": "Migrate dashboard/home/login/onboarding marker blocks into page CSS or delete retired patch blocks after screenshot verification.",
        })
    dash_hits = ff_info["risk_hits"].get("dashboard", 0)
    if dash_hits > 100:
        findings.append({
            "severity": "high",
            "area": "dashboard cascade",
            "finding": f"ff.css contains {dash_hits} dashboard-related hits.",
            "fix": "Load dashboard-modern.css after ff.css and migrate dashboard-only styling out of ff.css.",
        })

if missing_refs:
    findings.append({
        "severity": "high",
        "area": "missing CSS",
        "finding": f"Templates reference missing CSS files: {', '.join(missing_refs)}",
        "fix": "Either create the file or remove the stale link.",
    })

if unreferenced_css:
    findings.append({
        "severity": "medium",
        "area": "unreferenced CSS",
        "finding": f"Unreferenced top-level CSS files found: {', '.join(unreferenced_css[:20])}",
        "fix": "Move retired files into static/css/_quarantine/ after confirming they are not dynamically loaded.",
    })

# Build markdown report.
lines = []
lines.append("# FutureFunded CSS Architecture Audit")
lines.append("")
lines.append(f"Generated: `{timestamp}`")
lines.append("")
lines.append("## Executive verdict")
lines.append("")
lines.append("Use `ff.css` as the foundation stylesheet only, then load one page-specific authority stylesheet after it for each major surface.")
lines.append("")
lines.append("Recommended launch architecture:")
lines.append("")
lines.append("```txt")
lines.append("ff.css                 foundation: tokens, reset, base, shared primitives")
lines.append("platform-home.css      homepage-only composition")
lines.append("campaign.css           public campaign-only composition")
lines.append("dashboard-modern.css   operator dashboard-only composition")
lines.append("onboarding.css         launch setup/onboarding-only composition")
lines.append("login.css              login-only composition")
lines.append("```")
lines.append("")

lines.append("## Highest-priority findings")
lines.append("")
if findings:
    for i, f in enumerate(findings, 1):
        lines.append(f"### {i}. [{f['severity'].upper()}] {f['area']}")
        lines.append("")
        lines.append(f"**Finding:** {f['finding']}")
        lines.append("")
        lines.append(f"**Required fix:** {f['fix']}")
        lines.append("")
else:
    lines.append("No high-risk CSS architecture findings detected.")
    lines.append("")

lines.append("## Template CSS include map")
lines.append("")
for template, refs in sorted(template_css_refs.items()):
    lines.append(f"### `{template}`")
    for ref in refs:
        status = "present" if ref in existing_refs else "MISSING"
        lines.append(f"- `{ref}` — {status}")
    lines.append("")

lines.append("## CSS file inventory")
lines.append("")
lines.append("| CSS file | Referenced | Lines | !important | Markers | Media | Risk notes |")
lines.append("|---|---:|---:|---:|---:|---:|---|")
for rel, info in sorted(css_inventory.items()):
    risk_notes = []
    for key in ["dashboard", "homepage", "platform-home", "campaign", "onboarding", "login"]:
        value = info["risk_hits"].get(key, 0)
        if value >= 30:
            risk_notes.append(f"{key}:{value}")
    lines.append(
        f"| `{rel}` | {info['reference_count']} | {info['line_count']} | "
        f"{info['important_count']} | {info['marker_count']} | {info['media_count']} | "
        f"{', '.join(risk_notes) if risk_notes else '—'} |"
    )
lines.append("")

lines.append("## ff.css marker sample")
lines.append("")
if ff_info and ff_info["markers"]:
    for marker in ff_info["markers"][:80]:
        lines.append(f"- `{marker}`")
else:
    lines.append("No FF markers found in ff.css.")
lines.append("")

lines.append("## Recommended next migration order")
lines.append("")
lines.append("1. Dashboard: keep `dashboard-modern.css` loaded after `ff.css`; stop adding dashboard rules to `ff.css`.")
lines.append("2. Homepage: keep `platform-home.css` as the homepage authority.")
lines.append("3. Onboarding: create/load `onboarding.css` after `ff.css`.")
lines.append("4. Login: create/load `login.css` after `ff.css`.")
lines.append("5. Campaign: only after dashboard/login/onboarding are stable, extract campaign page composition into `campaign.css`.")
lines.append("6. Final cleanup: reduce `ff.css` to foundation primitives and shared contracts.")
lines.append("")

data = {
    "generated": timestamp,
    "findings": findings,
    "template_css_refs": template_css_refs,
    "css_inventory": css_inventory,
    "missing_refs": missing_refs,
    "unreferenced_css": unreferenced_css,
}

json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
report_path.write_text("\n".join(lines), encoding="utf-8")
latest_path.write_text("\n".join(lines), encoding="utf-8")

print(f"CSS architecture audit complete")
print(f"Report: {report_path}")
print(f"Latest: {latest_path}")
print(f"JSON:   {json_path}")

print()
print("Top findings:")
if findings:
    for f in findings[:8]:
        print(f"- [{f['severity']}] {f['area']}: {f['finding']}")
else:
    print("- No high-priority findings detected.")

print()
print("Open report:")
print(f"  sed -n '1,240p' {latest_path}")
