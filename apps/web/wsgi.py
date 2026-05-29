from __future__ import annotations

import os

from app import create_app


def _clean(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    return value.strip() or default


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _config_object() -> str | None:
    value = _clean(os.getenv("FUTUREFUNDED_CONFIG"))
    return value or None


def build_app():
    return create_app(_config_object())


app = build_app()
application = app


def main() -> None:
    host = _clean(os.getenv("FLASK_RUN_HOST"), "127.0.0.1")
    port = _as_int(os.getenv("FLASK_RUN_PORT"), 5000)
    debug = _as_bool(os.getenv("FLASK_DEBUG"), False)

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
