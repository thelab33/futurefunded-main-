import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path.cwd()
WEB_ROOT = ROOT / "apps/web"
STATIC_ROOT = WEB_ROOT / "app/static"
TOKEN_FILE = Path("/tmp/ff_operator_token")

# Support both import styles used by the app.
sys.path.insert(0, str(ROOT.resolve()))
sys.path.insert(0, str(WEB_ROOT.resolve()))

from app import create_app

ROUTES = [
    {
        "name": "homepage",
        "path": "/platform/",
        "expected_status": 200,
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/ff.homepage-flagship.css",
        ],
        "must_contain": [
            "ff-home",
            "data-ff-home-root",
            "ff-homeConsole",
            "ff-homeCampaignPreview",
        ],
        "identity_any": ["futurefunded", "fundraising"],
    },
    {
        "name": "campaign",
        "path": "/c/connect-atx-elite",
        "expected_status": 200,
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/ff.campaign-polish.css",
        ],
        "must_contain": [
            "data-ff-page-root",
            "data-ff-open-checkout",
            "data-ff-open-sponsor",
            "data-ff-share",
            "data-ff-checkout-sheet",
            "data-ff-sponsor-modal",
            "ffConfig",
            "ffSelectors",
        ],
        "identity_any": ["connect atx", "campaign", "donate"],
    },
    {
        "name": "login",
        "path": "/platform/login",
        "expected_status": 200,
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/ff.operator-dashboard.css",
        ],
        "must_contain": [
            "data-ff-login-root",
            "data-ff-login-form",
            "data-ff-login-email",
            "data-ff-login-password",
        ],
        "identity_any": ["futurefunded", "login", "operator"],
    },
    {
        "name": "dashboard-authenticated",
        "path": "/platform/dashboard",
        "requires_operator_token": True,
        "expected_status": 200,
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/ff.operator-dashboard.css",
        ],
        "must_contain": [
            "data-ff-operator-root",
            "data-ff-ledger-url",
            "data-ff-events-url",
            "data-ff-offline-url",
            "data-ff-export-url",
            "data-ff-offline-donation-form",
            "data-ff-donations-table",
            "data-ff-sponsors-list",
        ],
        "identity_any": ["ledger", "donation", "operator", "campaign"],
    },
    {
        "name": "onboarding",
        "path": "/platform/onboarding",
        "expected_status": 200,
        "expected_css": [
            "apps/web/app/static/css/ff.css",
            "apps/web/app/static/css/ff.operator-dashboard.css",
        ],
        "must_contain_any": [
            "onboarding",
            "setup",
            "campaign",
            "sponsor",
        ],
        "identity_any": ["campaign", "setup", "sponsor", "onboarding"],
    },
]

link_re = re.compile(
    r"""<link\b[^>]*\bhref=["']([^"']+\.css(?:\?[^"']*)?)["'][^>]*>""",
    re.I,
)


def css_file_from_href(href: str):
    path = unquote(urlparse(href).path)
    if not path.startswith("/static/"):
        return None
    return str((STATIC_ROOT / path.replace("/static/", "", 1)).relative_to(ROOT))


def extract_css(html: str):
    out = []
    for href in link_re.findall(html):
        rel = css_file_from_href(href)
        if rel and rel not in out:
            out.append(rel)
    return out


def load_operator_token():
    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if token:
        return token

    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(errors="ignore").strip()
        if token:
            os.environ["FF_OPERATOR_ACCESS_TOKEN"] = token
            return token

    return ""


def assert_css_files_exist(page_name, css_files, errors):
    for item in css_files:
        if ".bak" in item:
            errors.append(f"{page_name}: loads backup CSS file {item}")
        if not (ROOT / item).exists():
            errors.append(f"{page_name}: missing CSS file {item}")


def main():
    token = load_operator_token()
    app = create_app()

    errors = []
    report = {}

    with app.test_client() as client:
        for spec in ROUTES:
            path = spec["path"]
            query_string = None

            if spec.get("requires_operator_token"):
                if not token:
                    errors.append(
                        f"{spec['name']}: missing /tmp/ff_operator_token or FF_OPERATOR_ACCESS_TOKEN"
                    )
                    continue
                query_string = {"operator_token": token}

            res = client.get(path, query_string=query_string)
            html = res.get_data(as_text=True)
            lower_html = html.lower()
            css = extract_css(html)

            report[spec["name"]] = {
                "path": path,
                "status": res.status_code,
                "css": css,
            }

            if res.status_code != spec["expected_status"]:
                errors.append(
                    f"{spec['name']}: expected status {spec['expected_status']}, got {res.status_code}"
                )

            if "expected_css" in spec and css != spec["expected_css"]:
                errors.append(
                    f"{spec['name']}: CSS mismatch. Expected {spec['expected_css']}, got {css}"
                )

            if "expected_css_any" in spec:
                if not any(item in css for item in spec["expected_css_any"]):
                    errors.append(
                        f"{spec['name']}: expected at least one known product CSS file, got {css}"
                    )

            assert_css_files_exist(spec["name"], css, errors)

            for token_item in spec.get("must_contain", []):
                if token_item not in html:
                    errors.append(f"{spec['name']}: missing HTML hook/content {token_item}")

            if "must_contain_any" in spec:
                if not any(item.lower() in lower_html for item in spec["must_contain_any"]):
                    errors.append(f"{spec['name']}: none of expected terms found")

            if "identity_any" in spec:
                if not any(item.lower() in lower_html for item in spec["identity_any"]):
                    errors.append(f"{spec['name']}: missing brand/product identity text")

    Path("product-page-smoke-report.json").write_text(json.dumps(report, indent=2))

    print("FutureFunded Product Page Smoke Test")
    print("=" * 44)

    for name, data in report.items():
        print(f"\n{name}: {data['status']} {data['path']}")
        for css in data["css"]:
            print(f"  - {css}")

    print("\nErrors:")
    if errors:
        for error in errors:
            print("FAIL:", error)
        raise SystemExit(1)

    print("  none")


if __name__ == "__main__":
    main()
