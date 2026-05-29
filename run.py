#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import time
import webbrowser
from pathlib import Path

from flask import request


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "nogit"


def _asset_version(env: str) -> str:
    explicit = os.getenv("FF_ASSET_V") or os.getenv("FF_BUILD_ID")
    if explicit:
        return explicit.strip()

    sha = _git_sha()

    if env == "production":
        return sha

    return f"dev-{sha}-{int(time.time())}"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _install_dev_cache_controls(app) -> None:
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def _ff_dev_no_cache(response):
        content_type = (response.headers.get("Content-Type") or "").lower()

        if (
            "text/html" in content_type
            or "text/css" in content_type
            or "javascript" in content_type
            or "application/json" in content_type
            or "image/svg+xml" in content_type
        ):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


def _install_asset_context(app, asset_version: str) -> None:
    app.config["FF_ASSET_V"] = asset_version
    app.config["FF_BUILD_ID"] = asset_version

    @app.context_processor
    def _ff_asset_context():
        override = request.args.get("css_v") or request.args.get("v")
        version = override or asset_version

        return {
            "_asset_v": version,
            "_checkout_asset_v": version,
            "asset_version": version,
            "ff_asset_v": version,
        }


def create_runtime_app():
    # Load base env first so FF_ENV / APP_ENV / FLASK_ENV values inside .env
    # can actually control the runtime profile.
    _load_dotenv(Path(".env"))

    env = (
        os.getenv("FF_ENV")
        or os.getenv("APP_ENV")
        or os.getenv("FLASK_ENV")
        or os.getenv("ENV")
        or "development"
    ).strip().lower()

    _load_dotenv(Path(f".env.{env}"))

    if env != "production":
        _load_dotenv(Path(".env.local"))
        _load_dotenv(Path(".env.local.stripe-test"))

    asset_version = _asset_version(env)

    os.environ.setdefault("FLASK_ENV", env)
    os.environ.setdefault("APP_ENV", env)
    os.environ.setdefault("ENV", env)
    os.environ["FF_ASSET_V"] = asset_version
    os.environ["FF_BUILD_ID"] = asset_version
    os.environ.setdefault("FF_VERSION", asset_version)

    from apps.web.app import create_app

    app = create_app()

    _install_asset_context(app, asset_version)

    if env != "production" or app.debug:
        _install_dev_cache_controls(app)

    print()
    print("🚀 FutureFunded launcher")
    print(f"ENV:        {env}")
    print(f"ASSET_V:    {asset_version}")
    print(f"PUBLIC_URL: {os.getenv('PUBLIC_BASE_URL') or os.getenv('FF_PUBLIC_BASE_URL') or 'local'}")
    print()

    return app


app = create_runtime_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FutureFunded web app")
    parser.add_argument("--host", default=os.getenv("WEB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("WEB_PORT", "5000")))
    parser.add_argument("--debug", action="store_true", default=_truthy(os.getenv("FLASK_DEBUG", "1")))
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    if args.open:
        webbrowser.open_new_tab(f"http://127.0.0.1:{args.port}/c/connect-atx-elite")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug,
    )


if __name__ == "__main__":
    main()
