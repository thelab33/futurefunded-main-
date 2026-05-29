from __future__ import annotations

import os

from app.main import create_app
from apps.api.routes.web_sponsors import router as sponsors_router


def build_app():
    app = create_app()

    # Contract-test/API parity route:
    # exposes GET /sponsors in the same ASGI app CI boots.
    if hasattr(app, "include_router"):
        app.include_router(sponsors_router)

    return app


app = build_app()
application = app


def main() -> None:
    import uvicorn

    host = os.getenv("API_RUN_HOST", os.getenv("UVICORN_HOST", "127.0.0.1")).strip() or "127.0.0.1"

    try:
        port = int(os.getenv("API_RUN_PORT", os.getenv("UVICORN_PORT", "8000")))
    except (TypeError, ValueError):
        port = 8000

    reload_enabled = os.getenv("API_RELOAD", os.getenv("UVICORN_RELOAD", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    uvicorn.run("asgi:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
