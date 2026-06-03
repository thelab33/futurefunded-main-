#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="homepage",
        default_title="FutureFunded Public Homepage Screenshot Board",
        default_path="/",
        default_port=8765,
    )
)
