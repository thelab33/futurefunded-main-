from __future__ import annotations

import os
import sys

ROOT = os.getcwd()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from apps.web.wsgi import app  # type: ignore
except Exception as exc:
    print(f"FAIL: could not import apps.web.wsgi:app: {exc}")
    raise SystemExit(1)

print(f"OK: imported apps.web.wsgi:app -> {app!r}")
