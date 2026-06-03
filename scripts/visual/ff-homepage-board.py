#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="homepage",
        default_title="FutureFunded Homepage Screenshot Board",
        default_path="/platform/",
        default_port=8765,
    )
)
