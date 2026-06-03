#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="campaign",
        default_title="FutureFunded Campaign Screenshot Board",
        default_path="/c/connect-atx-elite",
        default_port=8766,
    )
)
