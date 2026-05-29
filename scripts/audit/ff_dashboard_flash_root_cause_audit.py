from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()

TARGETS = [
    "apps/web/app/templates/platform/dashboard.html",
    "apps/web/app/templates/platform/dashboard_locked.html",
    "apps/web/app/static/js/ff-dashboard-protected-exec.js",
    "apps/web/app/static/css/ff-dashboard-protected-exec.css",
    "apps/web/app/static/css/dashboard-modern.css",
    "apps/web/app/static/css/ff-dashboard-final.css",
]

PATTERNS = {
    "launch assistant markers": [
        "ff_dashboard_launch_assistant",
        "ff-dashboard-launch-assistant",
        "ff-launchAssistant",
        "Ready-to-send campaign scripts",
        "Launch assistant",
    ],
    "js layout mutation": [
        "insertAdjacentElement",
        "appendChild",
        "prepend",
        "closest(\".ff-dashboardModern\")",
        "dataset.ffDashboardExecAssistant",
        "ff-dashboardExecutiveAssistant",
    ],
    "boot / no-flash": [
        "ff-dashboard-hardboot",
        "ff-dashboard-protected-booting",
        "ff-dashboard-protected-exec-ready",
        "FF_DASHBOARD_HARD_NOFLASH",
        "FF_DASHBOARD_NO_FLASH",
    ],
    "dashboard css/js links": [
        "ff-dashboard-protected-exec.css",
        "ff-dashboard-protected-exec.js",
        "dashboard-modern.css",
        "ff-dashboard-final.css",
        "ff-launch-completion.css",
    ],
    "duplicate dashboard templates": [
        "data-ff-page=\"platform-dashboard\"",
        "data-ff-page=\"platform-dashboard-locked\"",
        "ff-dashboardModernBody",
        "dashboard_locked",
    ],
}

def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

def line_hits(path: Path, needles: list[str]) -> list[tuple[int, str, str]]:
    text = read(path)
    hits = []
    for idx, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        for needle in needles:
            if needle.lower() in low:
                hits.append((idx, needle, line.strip()))
    return hits

def print_section(title: str):
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)

print_section("FutureFunded dashboard flash root-cause audit")

print("\nRepo:", ROOT)
print("\nTracked target files:")
for item in TARGETS:
    path = ROOT / item
    print(f"{'OK ' if path.exists() else 'MISS'} {item}")

print_section("1) Dashboard asset order in dashboard.html")

dash = ROOT / "apps/web/app/templates/platform/dashboard.html"
dash_text = read(dash)
for token in [
    "FF_DASHBOARD_HARD_NOFLASH",
    "FF_DASHBOARD_NO_FLASH_BOOT",
    "ff.css",
    "dashboard-modern.css",
    "ff-launch-completion.css",
    "ff-dashboard-final.css",
    "ff-dashboard-protected-exec.css",
    "ff-dashboard-protected-exec.js",
    "</head>",
    "</body>",
]:
    pos = dash_text.find(token)
    print(f"{token:42} {pos if pos >= 0 else 'NOT FOUND'}")

print_section("2) Launch Assistant appears where in server HTML?")

for idx, line in enumerate(dash_text.splitlines(), start=1):
    if any(s.lower() in line.lower() for s in ["ff_dashboard_launch_assistant", "ff-dashboard-launch-assistant", "Ready-to-send campaign scripts", "ff-launchAssistant"]):
        print(f"{rel(dash)}:{idx}: {line.strip()}")

print_section("3) JS is still moving layout after first paint?")

js = ROOT / "apps/web/app/static/js/ff-dashboard-protected-exec.js"
for idx, needle, line in line_hits(js, PATTERNS["js layout mutation"]):
    print(f"{rel(js)}:{idx}: [{needle}] {line}")

print_section("4) Boot/no-flash class consistency")

for path_str in TARGETS:
    path = ROOT / path_str
    if not path.exists():
        continue
    hits = line_hits(path, PATTERNS["boot / no-flash"])
    if hits:
        print(f"\n{rel(path)}")
        for idx, needle, line in hits:
            print(f"  L{idx}: [{needle}] {line}")

print_section("5) Count dashboard executive asset links/includes")

for path_str in TARGETS:
    path = ROOT / path_str
    text = read(path)
    if not text:
        continue
    for asset in ["ff-dashboard-protected-exec.css", "ff-dashboard-protected-exec.js", "ff-dashboard-final.css", "ff-launch-completion.css"]:
        count = text.count(asset)
        if count:
            print(f"{rel(path)}: {asset} count={count}")

print_section("6) Search all templates for dashboard/assistant duplicates")

for path in sorted((ROOT / "apps/web/app/templates").rglob("*.html")):
    text = read(path)
    if any(x in text for x in [
        "ff_dashboard_launch_assistant",
        "ff-dashboard-launch-assistant",
        "ff-launchAssistant",
        "data-ff-page=\"platform-dashboard\"",
        "data-ff-page=\"platform-dashboard-locked\"",
    ]):
        print(f"\n{rel(path)}")
        for idx, line in enumerate(text.splitlines(), start=1):
            if any(x.lower() in line.lower() for x in [
                "ff_dashboard_launch_assistant",
                "ff-dashboard-launch-assistant",
                "ff-launchAssistant",
                "data-ff-page=\"platform-dashboard\"",
                "data-ff-page=\"platform-dashboard-locked\"",
                "dashboard_locked",
            ]):
                print(f"  L{idx}: {line.strip()}")

print_section("7) Search all static CSS/JS for old dashboard layout authority")

for base in [ROOT / "apps/web/app/static/css", ROOT / "apps/web/app/static/js"]:
    if not base.exists():
        continue
    for path in sorted(base.rglob("*")):
        if path.suffix not in {".css", ".js"}:
            continue
        text = read(path)
        if any(x in text for x in [
            "ff-dashboardModern__hero",
            "ff-launchAssistant",
            "ff-dashboardExecutiveAssistant",
            "ff-dashboard-hardboot",
            "ff-dashboard-protected-exec-ready",
        ]):
            print(f"\n{rel(path)}")
            for idx, line in enumerate(text.splitlines(), start=1):
                if any(x.lower() in line.lower() for x in [
                    "ff-dashboardmodern__hero",
                    "ff-launchassistant",
                    "ff-dashboardexecutiveassistant",
                    "ff-dashboard-hardboot",
                    "ff-dashboard-protected-exec-ready",
                    "insertadjacentelement",
                    "appendchild",
                ]):
                    print(f"  L{idx}: {line.strip()}")

print_section("8) Likely root-cause verdict")

mutation_terms = ["insertAdjacentElement", "appendChild", "prepend"]
has_mutation = any(term in read(js) for term in mutation_terms)
assistant_in_template = any(s in dash_text for s in ["ff_dashboard_launch_assistant", "ff-dashboard-launch-assistant", "Ready-to-send campaign scripts"])
has_hardboot = "ff-dashboard-hardboot" in dash_text

if has_mutation and assistant_in_template:
    print("LIKELY: Server renders Launch Assistant in old/original position, then JS moves/groups it after paint.")
    print("FIX: Stop doing layout reparenting in JS. Render Launch Assistant in final position directly in dashboard.html.")
elif has_mutation:
    print("LIKELY: JS still mutates dashboard layout after paint.")
    print("FIX: move final ordering into template/CSS; keep JS only for copy buttons/interactions.")
elif assistant_in_template:
    print("LIKELY: Template renders assistant before final CSS contract is available or in wrong location.")
    print("FIX: move include/markup to final server location and use CSS-only layout.")
else:
    print("No obvious Launch Assistant server/JS conflict found. Need Playwright frame capture next.")

if has_hardboot:
    print("NOTE: hardboot exists, but if flash persists it is either inserted too late, cleared too early, or browser tab reuse is showing previous page content.")
else:
    print("NOTE: hardboot marker not found in dashboard.html.")

print("\nNext best fix if verdict says JS mutation:")
print("  Make dashboard.html the single layout authority.")
print("  Delete assistant reparenting/grouping from ff-dashboard-protected-exec.js.")
print("  Keep JS only for copy-to-clipboard and dashboard interactions.")
