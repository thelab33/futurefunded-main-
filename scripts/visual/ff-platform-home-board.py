#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="platform-home",
        default_title="FutureFunded Platform Home Screenshot Board",
        default_path="/platform/",
        default_port=8770,
    )
)
