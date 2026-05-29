from __future__ import annotations

import os
import subprocess
import time


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "nogit"


def resolve_asset_version() -> str:
    explicit = (
        os.getenv("FF_ASSET_V")
        or os.getenv("FF_BUILD_ID")
        or os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("VERCEL_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("SOURCE_VERSION")
    )

    if explicit:
        return explicit[:12]

    env = (
        os.getenv("FF_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("FLASK_ENV")
        or os.getenv("ENV")
        or "development"
    ).lower()

    sha = _git_sha()

    if env == "production":
        return sha

    return f"dev-{sha}-{int(time.time())}"
