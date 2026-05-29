from pathlib import Path
import re
import json

ROOT = Path(".")
template = ROOT / "apps/web/app/templates/campaign/index.html"

html = template.read_text(encoding="utf-8", errors="replace")

css_refs = re.findall(r"filename='css/([^']+)'|filename=\"css/([^\"]+)\"", html)
js_refs = re.findall(r"filename='js/([^']+)'|filename=\"js/([^\"]+)\"", html)

css = [a or b for a, b in css_refs]
js = [a or b for a, b in js_refs]

includes = re.findall(r'{%\s*include\s+[\'"]([^\'"]+)[\'"]', html)
data_hooks = sorted(set(re.findall(r'data-ff-[a-zA-Z0-9_-]+', html)))
classes = sorted(set(re.findall(r'class="([^"]+)"', html)))

class_tokens = sorted(set(
    token
    for class_attr in classes
    for token in class_attr.split()
    if token.startswith("ff-")
))

report = {
    "template": str(template),
    "css": css,
    "js": js,
    "includes": includes,
    "dataHookCount": len(data_hooks),
    "dataHooks": data_hooks,
    "ffClassCount": len(class_tokens),
    "ffClasses": class_tokens,
}

out = ROOT / "docs/release-proof/campaign-asset-map-latest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")

print(json.dumps({
    "css": css,
    "js": js,
    "includes": includes,
    "dataHookCount": len(data_hooks),
    "ffClassCount": len(class_tokens),
    "written": str(out),
}, indent=2))
