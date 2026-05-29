import sys
from pathlib import Path

ROOT = Path("apps/web/app/templates")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


files = [
    p
    for p in ROOT.rglob("*.html")
    if ".bak." not in p.name and not p.name.endswith(".orig") and not p.name.endswith("~")
]

site_base = ROOT / "_base/site_base.html"
campaign_base = ROOT / "_base/campaign_base.html"
platform_base = ROOT / "_base/platform_base.html"

problems = []

for p in files:
    text = read(p)
    rel = p.relative_to(ROOT).as_posix()

    if rel != "_base/site_base.html" and "include_site_ff_assets = true" in text:
        problems.append(f"{rel}: include_site_ff_assets must not be true outside site_base")

    if (
        rel
        not in {
            "_base/campaign_base.html",
            "_base/platform_base.html",
            "_base/site_base.html",
        }
        and '{% extends "_base/site_base.html" %}' in text
    ):
        problems.append(f"{rel}: concrete templates must not extend site_base directly")

    if rel == "_base/campaign_base.html":
        for bad in [
            'name="viewport"',
            'name="format-detection"',
            'name="referrer"',
            'name="color-scheme"',
        ]:
            if bad in text:
                problems.append(f"{rel}: duplicate root meta still present -> {bad}")

    if rel in {"_base/campaign_base.html", "_base/platform_base.html"}:
        if "{% set include_site_ff_assets = false %}" not in text:
            problems.append(f"{rel}: missing include_site_ff_assets = false")

if not site_base.exists():
    problems.append("_base/site_base.html missing")
if not campaign_base.exists():
    problems.append("_base/campaign_base.html missing")
if not platform_base.exists():
    problems.append("_base/platform_base.html missing")

if problems:
    print("TEMPLATE CONTRACT: FAIL\n")
    for item in problems:
        print(f"- {item}")
    sys.exit(1)

print("TEMPLATE CONTRACT: PASS")
