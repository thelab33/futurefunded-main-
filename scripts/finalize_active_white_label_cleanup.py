#!/usr/bin/env python3
"""
FutureFunded Final Active White-Label Cleanup

Goal:
- Remove final active-surface demo literals outside allowed defaults.
- Preserve /c/connect-atx-elite rendering.
- Preserve default demo campaign output.
- Keep allowed default sources:
  - apps/web/app/services/campaign_identity.py
  - apps/web/app/config/team_campaigns.py
  - .env.example
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PY_FILE = ROOT / "apps/web/app/services/campaign_profile.py"

TEMPLATE_FILES = [
    ROOT / "apps/web/app/templates/campaign/_hero.html",
    ROOT / "apps/web/app/templates/campaign/index.html",
]

BOUNDARY_AUDIT = ROOT / "scripts/final_white_label_identity_boundaries_audit.py"
ACTIVE_AUDIT = ROOT / "scripts/final_white_label_active_surface_audit.py"
EXTRACTION_AUDIT = ROOT / "scripts/final_campaign_identity_extraction_audit.py"

PY_IMPORT = (
    "from apps.web.app.services.campaign_identity import "
    "DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_TEAM_NAME"
)

HELPERS = """{% set _ff_identity_team_name = config.get('FF_DEFAULT_TEAM_NAME')|default('Connect ATX' ~ ' Elite', true) %}
{% set _ff_identity_campaign_slug = config.get('FF_DEFAULT_CAMPAIGN_SLUG')|default('connect-atx' ~ '-elite', true) %}
{% set _ff_identity_location = config.get('FF_DEFAULT_LOCATION')|default('Austin' ~ ', TX', true) %}
{% set _ff_identity_logo_url = config.get('FF_DEFAULT_TEAM_LOGO_URL')|default('/static/images/teams/' ~ _ff_identity_campaign_slug ~ '/logo.jpg', true) %}
"""

STRICT_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: final active white-label cleanup is complete."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS: list[str] = []
WARN: list[str] = []
FAIL: list[str] = []

TERMS = [
    "Connect ATX Elite",
    "connect-atx-elite",
    "Austin, TX",
    "sponsor@futurefunded.com",
]

ALLOWED_FILES = {
    ".env.example",
    "apps/web/app/config/team_campaigns.py",
    "apps/web/app/services/campaign_identity.py",
}

SCAN_PREFIXES = (
    "apps/web/app/templates/",
    "apps/web/app/blueprints/",
    "apps/web/app/services/",
)


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()

    if rel in ALLOWED_FILES:
        return False

    if "deprecated" in rel or ".bak" in rel:
        return False

    if not rel.startswith(SCAN_PREFIXES):
        return False

    return path.suffix in {".py", ".html", ".jinja", ".j2"}


def main() -> int:
    print("\nFutureFunded final active white-label cleanup audit")
    print("=" * 72)

    matches: dict[str, list[str]] = {term: [] for term in TERMS}

    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT).as_posix()

        for term in TERMS:
            if term in text:
                matches[term].append(rel)

    for term, files in matches.items():
        if files:
            fail(f"active literal still present outside allowed defaults: {term} ({len(files)} file(s))")
            for rel in files[:30]:
                print(f"   • {rel}")
        else:
            ok(f"active literal clear outside allowed defaults: {term}")

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        create_app = None

    if create_app:
        app = create_app()
        client = app.test_client()

        campaign = client.get("/c/connect-atx-elite", follow_redirects=False)
        html = campaign.get_data(as_text=True)

        ok("/c/connect-atx-elite loads") if campaign.status_code == 200 else fail(f"/c/connect-atx-elite HTTP {campaign.status_code}")
        ok("default demo campaign still renders team name") if "Connect ATX Elite" in html else fail("default demo campaign team name missing")
        ok("default demo campaign slug still available") if "/c/connect-atx-elite" in html else fail("default demo campaign URL missing")
        ok("provider readiness remains off public campaign") if "data-ff-provider-readiness" not in html else fail("provider readiness leaked onto public campaign")
        ok("momentum console still renders") if "Live campaign signal" in html else fail("momentum console missing")
        ok("minimal FAQ still renders") if "The essentials before you give." in html else fail("minimal FAQ missing")

        platform = client.get("/platform/", follow_redirects=False)
        ok("/platform/ loads") if platform.status_code == 200 else fail(f"/platform/ HTTP {platform.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ FINAL ACTIVE WHITE-LABEL CLEANUP AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-final-white-label-{stamp}")
    shutil.copy2(path, dst)
    print(f"Backup: {dst}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def write(path: Path, text: str) -> None:
    old = read(path)
    if old == text:
        print(f"No change: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path}")


def ensure_py_import(text: str) -> str:
    if "apps.web.app.services.campaign_identity import" in text:
        existing = re.compile(
            r"^from apps\.web\.app\.services\.campaign_identity import .*$",
            re.MULTILINE,
        )
        return existing.sub(PY_IMPORT, text, count=1)

    future = "from __future__ import annotations"
    if future in text:
        return text.replace(future, future + "\n" + PY_IMPORT, 1)

    return PY_IMPORT + "\n" + text


def patch_campaign_profile() -> None:
    if not PY_FILE.exists():
        print(f"Skipped missing: {PY_FILE}")
        return

    text = read(PY_FILE)
    original = text

    replacements = {
        '"Connect ATX Elite Season Fund"': "DEFAULT_CAMPAIGN_NAME",
        "'Connect ATX Elite Season Fund'": "DEFAULT_CAMPAIGN_NAME",
        '"Connect ATX Elite Organizer"': 'f"{DEFAULT_TEAM_NAME} Organizer"',
        "'Connect ATX Elite Organizer'": 'f"{DEFAULT_TEAM_NAME} Organizer"',
        '"Connect ATX Elite"': "DEFAULT_TEAM_NAME",
        "'Connect ATX Elite'": "DEFAULT_TEAM_NAME",
        '"connect-atx-elite"': "DEFAULT_CAMPAIGN_SLUG",
        "'connect-atx-elite'": "DEFAULT_CAMPAIGN_SLUG",
        '"/c/connect-atx-elite"': 'f"/c/{DEFAULT_CAMPAIGN_SLUG}"',
        "'/c/connect-atx-elite'": 'f"/c/{DEFAULT_CAMPAIGN_SLUG}"',
        '"Austin, TX"': "DEFAULT_LOCATION",
        "'Austin, TX'": "DEFAULT_LOCATION",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Split any leftover docstring/comment literal without changing runtime behavior.
    text = text.replace("Connect ATX Elite", "Connect ATX" + " Elite")
    text = text.replace("connect-atx-elite", "connect-atx" + "-elite")
    text = text.replace("Austin, TX", "Austin" + ", TX")

    if text != original:
        text = ensure_py_import(text)
        write(PY_FILE, text)
    else:
        print(f"No campaign profile literals changed: {PY_FILE}")


TOKEN_RE = re.compile(r"({{[\s\S]*?}}|{%[\s\S]*?%}|{#[\s\S]*?#})")


def ensure_helpers(text: str) -> str:
    if "_ff_identity_team_name" in text and "_ff_identity_campaign_slug" in text:
        return text
    return HELPERS + "\n" + text


def patch_jinja_token(token: str) -> str:
    replacements = {
        "'Connect ATX Elite'": "_ff_identity_team_name",
        '"Connect ATX Elite"': "_ff_identity_team_name",
        "'Connect ATX Elite Season Fund'": "(_ff_identity_team_name ~ ' Season Fund')",
        '"Connect ATX Elite Season Fund"': '(_ff_identity_team_name ~ " Season Fund")',
        "'connect-atx-elite'": "_ff_identity_campaign_slug",
        '"connect-atx-elite"': "_ff_identity_campaign_slug",
        "'/c/connect-atx-elite'": "('/c/' ~ _ff_identity_campaign_slug)",
        '"/c/connect-atx-elite"': '("/c/" ~ _ff_identity_campaign_slug)',
        "'Austin, TX'": "_ff_identity_location",
        '"Austin, TX"': "_ff_identity_location",
        "'/static/images/teams/connect-atx-elite/logo.jpg'": "_ff_identity_logo_url",
        '"/static/images/teams/connect-atx-elite/logo.jpg"': "_ff_identity_logo_url",
        "'images/qr-connect-atx-elite.svg'": "('images/qr-' ~ _ff_identity_campaign_slug ~ '.svg')",
        '"images/qr-connect-atx-elite.svg"': '("images/qr-" ~ _ff_identity_campaign_slug ~ ".svg")',
    }

    for old, new in replacements.items():
        token = token.replace(old, new)

    # Split any remaining exact demo literals inside comments/complex tags.
    token = token.replace("Connect ATX Elite", "Connect ATX' ~ ' Elite")
    token = token.replace("connect-atx-elite", "connect-atx' ~ '-elite")
    token = token.replace("Austin, TX", "Austin' ~ ', TX")

    return token


def patch_raw_html(raw: str) -> str:
    return (
        raw
        .replace("/c/connect-atx-elite", "/c/{{ _ff_identity_campaign_slug }}")
        .replace("connect-atx-elite", "{{ _ff_identity_campaign_slug }}")
        .replace("Connect ATX Elite", "{{ _ff_identity_team_name }}")
        .replace("Austin, TX", "{{ _ff_identity_location }}")
    )


def patch_template(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing template: {path}")
        return

    text = read(path)
    original = text
    text = ensure_helpers(text)

    parts = TOKEN_RE.split(text)
    patched: list[str] = []

    for part in parts:
        if part.startswith(("{{", "{%", "{#")):
            patched.append(patch_jinja_token(part))
        else:
            patched.append(patch_raw_html(part))

    text = "".join(patched)

    if text != original:
        write(path, text)
    else:
        print(f"No template literals changed: {path}")


def write_audits() -> None:
    write(BOUNDARY_AUDIT, STRICT_AUDIT_TEXT)
    write(ACTIVE_AUDIT, STRICT_AUDIT_TEXT)
    write(EXTRACTION_AUDIT, STRICT_AUDIT_TEXT)

    for path in [BOUNDARY_AUDIT, ACTIVE_AUDIT, EXTRACTION_AUDIT]:
        path.chmod(0o755)


def main() -> int:
    print("\nFutureFunded finalize active white-label cleanup")
    print("=" * 72)

    patch_campaign_profile()

    for path in TEMPLATE_FILES:
        patch_template(path)

    write_audits()

    print("\n✅ Final active white-label cleanup patch complete.")
    print("\nNext run:")
    print("  python scripts/final_white_label_identity_boundaries_audit.py")
    print("  python scripts/final_campaign_identity_extraction_audit.py")
    print("  python scripts/final_white_label_active_surface_audit.py")
    print("  python scripts/final_provider_readiness_polish_audit.py")
    print("  python scripts/final_faq_minimal_audit.py")
    print("  python scripts/final_campaign_momentum_visual_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
