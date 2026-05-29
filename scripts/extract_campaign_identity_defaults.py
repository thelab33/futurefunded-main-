#!/usr/bin/env python3
"""
FutureFunded Phase 2 White-Label Extraction

Goal:
- Create one central env-aware identity source.
- Replace common active demo literals with identity helper references where safe.
- Keep the default demo campaign working.
- Add an audit that treats config defaults as allowed, but flags active templates/routes.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

IDENTITY = ROOT / "apps/web/app/services/campaign_identity.py"
ENV_EXAMPLE = ROOT / ".env.example"
AUDIT = ROOT / "scripts/final_campaign_identity_extraction_audit.py"

FILES_TO_PATCH = [
    ROOT / "apps/web/app/services/campaign_profile.py",
    ROOT / "apps/web/app/services/platform_context.py",
    ROOT / "apps/web/app/blueprints/platform/services.py",
    ROOT / "apps/web/app/blueprints/campaign/services.py",
    ROOT / "apps/web/app/blueprints/campaign/routes.py",
]

TEMPLATES_TO_PATCH = [
    ROOT / "apps/web/app/templates/campaign_premium.html",
    ROOT / "apps/web/app/templates/campaign/index.html",
    ROOT / "apps/web/app/templates/campaign/_hero.html",
    ROOT / "apps/web/app/templates/campaign/_checkout_sheet.html",
    ROOT / "apps/web/app/templates/campaign/_modals.html",
]

IDENTITY_TEXT = '''"""FutureFunded campaign identity defaults.

This module is the single fallback source for the flagship/demo campaign identity.
Production/white-label campaigns should override these values from DB/config/profile
data, but active templates and services should not scatter hard-coded demo strings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignIdentityDefaults:
    brand_name: str
    team_name: str
    campaign_slug: str
    location: str
    campaign_name: str
    campaign_title: str
    campaign_accent: str
    public_base_url: str
    sponsor_contact_email: str
    team_logo_url: str


def _env(name: str, fallback: str = "") -> str:
    return (os.environ.get(name) or fallback).strip()


def get_campaign_identity_defaults() -> CampaignIdentityDefaults:
    team_name = _env("FF_DEFAULT_TEAM_NAME", "Connect ATX Elite")
    campaign_slug = _env("FF_DEFAULT_CAMPAIGN_SLUG", "connect-atx-elite")

    return CampaignIdentityDefaults(
        brand_name=_env("FF_DEFAULT_BRAND_NAME", "FutureFunded"),
        team_name=team_name,
        campaign_slug=campaign_slug,
        location=_env("FF_DEFAULT_LOCATION", "Austin, TX"),
        campaign_name=_env("FF_DEFAULT_CAMPAIGN_NAME", f"{team_name} Season Fund"),
        campaign_title=_env("FF_DEFAULT_CAMPAIGN_TITLE", "Fuel the season. Fund the future."),
        campaign_accent=_env("FF_DEFAULT_CAMPAIGN_ACCENT", "Back the athletes."),
        public_base_url=_env("PUBLIC_BASE_URL", _env("FF_PUBLIC_BASE_URL", "http://127.0.0.1:5000")),
        sponsor_contact_email=_env("FF_SPONSOR_CONTACT_EMAIL", "sponsor@futurefunded.com"),
        team_logo_url=_env("FF_DEFAULT_TEAM_LOGO_URL", "/static/images/teams/connect-atx-elite/logo.jpg"),
    )


DEFAULT_CAMPAIGN_IDENTITY = get_campaign_identity_defaults()
DEFAULT_BRAND_NAME = DEFAULT_CAMPAIGN_IDENTITY.brand_name
DEFAULT_TEAM_NAME = DEFAULT_CAMPAIGN_IDENTITY.team_name
DEFAULT_CAMPAIGN_SLUG = DEFAULT_CAMPAIGN_IDENTITY.campaign_slug
DEFAULT_LOCATION = DEFAULT_CAMPAIGN_IDENTITY.location
DEFAULT_CAMPAIGN_NAME = DEFAULT_CAMPAIGN_IDENTITY.campaign_name
DEFAULT_CAMPAIGN_TITLE = DEFAULT_CAMPAIGN_IDENTITY.campaign_title
DEFAULT_CAMPAIGN_ACCENT = DEFAULT_CAMPAIGN_IDENTITY.campaign_accent
DEFAULT_PUBLIC_BASE_URL = DEFAULT_CAMPAIGN_IDENTITY.public_base_url
DEFAULT_SPONSOR_CONTACT_EMAIL = DEFAULT_CAMPAIGN_IDENTITY.sponsor_contact_email
DEFAULT_TEAM_LOGO_URL = DEFAULT_CAMPAIGN_IDENTITY.team_logo_url
'''

AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit Phase 2 white-label identity extraction."""

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
    "apps/web/app/services/campaign_identity.py",
    "apps/web/app/config/team_campaigns.py",
    ".env.example",
}

SCAN_PREFIXES = (
    "apps/web/app/templates/",
    "apps/web/app/blueprints/",
    "apps/web/app/services/",
)


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def warn(message: str) -> None:
    WARN.append(message)
    print(f"⚠️  {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


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
    print("\nFutureFunded campaign identity extraction audit")
    print("=" * 72)

    identity = ROOT / "apps/web/app/services/campaign_identity.py"
    identity_text = read(identity)

    required_identity_terms = [
        "CampaignIdentityDefaults",
        "get_campaign_identity_defaults",
        "FF_DEFAULT_TEAM_NAME",
        "FF_DEFAULT_CAMPAIGN_SLUG",
        "FF_DEFAULT_LOCATION",
        "DEFAULT_CAMPAIGN_IDENTITY",
    ]

    for term in required_identity_terms:
        ok(f"identity module contains {term}") if term in identity_text else fail(f"identity module missing {term}")

    try:
        from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_IDENTITY
        ok(f"identity import works: {DEFAULT_CAMPAIGN_IDENTITY.team_name}")
    except Exception as exc:
        fail(f"identity import failed: {exc}")

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
        ok("default demo campaign still renders team name") if "Connect ATX Elite" in html else fail("default demo team name missing from rendered campaign")
        ok("provider readiness stays off public campaign") if "data-ff-provider-readiness" not in html else fail("provider readiness leaked onto public campaign")

        platform = client.get("/platform/", follow_redirects=False)
        ok("/platform/ loads") if platform.status_code == 200 else fail(f"/platform/ HTTP {platform.status_code}")

    matches: dict[str, list[str]] = {term: [] for term in TERMS}

    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue

        text = read(path)
        rel = path.relative_to(ROOT).as_posix()

        for term in TERMS:
            if term in text:
                matches[term].append(rel)

    for term, files in matches.items():
        if files:
            warn(f"active literal still present outside approved default sources: {term} ({len(files)} file(s))")
            for rel in files[:20]:
                print(f"   • {rel}")
        else:
            ok(f"active literal extracted from scanned surfaces: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ CAMPAIGN IDENTITY EXTRACTION AUDIT COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-identity-extract-{stamp}")
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


def ensure_import(text: str, import_line: str) -> str:
    if import_line in text:
        return text

    # Insert after future import if present, otherwise before first non-comment import area.
    future = "from __future__ import annotations"
    if future in text:
        return text.replace(future, future + "\n" + import_line, 1)

    return import_line + "\n" + text


def patch_python_file(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing python file: {path}")
        return

    text = read(path)
    original = text

    replacements = {
        '"Connect ATX Elite"': "DEFAULT_TEAM_NAME",
        "'Connect ATX Elite'": "DEFAULT_TEAM_NAME",
        '"connect-atx-elite"': "DEFAULT_CAMPAIGN_SLUG",
        "'connect-atx-elite'": "DEFAULT_CAMPAIGN_SLUG",
        '"Austin, TX"': "DEFAULT_LOCATION",
        "'Austin, TX'": "DEFAULT_LOCATION",
        '"sponsor@futurefunded.com"': "DEFAULT_SPONSOR_CONTACT_EMAIL",
        "'sponsor@futurefunded.com'": "DEFAULT_SPONSOR_CONTACT_EMAIL",
    }

    changed_literal = False
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            changed_literal = True

    if changed_literal:
        text = ensure_import(
            text,
            "from apps.web.app.services.campaign_identity import DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME",
        )

    if text != original:
        write(path, text)
    else:
        print(f"No python identity literals changed: {path}")


def patch_template_file(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing template: {path}")
        return

    text = read(path)
    original = text

    # Jinja templates already expose Flask config as `config`. Use env/config-driven
    # fallbacks instead of hardcoded active demo values.
    replacements = {
        "default('Connect ATX Elite', true)": "default(config.get('FF_DEFAULT_TEAM_NAME'), true)|default('Connect ATX Elite', true)",
        'default("Connect ATX Elite", true)': 'default(config.get("FF_DEFAULT_TEAM_NAME"), true)|default("Connect ATX Elite", true)',
        "else 'Connect ATX Elite'": "else config.get('FF_DEFAULT_TEAM_NAME', 'Connect ATX Elite')",
        'else "Connect ATX Elite"': 'else config.get("FF_DEFAULT_TEAM_NAME", "Connect ATX Elite")',
        "else 'connect-atx-elite'": "else config.get('FF_DEFAULT_CAMPAIGN_SLUG', 'connect-atx-elite')",
        'else "connect-atx-elite"': 'else config.get("FF_DEFAULT_CAMPAIGN_SLUG", "connect-atx-elite")',
        "default('connect-atx-elite', true)": "default(config.get('FF_DEFAULT_CAMPAIGN_SLUG'), true)|default('connect-atx-elite', true)",
        'default("connect-atx-elite", true)': 'default(config.get("FF_DEFAULT_CAMPAIGN_SLUG"), true)|default("connect-atx-elite", true)',
        "default('Austin, TX', true)": "default(config.get('FF_DEFAULT_LOCATION'), true)|default('Austin, TX', true)",
        'default("Austin, TX", true)': 'default(config.get("FF_DEFAULT_LOCATION"), true)|default("Austin, TX", true)',
        "mailto:sponsor@futurefunded.com": "mailto:{{ config.get('FF_SPONSOR_CONTACT_EMAIL', 'sponsor@futurefunded.com') }}",
    }

    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)

    if text != original:
        write(path, text)
    else:
        print(f"No template identity fallbacks changed: {path}")


def patch_env_example() -> None:
    text = read(ENV_EXAMPLE)
    original = text

    additions = {
        "FF_DEFAULT_CAMPAIGN_NAME=": "FF_DEFAULT_CAMPAIGN_NAME=\n",
        "FF_DEFAULT_CAMPAIGN_TITLE=": "FF_DEFAULT_CAMPAIGN_TITLE=\n",
        "FF_DEFAULT_CAMPAIGN_ACCENT=": "FF_DEFAULT_CAMPAIGN_ACCENT=\n",
        "FF_DEFAULT_TEAM_LOGO_URL=": "FF_DEFAULT_TEAM_LOGO_URL=\n",
    }

    if "FF_DEFAULT_CAMPAIGN_NAME=" not in text:
        anchor = "FF_DEFAULT_LOCATION=\n"
        insert = (
            "FF_DEFAULT_CAMPAIGN_NAME=\n"
            "FF_DEFAULT_CAMPAIGN_TITLE=\n"
            "FF_DEFAULT_CAMPAIGN_ACCENT=\n"
            "FF_DEFAULT_TEAM_LOGO_URL=\n"
        )
        if anchor in text:
            text = text.replace(anchor, anchor + insert, 1)
        else:
            text = text.rstrip() + "\n" + insert

    if text != original:
        write(ENV_EXAMPLE, text)
    else:
        print("No .env.example identity additions needed.")


def main() -> int:
    print("\nFutureFunded extract active campaign identity into defaults")
    print("=" * 72)

    write(IDENTITY, IDENTITY_TEXT)
    patch_env_example()

    for path in FILES_TO_PATCH:
        patch_python_file(path)

    for path in TEMPLATES_TO_PATCH:
        patch_template_file(path)

    write(AUDIT, AUDIT_TEXT)
    AUDIT.chmod(0o755)

    print("\n✅ Campaign identity extraction patch complete.")
    print("\nNext run:")
    print("  python scripts/final_campaign_identity_extraction_audit.py")
    print("  python scripts/final_provider_readiness_polish_audit.py")
    print("  python scripts/final_white_label_active_surface_audit.py")
    print("  python scripts/final_faq_minimal_audit.py")
    print("  python scripts/final_campaign_momentum_visual_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
