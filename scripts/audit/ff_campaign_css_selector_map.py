from pathlib import Path
import json
import re

ROOT = Path(".")
template = ROOT / "apps/web/app/templates/campaign/index.html"

css_files = [
    "ff.css",
    "ff.checkout.css",
    "campaign.css",
    "ff-launch-completion.css",
    "ff-campaign-enterprise.css",
    "ff-fortune500-final.css",
    "ff-campaign-final-compression.css",
    "campaign.authority.css",
]

html = template.read_text(encoding="utf-8", errors="replace")

class_tokens = sorted(set(
    token
    for attr in re.findall(r'class="([^"]+)"', html)
    for token in attr.split()
    if token.startswith("ff-")
))

data_hooks = sorted(set(re.findall(r'data-ff-[a-zA-Z0-9_-]+', html)))

def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def selector_blocks(css: str):
    css = strip_comments(css)
    blocks = []
    for m in re.finditer(r"([^{}]+)\{", css):
        raw = m.group(1).strip()
        if not raw or raw.startswith("@"):
            continue
        selectors = [s.strip() for s in raw.split(",") if s.strip()]
        blocks.extend(selectors)
    return blocks

report = {
    "template": str(template),
    "campaignClassCount": len(class_tokens),
    "campaignDataHookCount": len(data_hooks),
    "cssFiles": [],
}

for name in css_files:
    path = ROOT / "apps/web/app/static/css" / name
    if not path.exists():
        report["cssFiles"].append({
            "file": name,
            "exists": False,
        })
        continue

    css = path.read_text(encoding="utf-8", errors="replace")
    selectors = selector_blocks(css)

    matched_classes = sorted({
        cls for cls in class_tokens
        if f".{cls}" in css
    })

    matched_hooks = sorted({
        hook for hook in data_hooks
        if f"[{hook}" in css or hook in css
    })

    body_scoped = len(re.findall(r"body\.ff-campaignBody|html\[data-ff-page=['\"]campaign['\"]\]|\.ff-campaign", css))
    global_body = len(re.findall(r"(^|\n)\s*body\s*[,{]", css))
    platform_terms = len(re.findall(r"ff-platform|ff-dashboard|ff-onboard|ff-login", css))
    checkout_terms = len(re.findall(r"ff-checkout|ff-embeddedCheckout|ff-payment", css))

    report["cssFiles"].append({
        "file": name,
        "exists": True,
        "bytes": len(css.encode("utf-8")),
        "lines": css.count("\n") + 1,
        "selectorCountApprox": len(selectors),
        "matchedCampaignClasses": len(matched_classes),
        "matchedCampaignHooks": len(matched_hooks),
        "bodyCampaignScopedSignals": body_scoped,
        "globalBodySelectorSignals": global_body,
        "nonCampaignSurfaceSignals": platform_terms,
        "checkoutSignals": checkout_terms,
        "topMatchedClasses": matched_classes[:50],
        "matchedHooks": matched_hooks[:50],
    })

out = ROOT / "docs/release-proof/campaign-css-selector-map-latest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps({
    "written": str(out),
    "campaignClassCount": report["campaignClassCount"],
    "campaignDataHookCount": report["campaignDataHookCount"],
    "files": [
        {
            "file": f["file"],
            "exists": f.get("exists"),
            "lines": f.get("lines"),
            "matchedCampaignClasses": f.get("matchedCampaignClasses"),
            "matchedCampaignHooks": f.get("matchedCampaignHooks"),
            "nonCampaignSurfaceSignals": f.get("nonCampaignSurfaceSignals"),
            "checkoutSignals": f.get("checkoutSignals"),
        }
        for f in report["cssFiles"]
    ],
}, indent=2))
