#!/usr/bin/env python3
"""FutureFunded sponsor stage form security audit."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.web.app import create_app  # noqa: E402


PASS: list[str] = []
FAIL: list[str] = []


def ok(message: str) -> None:
    PASS.append(message)
    print(f"✅ {message}")


def fail(message: str) -> None:
    FAIL.append(message)
    print(f"❌ {message}")


def main() -> int:
    print("\nFutureFunded sponsor stage form security audit")
    print("=" * 72)

    token = os.getenv("FF_OPERATOR_ACCESS_TOKEN", "").strip()
    if not token:
        fail("FF_OPERATOR_ACCESS_TOKEN missing")
        return 1

    app = create_app()
    client = app.test_client()

    res = client.get(f"/platform/dashboard?token={token}", follow_redirects=False)

    if res.status_code == 200:
        ok("dashboard loads with operator token")
    else:
        fail(f"dashboard returned HTTP {res.status_code}")
        return 1

    html = res.get_data(as_text=True)

    stage_actions = re.findall(r'action="([^"]*/sponsors/lead/[^"]*/stage[^"]*)"', html)

    if stage_actions:
        ok(f"dashboard renders {len(stage_actions)} sponsor stage form action(s)")
    else:
        fail("dashboard renders no sponsor stage form actions")

    leaking = [action for action in stage_actions if "token=" in action or "operator_token=" in action]

    if leaking:
        fail(f"stage form action leaks operator token in URL: {leaking[0]}")
    else:
        ok("stage form actions do not include operator token query params")

    if 'name="token"' in html:
        ok("stage form includes hidden operator token field")
    else:
        fail("stage form missing hidden operator token field")

    route_text = (REPO_ROOT / "apps/web/app/blueprints/sponsors/routes.py").read_text(errors="ignore")

    if 'request.form.get("token")' in route_text or "request.form.get('token')" in route_text:
        ok("stage update route accepts token from POST body")
    else:
        fail("stage update route does not read token from POST body")

    print("\n" + "=" * 72)
    print(f"PASS: {len(PASS)}  FAIL: {len(FAIL)}")

    if FAIL:
        print("\nFailures:")
        for item in FAIL:
            print(f"❌ {item}")
        return 1

    print("\n✅ SPONSOR STAGE FORM SECURITY AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
