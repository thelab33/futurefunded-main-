#!/usr/bin/env python3
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
