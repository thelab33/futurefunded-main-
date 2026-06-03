#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="platform-login",
        default_title="FutureFunded Platform Login Screenshot Board",
        default_path="/platform/login",
        default_port=8771,
    )
)
