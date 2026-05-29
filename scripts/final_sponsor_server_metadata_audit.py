#!/usr/bin/env python3
"""FutureFunded sponsor server metadata audit."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app.services.sponsor_package_metadata import (  # noqa: E402
    resolve_sponsor_package_metadata,
    sponsor_packages_for_campaign,
)


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded sponsor server metadata audit")
    print("=" * 72)

    packages = sponsor_packages_for_campaign("connect-atx-elite")

    if len(packages) >= 3:
        ok(f"server can load {len(packages)} sponsor packages")
    else:
        fail(f"expected at least 3 sponsor packages, got {len(packages)}")

    expected = {
        "community": ("Community Partner", 300),
        "featured": ("Featured Sponsor", 750),
        "legacy": ("Legacy Sponsor", 1500),
    }

    for package_key, (expected_name, expected_amount) in expected.items():
        metadata = resolve_sponsor_package_metadata(
            {
                "package_key": package_key,
                "package_name": "Tampered Name",
                "package_amount": "1",
            },
            campaign_slug="connect-atx-elite",
        )

        if metadata["package_validated"] is True:
            ok(f"{package_key} validates against campaign profile")
        else:
            fail(f"{package_key} did not validate against campaign profile")

        if metadata["package_name"] == expected_name:
            ok(f"{package_key} normalized name = {expected_name}")
        else:
            fail(f"{package_key} name mismatch: {metadata['package_name']}")

        if metadata["package_amount"] == expected_amount:
            ok(f"{package_key} normalized amount = {expected_amount}")
        else:
            fail(f"{package_key} amount mismatch: {metadata['package_amount']}")

    fallback = resolve_sponsor_package_metadata(
        {
            "package_key": "unknown-package",
            "package_name": "Unknown Package",
            "package_amount": "999999",
        },
        campaign_slug="connect-atx-elite",
    )

    if fallback["package_validated"] is True:
        ok("unknown package safely falls back to campaign-profile package")
    else:
        fail("unknown package did not safely fall back to campaign-profile package")

    if fallback["package_amount"] != 999999:
        ok("tampered unknown package amount is not trusted")
    else:
        fail("tampered unknown package amount was trusted")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR SERVER METADATA AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
