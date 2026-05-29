from __future__ import annotations

import multiprocessing
import os
from typing import Any


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _as_int(
    value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None
) -> int:
    try:
        parsed = int(str(value).strip())
    except (AttributeError, TypeError, ValueError):
        parsed = default

    if minimum is not None and parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _default_workers() -> int:
    cpu_count = multiprocessing.cpu_count()
    return max(2, min((cpu_count * 2) + 1, 4))


bind = _clean(os.getenv("GUNICORN_BIND"), f"0.0.0.0:{_clean(os.getenv('PORT'), '5000')}")

workers = _as_int(
    os.getenv("WEB_CONCURRENCY", os.getenv("GUNICORN_WORKERS")),
    _default_workers(),
    minimum=1,
    maximum=8,
)

worker_class = _clean(os.getenv("GUNICORN_WORKER_CLASS"), "gthread")
threads = _as_int(os.getenv("GUNICORN_THREADS"), 4, minimum=1, maximum=16)

timeout = _as_int(os.getenv("GUNICORN_TIMEOUT"), 120, minimum=1)
graceful_timeout = _as_int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT"), 30, minimum=1)
keepalive = _as_int(os.getenv("GUNICORN_KEEPALIVE"), 5, minimum=1)

max_requests = _as_int(os.getenv("GUNICORN_MAX_REQUESTS"), 1000, minimum=0)
max_requests_jitter = _as_int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER"), 100, minimum=0)

worker_tmp_dir = _clean(os.getenv("GUNICORN_WORKER_TMP_DIR"), "/dev/shm")

accesslog = _clean(os.getenv("GUNICORN_ACCESS_LOG"), "-")
errorlog = _clean(os.getenv("GUNICORN_ERROR_LOG"), "-")
loglevel = _clean(os.getenv("GUNICORN_LOG_LEVEL"), "info").lower()

capture_output = _as_bool(os.getenv("GUNICORN_CAPTURE_OUTPUT"), True)
preload_app = _as_bool(os.getenv("GUNICORN_PRELOAD_APP"), False)

forwarded_allow_ips = _clean(
    os.getenv("GUNICORN_FORWARDED_ALLOW_IPS"),
    "*",
)

secure_scheme_headers = {
    "X-Forwarded-Proto": "https",
    "X-Forwarded-Port": "443",
    "X-Forwarded-Ssl": "on",
}

access_log_format = _clean(
    os.getenv("GUNICORN_ACCESS_LOG_FORMAT"),
    '%(h)s %(l)s %(u)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" req_id=%({x-request-id}i)s',
)
