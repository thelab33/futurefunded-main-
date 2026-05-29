#!/usr/bin/env python3
"""
FutureFunded public sponsor leak fix.

Fixes the remaining audit failure:
- Rendered campaign still contains "FutureFunded Public Sponsor"
- Keeps sponsor cards/forms intact
- Filters demo/test/audit sponsor names from the Campaign Momentum rail
- Adds a focused leak audit
"""

from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path.cwd()

PARTIAL = ROOT / "apps/web/app/templates/campaign/_campaign_momentum_bar.html"
OS_AUDIT = ROOT / "scripts/final_campaign_momentum_os_audit.py"
LEAK_AUDIT = ROOT / "scripts/final_campaign_public_sponsor_leak_audit.py"

BANNED_TERMS = [
    "FutureFunded Public Sponsor",
    "FutureFunded Public Sponsor ae7dbb3d",
    "ae7dbb3d",
    "demo sponsor",
    "test sponsor",
]

SAFE_PUBLIC_SPONSOR_BLOCK = r'''            {% if _ff_public_sponsors %}
              {% for sponsor in _ff_public_sponsors[:4] %}
                {% set _ff_sponsor_name = sponsor.business_name|default(sponsor.name|default('Community sponsor', true), true)|string|trim %}
                {% set _ff_sponsor_blob = (_ff_sponsor_name ~ ' ' ~ sponsor.id|default('', true) ~ ' ' ~ sponsor.lead_id|default('', true) ~ ' ' ~ sponsor.sponsor_id|default('', true))|lower %}
                {% if _ff_sponsor_name
                      and 'futurefunded public sponsor' not in _ff_sponsor_blob
                      and 'ae7dbb3d' not in _ff_sponsor_blob
                      and 'demo sponsor' not in _ff_sponsor_blob
                      and 'test sponsor' not in _ff_sponsor_blob %}
                  <span class="ff-momentum__item" data-ff-public-sponsor-safe>
                    <span class="ff-momentum__dot" aria-hidden="true"></span>
                    <strong>{{ _ff_sponsor_name }}</strong>
                    recognized through sponsor review
                  </span>
                {% endif %}
              {% endfor %}
            {% endif %}'''

LEAK_AUDIT_TEXT = r'''#!/usr/bin/env python3
"""Focused audit: no demo/test sponsor identity leaks on public campaign page."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded public sponsor leak audit")
    print("=" * 72)

    try:
        from apps.web.app import create_app
    except Exception as exc:
        fail(f"could not import create_app: {exc}")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get("/c/connect-atx-elite", follow_redirects=False)
    html = res.get_data(as_text=True)

    if res.status_code == 200:
        ok("/c/connect-atx-elite loads")
    else:
        fail(f"/c/connect-atx-elite HTTP {res.status_code}")

    required_terms = [
        "Campaign Momentum",
        "data-ff-momentum",
        "ff.momentum.js",
        "id=\"sponsor-form\"",
        "data-ff-sponsor-package-key-input",
        "data-ff-sponsor-package-name-input",
        "data-ff-sponsor-package-amount-input",
        "data-ff-sponsor-submit",
    ]

    for term in required_terms:
        if term in html:
            ok(f"required public contract present: {term}")
        else:
            fail(f"required public contract missing: {term}")

    banned_terms = [
        "FutureFunded Public Sponsor",
        "FutureFunded Public Sponsor ae7dbb3d",
        "ae7dbb3d",
        "Sponsor onboarding",
        "Ready to be recognized?",
        "Pick a package above or email the sponsor team",
        "Sponsors helping move this campaign forward",
    ]

    for term in banned_terms:
        if term not in html:
            ok(f"public campaign does not leak: {term}")
        else:
            fail(f"public campaign still leaks: {term}")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ PUBLIC SPONSOR LEAK AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = path.with_suffix(path.suffix + f".bak-public-sponsor-leak-{stamp}")
    shutil.copy2(path, dst)
    print(f"Backup: {dst}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str) -> None:
    old = read(path) if path.exists() else ""
    if old == text:
        print(f"No change: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path}")


def patch_momentum_partial() -> None:
    if not PARTIAL.exists():
        raise FileNotFoundError(f"Missing momentum partial: {PARTIAL}")

    text = read(PARTIAL)

    if "data-ff-public-sponsor-safe" in text:
        print("Momentum partial already has public sponsor sanitizer.")
        return

    pattern = re.compile(
        r'{%\s*if\s+_ff_public_sponsors\s*%}\s*'
        r'{%\s*for\s+sponsor\s+in\s+_ff_public_sponsors\[:4\]\s*%}'
        r'.*?'
        r'{%\s*endfor\s*%}\s*'
        r'{%\s*endif\s*%}',
        re.DOTALL,
    )

    patched, count = pattern.subn(SAFE_PUBLIC_SPONSOR_BLOCK, text, count=1)

    if count == 0:
        raise RuntimeError(
            "Could not find the _ff_public_sponsors loop in _campaign_momentum_bar.html. "
            "Open the partial and manually wrap the public sponsor loop with the banned-term guard."
        )

    write(PARTIAL, patched)


def patch_os_audit() -> None:
    if not OS_AUDIT.exists():
        print(f"Skipped missing audit: {OS_AUDIT}")
        return

    text = read(OS_AUDIT)

    if "ae7dbb3d" in text:
        print("OS audit already checks ae7dbb3d.")
        return

    text = text.replace(
        '"FutureFunded Public Sponsor",',
        '"FutureFunded Public Sponsor",\n'
        '            "FutureFunded Public Sponsor ae7dbb3d",\n'
        '            "ae7dbb3d",',
    )

    write(OS_AUDIT, text)


def write_leak_audit() -> None:
    write(LEAK_AUDIT, LEAK_AUDIT_TEXT)
    LEAK_AUDIT.chmod(0o755)


def source_scan() -> None:
    print("\nSource scan for banned public sponsor residue")
    print("-" * 72)

    skip_parts = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    allowed_suffixes = {".py", ".html", ".jinja", ".j2", ".js", ".css", ".json", ".md", ".txt"}

    matches: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if any(part in skip_parts for part in path.parts):
            continue

        if path.suffix not in allowed_suffixes:
            continue

        rel = path.relative_to(ROOT)

        if str(rel).startswith("scripts/fix_campaign_momentum_public_sponsor_leak.py"):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for term in BANNED_TERMS:
            if term in content:
                matches.append(f"{rel}: {term}")
                break

    if not matches:
        print("✅ no banned literal source residue found outside this patch")
        return

    print("⚠️ found banned literal(s) in source/audits. Review these:")
    for item in matches[:40]:
        print(f"   • {item}")


def main() -> int:
    print("\nFutureFunded public sponsor leak fix")
    print("=" * 72)

    patch_momentum_partial()
    patch_os_audit()
    write_leak_audit()
    source_scan()

    print("\n✅ Patch complete.")
    print("\nNext run:")
    print("  python scripts/final_campaign_public_sponsor_leak_audit.py")
    print("  python scripts/final_campaign_momentum_os_audit.py")
    print("  python scripts/final_sponsor_package_behavior_audit.py")
    print("  python scripts/final_campaign_profile_audit.py")
    print("  python scripts/final_platform_smoke.py")
    print("  python scripts/final_funnel_functional_audit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
