#!/usr/bin/env python3
from pathlib import Path
import json
import re

ROOT = Path(".")
templates = {
    "platform_home": "apps/web/app/templates/platform/index.html",
    "campaign": "apps/web/app/templates/campaign/index.html",
    "onboarding": "apps/web/app/templates/platform/onboarding.html",
    "dashboard": "apps/web/app/templates/platform/dashboard.html",
    "dashboard_locked": "apps/web/app/templates/platform/dashboard_locked.html",
    "login": "apps/web/app/templates/platform/login.html",
}

def refs(text, kind):
    """Find url_for static refs and hardcoded /static refs."""
    found = []
    found.extend(re.findall(r"filename=['\"]" + kind + r"/([^'\"]+)['\"]", text))
    found.extend(re.findall(r"/static/" + kind + r"/([^?'\"]+)", text))
    return found

report = {}

for name, rel in templates.items():
    p = ROOT / rel
    if not p.exists():
        report[name] = {"exists": False, "path": rel}
        continue

    text = p.read_text(encoding="utf-8", errors="replace")
    css = refs(text, "css")
    js = refs(text, "js")
    includes = re.findall(r"{%\s*include\s+['\"]([^'\"]+)['\"]", text)

    report[name] = {
        "exists": True,
        "path": rel,
        "cssCount": len(css),
        "css": css,
        "jsCount": len(js),
        "js": js,
        "includes": includes,
        "hasBundleCss": any("bundle" in x for x in css),
    }

out = ROOT / "docs/release-proof/surface-stylesheet-map-latest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps(report, indent=2))
