#!/usr/bin/env python3
import os
from ff_page_board import run_page_board

token = os.environ.get("FF_DASHBOARD_TOKEN", "dev-operator-20260529123018")

raise SystemExit(
    run_page_board(
        default_slug="platform-dashboard",
        default_title="FutureFunded Platform Dashboard Screenshot Board",
        default_path=f"/platform/dashboard?access_token={token}",
        default_port=8772,
    )
)
