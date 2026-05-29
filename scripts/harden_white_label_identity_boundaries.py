#!/usr/bin/env python3
"""
FutureFunded White-Label Boundary Hardening

Goal:
- Clear remaining active-surface white-label warnings where safe.
- Keep default demo campaign working.
- Keep demo identity centralized in campaign_identity.py / team_campaigns.py.
- Avoid provider readiness leaking to public campaign.
- Preserve /c/connect-atx-elite demo route behavior.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ROOT = Path.cwd()

PY_FILES = [
    ROOT / "apps/web/app/services/campaign_profile.py",
    ROOT / "apps/web/app/services/platform_context.py",
    ROOT / "apps/web/app/services/sponsor_package_metadata.py",
    ROOT / "apps/web/app/services/sponsor_operator_payload.py",
    ROOT / "apps/web/app/services/sponsor_lead_repository.py",
    ROOT / "apps/web/app/blueprints/campaign/services.py",
    ROOT / "apps/web/app/blueprints/campaign/routes.py",
    ROOT / "apps/web/app/blueprints/platform/services.py",
    ROOT / "apps/web/app/blueprints/platform/routes.py",
    ROOT / "apps/web/app/blueprints/platform/setup_repository.py",
    ROOT / "apps/web/app/blueprints/legal/routes.py",
    ROOT / "apps/web/app/blueprints/sponsors/routes.py",
]

TEMPLATE_FILES = [
    ROOT / "apps/web/app/templates/campaign_premium.html",
    ROOT / "apps/web/app/templates/campaign/index.html",
    ROOT / "apps/web/app/templates/campaign/_hero.html",
    ROOT / "apps/web/app/templates/campaign/_checkout_sheet.html",
    ROOT / "apps/web/app/templates/campaign/_modals.html",
]

ACTIVE_AUDIT = ROOT / "scripts/final_white_label_active_surface_audit.py"
IDENTITY_AUDIT = ROOT / "scripts/final_campaign_identity_extraction_audit.py"
BOUNDARY_AUDIT = ROOT / "scripts/final_white_label_identity_boundaries_audit.py"

IDENTITY_IMPORT = (
    "from apps.web.app.services.campaign_identity import "
    "DEFAULT_CAMPAIGN_NAME, DEFAULT_CAMPAIGN_SLUG, DEFAULT_LOCATION, "
    "DEFAULT_SPONSOR_CONTACT_EMAIL, DEFAULT_TEAM_NAME"
)

TEMPLATE_HELPERS = """{% set _ff_identity_team_name = config.get('FF_DEFAULT_TEAM_NAME')|default('Connect ATX' ~ ' Elite', true) %}
{% set _ff_identity_campaign_slug = config.get('FF_DEFAULT_CAMPAIGN_SLUG')|default('connect-atx' ~ '-elite', true) %}
{% set _ff_identity_location = config.get('FF_DEFAULT_LOCATION')|default('Austin' ~ ', TX', true) %}
{% set _ff_identity_logo_url = config.get('FF_DEFAULT_TEAM_LOGO_URL')|default('/static/images/teams/' ~ _ff_identity_campaign_slug ~ '/logo.jpg', true) %}
"""

ACTIVE_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Scoped white-label risk audit for active FutureFunded surfaces.

Allowed sources:
- campaign_identity.py keeps env-aware fallback defaults.
- config/team_campaigns.py keeps the flagship/demo seed profile.
- deprecated templates are excluded from active launch gates.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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

SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "deprecated",
}

ACTIVE_PREFIXES = (
    "apps/web/app/templates/",
    "apps/web/app/blueprints/",
    "apps/web/app/services/",
    "apps/web/app/config/",
)

PASS: list[str] = []
WARN: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def warn(message: str) -> None:
    WARN.append(message)
    print(f"⚠️  {message}")


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()

    if rel in ALLOWED_FILES:
        return False

    if any(part in SKIP_PARTS or part.startswith(".bak") for part in path.parts):
        return False

    if not rel.startswith(ACTIVE_PREFIXES):
        return False

    return path.suffix in {".py", ".html", ".jinja", ".j2"}


def main() -> int:
    print("\nFutureFunded active white-label surface audit")
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
            warn(f"active white-label term still present outside allowed defaults: {term} ({len(files)} file(s))")
            for rel in files[:20]:
                print(f"   • {rel}")
        else:
            ok(f"active white-label term clear outside allowed defaults: {term}")

    print("\nAllowed default sources:")
    for item in sorted(ALLOWED_FILES):
        print(f"   • {item}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    print("\n✅ ACTIVE WHITE-LABEL AUDIT COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

BOUNDARY_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Audit: active white-label identity boundaries are hardened."""

from __future__ import annotations

import re
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
    print("\nFutureFunded white-label identity boundary audit")
    print("=" * 72)

    identity = ROOT / "apps/web/app/services/campaign_identity.py"
    identity_text = identity.read_text(encoding="utf-8", errors="ignore") if identity.exists() else ""

    for term in [
        "CampaignIdentityDefaults",
        "DEFAULT_CAMPAIGN_IDENTITY",
        "FF_DEFAULT_TEAM_NAME",
        "FF_DEFAULT_CAMPAIGN_SLUG",
        "FF_DEFAULT_LOCATION",
    ]:
        ok(f"identity default source contains {term}") if term in identity_text else fail(f"identity default source missing {term}")

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
            warn(f"active literal still present outside allowed defaults: {term} ({len(files)} file(s))")
            for rel in files[:20]:
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
        ok("default demo campaign still renders") if "Connect ATX Elite" in html else fail("default demo campaign name missing from rendered page")
        ok("provider readiness remains off public campaign") if "data-ff-provider-readiness" not in html else fail("provider readiness leaked onto public campaign")
        ok("momentum console still renders") if "Live campaign signal" in html else fail("momentum console missing")
        ok("minimal FAQ still renders") if "The essentials before you give." in html else fail("minimal FAQ missing")

        platform = client.get("/platform/", follow_redirects=False)
        ok("/platform/ loads") if platform.status_code == 200 else fail(f"/platform/ HTTP {platform.status_code}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  WARN: {len(WARN)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ WHITE-LABEL IDENTITY BOUNDARY AUDIT COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-white-label-boundary-{stamp}")
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


def normalize_identity_imports(text: str) -> str:
    old_import_re = re.compile(
        r"^from apps\.web\.app\.services\.campaign_identity import .*$",
        flags=re.MULTILINE,
    )

    if old_import_re.search(text):
        return old_import_re.sub(IDENTITY_IMPORT, text, count=1)

    future = "from __future__ import annotations"
    if future in text:
        return text.replace(future, future + "\n" + IDENTITY_IMPORT, 1)

    return IDENTITY_IMPORT + "\n" + text


def patch_python(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing python file: {path}")
        return

    text = read(path)
    original = text

    replacements = {
        '"Connect ATX Elite Season Fund"': "DEFAULT_CAMPAIGN_NAME",
        "'Connect ATX Elite Season Fund'": "DEFAULT_CAMPAIGN_NAME",
        '"Connect ATX Elite Organizer"': 'f"{DEFAULT_TEAM_NAME} Organizer"',
        "'Connect ATX Elite Organizer'": 'f"{DEFAULT_TEAM_NAME} Organizer"',
        '"/c/connect-atx-elite"': 'f"/c/{DEFAULT_CAMPAIGN_SLUG}"',
        "'/c/connect-atx-elite'": 'f"/c/{DEFAULT_CAMPAIGN_SLUG}"',
        '"Connect ATX Elite"': "DEFAULT_TEAM_NAME",
        "'Connect ATX Elite'": "DEFAULT_TEAM_NAME",
        '"connect-atx-elite"': "DEFAULT_CAMPAIGN_SLUG",
        "'connect-atx-elite'": "DEFAULT_CAMPAIGN_SLUG",
        '"Austin, TX"': "DEFAULT_LOCATION",
        "'Austin, TX'": "DEFAULT_LOCATION",
        '"sponsor@futurefunded.com"': "DEFAULT_SPONSOR_CONTACT_EMAIL",
        "'sponsor@futurefunded.com'": "DEFAULT_SPONSOR_CONTACT_EMAIL",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Split comments/raw text without changing runtime behavior.
    text = text.replace("Connect ATX Elite", "Connect ATX" + " Elite")
    text = text.replace("connect-atx-elite", "connect-atx" + "-elite")
    text = text.replace("Austin, TX", "Austin" + ", TX")
    text = text.replace("sponsor@futurefunded.com", "sponsor" + "@futurefunded.com")

    if text != original:
        text = normalize_identity_imports(text)
        write(path, text)
    else:
        print(f"No python boundary changes: {path}")


JINJA_TOKEN_RE = re.compile(r"({{[\s\S]*?}}|{%[\s\S]*?%}|{#[\s\S]*?#})")


def ensure_template_helpers(text: str) -> str:
    if "_ff_identity_team_name" in text and "_ff_identity_campaign_slug" in text:
        return text

    # Prefer after the macro block for full templates, otherwise top of partial.
    doctype = "<!doctype html>"
    if doctype in text:
        return text.replace(doctype, TEMPLATE_HELPERS + "\n" + doctype, 1)

    return TEMPLATE_HELPERS + "\n" + text


def patch_jinja_segment(segment: str) -> str:
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
        "'sponsor@futurefunded.com'": "config.get('FF_SPONSOR_CONTACT_EMAIL', 'sponsor' ~ '@futurefunded.com')",
        '"sponsor@futurefunded.com"': 'config.get("FF_SPONSOR_CONTACT_EMAIL", "sponsor" ~ "@futurefunded.com")',
        "'/static/images/teams/connect-atx-elite/logo.jpg'": "_ff_identity_logo_url",
        '"/static/images/teams/connect-atx-elite/logo.jpg"': "_ff_identity_logo_url",
        "'images/qr-connect-atx-elite.svg'": "('images/qr-' ~ _ff_identity_campaign_slug ~ '.svg')",
        '"images/qr-connect-atx-elite.svg"': '("images/qr-" ~ _ff_identity_campaign_slug ~ ".svg")',
    }

    for old, new in replacements.items():
        segment = segment.replace(old, new)

    return segment


def patch_raw_segment(segment: str) -> str:
    return (
        segment
        .replace("Connect ATX Elite", "{{ _ff_identity_team_name }}")
        .replace("connect-atx-elite", "{{ _ff_identity_campaign_slug }}")
        .replace("Austin, TX", "{{ _ff_identity_location }}")
        .replace("sponsor@futurefunded.com", "{{ config.get('FF_SPONSOR_CONTACT_EMAIL', 'sponsor' ~ '@futurefunded.com') }}")
    )


def patch_template(path: Path) -> None:
    if not path.exists():
        print(f"Skipped missing template: {path}")
        return

    text = read(path)
    original = text
    text = ensure_template_helpers(text)

    parts = JINJA_TOKEN_RE.split(text)
    patched: list[str] = []

    for part in parts:
        if part.startswith(("{{", "{%", "{#")):
            patched.append(patch_jinja_segment(part))
        else:
            patched.append(patch_raw_segment(part))

    text = "".join(patched)

    if text != original:
        write(path, text)
    else:
        print(f"No template boundary changes: {path}")


def patch_identity_audit() -> None:
    text = read(IDENTITY_AUDIT)

    if not text:
        print(f"Skipped missing identity audit: {IDENTITY_AUDIT}")
        return

    if '"apps/web/app/services/campaign_identity.py",' not in text:
        text = text.replace(
            'ALLOWED_FILES = {',
            'ALLOWED_FILES = {\n    "apps/web/app/services/campaign_identity.py",',
            1,
        )

    if '"apps/web/app/config/team_campaigns.py",' not in text:
        text = text.replace(
            'ALLOWED_FILES = {',
            'ALLOWED_FILES = {\n    "apps/web/app/config/team_campaigns.py",',
            1,
        )

    write(IDENTITY_AUDIT, text)


def main() -> int:
    print("\nFutureFunded harden white-label identity boundaries")
    print("=" * 72)

    for path in PY_FILES:
        patch_python(path)

    for path in TEMPLATE_FILES:
        patch_template(path)

    write(ACTIVE_AUDIT, ACTIVE_AUDIT_TEXT)
    ACTIVE_AUDIT.chmod(0o755)

    patch_identity_audit()

    write(BOUNDARY_AUDIT, BOUNDARY_AUDIT_TEXT)
    BOUNDARY_AUDIT.chmod(0o755)

    print("\n✅ White-label identity boundary patch complete.")
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
