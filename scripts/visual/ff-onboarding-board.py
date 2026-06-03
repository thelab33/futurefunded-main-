#!/usr/bin/env python3
from ff_page_board import run_page_board

raise SystemExit(
    run_page_board(
        default_slug="onboarding",
        default_title="FutureFunded Onboarding Screenshot Board",
        default_path="/platform/onboarding",
        default_port=8767,
    )
)
