from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import request, url_for


def _asset_fingerprint(app: Any, filename: str) -> str:
    """
    Returns a stable cache-busting fingerprint for a static asset.

    Example:
      css/ff.css -> 1715195432-98321

    This keeps clean page URLs working while still forcing browsers to fetch
    changed CSS/JS/image assets.
    """
    static_folder = Path(app.static_folder or "")
    asset_path = static_folder / filename

    try:
        stat = asset_path.stat()
    except OSError:
        fallback = (
            app.config.get("FF_ASSET_V")
            or app.config.get("FF_BUILD_ID")
            or app.config.get("FF_VERSION")
            or "dev"
        )
        return str(fallback)

    return f"{int(stat.st_mtime)}-{stat.st_size}"


def register_ff_asset_versioning(app: Any) -> None:
    """
    FutureFunded asset versioning.

    Clean route:
      /platform/

    Rendered asset:
      /static/css/ff.css?v=<actual-file-fingerprint>

    Result:
      no more manual ?css_v=... page URLs during normal use.
    """

    ff_css_v = _asset_fingerprint(app, "css/ff.css")
    home_css_v = _asset_fingerprint(app, "css/platform-home.css")
    checkout_css_v = _asset_fingerprint(app, "css/ff.checkout.css")

    app.config["FF_ASSET_V"] = ff_css_v
    app.config["FF_CAMPAIGN_CSS_REV"] = ff_css_v
    app.config["FF_PLATFORM_CSS_REV"] = f"{ff_css_v}-{home_css_v}"
    app.config["FF_CHECKOUT_CSS_REV"] = f"{ff_css_v}-{checkout_css_v}"

    if app.debug:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.context_processor
    def _ff_asset_context() -> dict[str, Any]:
        ff_css_v_live = _asset_fingerprint(app, "css/ff.css")
        home_css_v_live = _asset_fingerprint(app, "css/platform-home.css")
        checkout_css_v_live = _asset_fingerprint(app, "css/ff.checkout.css")

        platform_css_rev = f"{ff_css_v_live}-{home_css_v_live}"
        checkout_css_rev = f"{ff_css_v_live}-{checkout_css_v_live}"

        app.config["FF_ASSET_V"] = ff_css_v_live
        app.config["FF_CAMPAIGN_CSS_REV"] = ff_css_v_live
        app.config["FF_PLATFORM_CSS_REV"] = platform_css_rev
        app.config["FF_CHECKOUT_CSS_REV"] = checkout_css_rev

        def asset_version(filename: str = "css/ff.css") -> str:
            return _asset_fingerprint(app, filename)

        def static_asset_url(filename: str, **kwargs: Any) -> str:
            version = kwargs.pop("v", None) or asset_version(filename)
            return url_for("static", filename=filename, v=version, **kwargs)

        return {
            "asset_version": asset_version,
            "static_asset_url": static_asset_url,
            "ff_asset_v": ff_css_v_live,
            "asset_v": ff_css_v_live,
            "campaign_css_rev": ff_css_v_live,
            "platform_css_rev": platform_css_rev,
            "checkout_css_rev": checkout_css_rev,
        }

    @app.after_request
    def _ff_dev_static_no_cache(response):
        if app.debug:
            static_url_path = app.static_url_path or "/static"
            if request.path.startswith(static_url_path):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        return response
