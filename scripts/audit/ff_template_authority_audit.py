from pathlib import Path
import ast
import re
import subprocess
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path.cwd()
TEMPLATE_DIR = ROOT / "apps/web/app/templates"
PY_DIRS = [ROOT / "apps/web/app"]

URLS = [
    "http://127.0.0.1:5000/platform/",
    "http://127.0.0.1:5000/platform/login",
    "http://127.0.0.1:5000/platform/onboarding",
    "http://127.0.0.1:5000/platform/dashboard",
    "http://127.0.0.1:5000/c/connect-atx-elite",
]

WATCH_TEMPLATES = [
    "_base/site_base.html",
    "platform/index.html",
    "platform/login.html",
    "platform/dashboard.html",
    "platform/onboarding.html",
    "campaign/index.html",
    "campaign_premium.html",
]

EXTENDS_RE = re.compile(r'{%\s*extends\s+[\'"]([^\'"]+)[\'"]\s*%}')
INCLUDE_RE = re.compile(r'{%\s*include\s+[\'"]([^\'"]+)[\'"]')
CINEMATIC_RE = re.compile(r'ff\.cinematic\.css|ff-cinematic\.js|data-ff-cinematic-asset')


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def template_report():
    print("\n=== Template inheritance + cinematic ownership ===")
    for name in WATCH_TEMPLATES:
        path = TEMPLATE_DIR / name
        if not path.exists():
            print(f"MISS {name}")
            continue

        text = read(path)
        extends = EXTENDS_RE.findall(text)
        includes = INCLUDE_RE.findall(text)
        cinematic_count = len(CINEMATIC_RE.findall(text))

        print(f"\n{name}")
        print(f"  extends: {extends[0] if extends else 'NONE / standalone'}")
        print(f"  includes: {', '.join(includes[:8]) if includes else 'none'}")
        print(f"  cinematic markers in file: {cinematic_count}")


def route_template_scan():
    print("\n=== Python render_template() references ===")
    found = []

    for base in PY_DIRS:
        for path in base.rglob("*.py"):
            text = read(path)
            if "render_template" not in text:
                continue

            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue

                func = node.func
                is_render = (
                    isinstance(func, ast.Name) and func.id == "render_template"
                ) or (
                    isinstance(func, ast.Attribute) and func.attr == "render_template"
                )

                if not is_render or not node.args:
                    continue

                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    found.append((path, node.lineno, first.value))

    if not found:
        print("No static render_template('...') references found. Routes may use dynamic template names.")
        return

    for path, line, template in sorted(found, key=lambda x: (str(x[0]), x[1])):
        flag = "  <== WATCH" if template in WATCH_TEMPLATES else ""
        print(f"{rel(path)}:{line} -> {template}{flag}")


def grep_template_usage():
    print("\n=== Raw references to site_base / watched templates ===")
    needles = ["_base/site_base.html", "site_base.html"] + WATCH_TEMPLATES
    for needle in needles:
        try:
            out = subprocess.check_output(
                ["grep", "-RIn", needle, "apps/web/app", "--exclude-dir=__pycache__"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except subprocess.CalledProcessError:
            out = ""

        if out:
            print(f"\n[{needle}]")
            print(out)


def fetch(url: str) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "FutureFunded-template-authority-audit"})
    try:
        with urlopen(req, timeout=8) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except URLError as e:
        return 0, str(e)


def rendered_asset_counts():
    print("\n=== Rendered route asset counts ===")
    for url in URLS:
        status, html = fetch(url)
        css = html.count("ff.cinematic.css")
        js = html.count("ff-cinematic.js")
        site_base_hint = html.count("_base/site_base.html")
        print(f"{url:<58} status={status:<3} css={css} js={js} site_base_hint={site_base_hint}")


def main():
    print("FutureFunded Template Authority Audit")
    print(f"Repo: {ROOT}")

    template_report()
    route_template_scan()
    grep_template_usage()
    rendered_asset_counts()

    print("\n=== Read ===")
    print("If watched templates show 'NONE / standalone', they own their document shell.")
    print("If rendered routes show css=1 js=1, the browser is not double-loading the cinematic layer.")
    print("If _base/site_base.html has no route/template inheritance references, it can be restored or left harmless.")

if __name__ == "__main__":
    main()
