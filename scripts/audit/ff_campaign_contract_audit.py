from pathlib import Path
import re
import json

ROOT = Path.cwd()
HTML = ROOT / "apps/web/app/templates/campaign/index.html"
CSS = ROOT / "apps/web/app/static/css/ff.css"
JS_DIR = ROOT / "apps/web/app/static/js"

CLASS_ATTR_RE = re.compile(r'class=["\']([^"\']+)["\']')
ID_RE = re.compile(r'id=["\']([^"\']+)["\']')
HREF_ANCHOR_RE = re.compile(r'href=["\']#([^"\']+)["\']')
DATA_FF_RE = re.compile(r'\b(data-ff-[a-zA-Z0-9_-]+)')
CSS_CLASS_RE = re.compile(r'(?<![a-zA-Z0-9_-])\.([a-zA-Z_][a-zA-Z0-9_-]*)')
CSS_ID_RE = re.compile(r'(?<![a-zA-Z0-9_-])#([a-zA-Z_][a-zA-Z0-9_-]*)')

IMPORTANT_CLASSES = [
    "ff-impactCardsGrid",
    "ff-impactActionCard",
    "ff-impactActionCard__amount",
    "ff-impactActionCard__title",
    "ff-impactActionCard__copy",
    "ff-sectionActions",
    "ff-campaignHero",
    "ff-donatePanel",
    "ff-sponsorCleanGrid",
    "ff-sponsorCleanCard",
    "ff-sponsorIntakeGrid",
    "ff-teamGrid--story",
    "ff-squadProofRail",
]

IMPORTANT_HOOKS = [
    "data-ff-open-checkout",
    "data-ff-donate-trigger",
    "data-ff-payment-trigger",
    "data-ff-sponsor-trigger",
    "data-ff-open-sponsor",
    "data-ff-share-trigger",
    "data-ff-qr-trigger",
    "data-ff-sponsor-form",
    "data-ff-sponsor-package",
]

def read(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Missing {path}")
    return path.read_text(encoding="utf-8", errors="replace")

def extract_html_classes(text: str) -> set[str]:
    out = set()
    for raw in CLASS_ATTR_RE.findall(text):
        for token in raw.split():
            token = token.strip()
            if token and "{{" not in token and "{%" not in token:
                out.add(token)
    return out

def has_rule_for(css: str, cls: str) -> bool:
    return re.search(rf'\.{re.escape(cls)}(?:[\s,.:#>\[{{]|$)', css) is not None

def collect_js_text() -> str:
    chunks = []
    if JS_DIR.exists():
        for path in JS_DIR.rglob("*.js"):
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
    return "\n".join(chunks)

html = read(HTML)
css = read(CSS)
js = collect_js_text()

html_classes = extract_html_classes(html)
css_classes = set(CSS_CLASS_RE.findall(css))
html_ids = set(ID_RE.findall(html))
href_anchors = set(HREF_ANCHOR_RE.findall(html))
html_hooks = set(DATA_FF_RE.findall(html))
css_ids = set(CSS_ID_RE.findall(css))

missing_anchor_targets = sorted(a for a in href_anchors if a not in html_ids)
important_class_report = {
    cls: {
        "in_html": cls in html_classes,
        "in_css": has_rule_for(css, cls),
    }
    for cls in IMPORTANT_CLASSES
}
important_hook_report = {
    hook: {
        "in_html": hook in html_hooks,
        "in_js": hook in js or hook.replace("data-ff-", "[data-ff-") in js,
        "in_css": hook in css,
    }
    for hook in IMPORTANT_HOOKS
}

impact_css_checks = {
    "grid_defined": has_rule_for(css, "ff-impactCardsGrid"),
    "card_defined": has_rule_for(css, "ff-impactActionCard"),
    "copy_defined": has_rule_for(css, "ff-impactActionCard__copy"),
    "wrap_safety_present": (
        (
            "ff-impact-contract-repair-v13" in css
            or "FutureFunded Campaign Launch Authority v1.0" in css
            or "FutureFunded Campaign Lower Funnel Finish v1.1" in css
        )
        and "white-space: normal" in css
        and "overflow-wrap" in css
    ),
}

html_ff_not_in_css = sorted(
    cls for cls in html_classes
    if cls.startswith("ff-") and cls not in css_classes
)

report = {
    "files": {
        "html": str(HTML.relative_to(ROOT)),
        "css": str(CSS.relative_to(ROOT)),
    },
    "counts": {
        "html_ff_classes": len([c for c in html_classes if c.startswith("ff-")]),
        "css_classes": len(css_classes),
        "html_data_ff_hooks": len(html_hooks),
        "html_ids": len(html_ids),
        "href_anchors": len(href_anchors),
    },
    "missing_anchor_targets": missing_anchor_targets,
    "important_classes": important_class_report,
    "important_hooks": important_hook_report,
    "impact_css_checks": impact_css_checks,
    "html_ff_classes_without_direct_css_rule_sample": html_ff_not_in_css[:80],
}

print(json.dumps(report, indent=2))

if missing_anchor_targets:
    print("\nCHECK missing anchor targets:", ", ".join(missing_anchor_targets))

if not impact_css_checks["wrap_safety_present"]:
    print("\nCHECK impact cards need wrap-safety CSS repair.")

bad_important = [
    cls for cls, info in important_class_report.items()
    if info["in_html"] and not info["in_css"]
]
if bad_important:
    print("\nCHECK important HTML classes missing CSS rules:", ", ".join(bad_important))
