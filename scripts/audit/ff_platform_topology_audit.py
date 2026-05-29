from pathlib import Path
import re
import json
from datetime import datetime, timezone

ROOT = Path.cwd()

FILES = {
    "global_css": ROOT / "apps/web/app/static/css/ff.css",
    "platform_home_css": ROOT / "apps/web/app/static/css/platform-home.css",
    "platform_home_template": ROOT / "apps/web/app/templates/platform/index.html",
    "campaign_template": ROOT / "apps/web/app/templates/campaign/index.html",
}

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def line_of(text: str, needle: str) -> int | None:
    idx = text.find(needle)
    return None if idx < 0 else text[:idx].count("\n") + 1

def marker_scan(text: str):
    patterns = [
        r"/\*\s*===\s*(.*?)\s*START\s*===\s*\*/",
        r"/\*\s*(FF_[A-Z0-9_]+)",
        r"Version:\s*([^\n]+)",
        r"Purpose:\s*([^\n]+)",
    ]
    markers = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            markers.append({
                "line": text[:m.start()].count("\n") + 1,
                "marker": m.group(1).strip()
            })
    return sorted(markers, key=lambda x: x["line"])

def hrefs(text: str):
    return re.findall(r'href=["\']([^"\']+\.(?:css|js)[^"\']*)["\']', text)

def scripts(text: str):
    return re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', text)

def class_counts(text: str):
    counts = {}
    for cls in re.findall(r"\.ff-[A-Za-z0-9_-]+", text):
        counts[cls] = counts.get(cls, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:35]

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "files": {},
    "contracts": {},
}

for name, path in FILES.items():
    text = read(path)
    report["files"][name] = {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "lines": len(text.splitlines()),
        "bytes": len(text.encode("utf-8")),
        "important_count": text.count("!important"),
        "markers": marker_scan(text)[:80],
        "top_ff_selectors": class_counts(text),
    }

platform_template = read(FILES["platform_home_template"])
report["contracts"]["platform_home_template"] = {
    "css_links": hrefs(platform_template),
    "js_links": scripts(platform_template),
    "loads_ff_css": "css/ff.css" in platform_template,
    "loads_platform_home_css": "css/platform-home.css" in platform_template,
    "platform_home_css_after_ff_css": (
        line_of(platform_template, "css/ff.css") is not None
        and line_of(platform_template, "css/platform-home.css") is not None
        and line_of(platform_template, "css/platform-home.css") > line_of(platform_template, "css/ff.css")
    ),
    "data_contracts": sorted(set(re.findall(r"data-ff-[A-Za-z0-9_-]+", platform_template))),
}

campaign_template = read(FILES["campaign_template"])
report["contracts"]["campaign_template"] = {
    "loads_ff_css": "css/ff.css" in campaign_template,
    "loads_checkout_css": "ff.checkout.css" in campaign_template,
    "loads_campaign_js": "ff-campaign.js" in campaign_template,
    "critical_hooks": {
        "ffCampaignConfig": "ffCampaignConfig" in campaign_template,
        "data_ff_open_checkout": "data-ff-open-checkout" in campaign_template,
        "data_ff_payment_trigger": "data-ff-payment-trigger" in campaign_template,
    },
}

out = ROOT / "docs/release-proof/platform-topology-latest.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(f"Wrote {out}")
print("")
print("Platform CSS facts:")
ph = report["files"]["platform_home_css"]
print(f"- platform-home.css lines: {ph['lines']}")
print(f"- platform-home.css !important count: {ph['important_count']}")
print(f"- platform-home.css marker count: {len(ph['markers'])}")
print("")
print("Template load order:")
c = report["contracts"]["platform_home_template"]
print(f"- loads ff.css: {c['loads_ff_css']}")
print(f"- loads platform-home.css: {c['loads_platform_home_css']}")
print(f"- platform-home.css loads after ff.css: {c['platform_home_css_after_ff_css']}")
print("")
print("Top platform-home markers:")
for m in ph["markers"][:24]:
    print(f"  line {m['line']}: {m['marker']}")
