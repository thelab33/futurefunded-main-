"""
FutureFunded lifecycle idempotency guard.

Prevents duplicate donor/sponsor lifecycle messages when:
- Stripe retries a webhook
- session-status is polled multiple times
- PayPal capture is retried
- sponsor lead submit is retried

This file stores a lightweight JSON ledger in instance/lifecycle-events.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


LEDGER_PATH = Path(os.getenv("FF_LIFECYCLE_LEDGER_PATH", "instance/lifecycle-events.json"))


def _disabled() -> bool:
    return str(os.getenv("FF_LIFECYCLE_DISABLE", "")).strip().lower() in {"1", "true", "yes", "on"}


def _load() -> dict[str, Any]:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER_PATH.exists():
        return {"events": {}}
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"events": {}}


def _save(data: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(LEDGER_PATH)


def lifecycle_key(kind: str, external_id: str | None, payload: Mapping[str, Any]) -> str:
    if external_id:
        return f"{kind}:{external_id}"

    for key in ("checkout_session_id", "session_id", "payment_intent", "order_id", "lead_id", "id"):
        value = payload.get(key)
        if value:
            return f"{kind}:{value}"

    fallback = "|".join(
        str(payload.get(k, ""))
        for k in ("campaign_slug", "email", "supporter_email", "sponsor_email", "amount_cents")
    )
    return f"{kind}:fallback:{fallback}"


def dispatch_once(
    *,
    kind: str,
    external_id: str | None,
    payload: Mapping[str, Any],
    dispatcher: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    key = lifecycle_key(kind, external_id, payload)

    if _disabled():
        return {
            "sent": False,
            "mode": "disabled",
            "key": key,
            "category": kind,
        }

    ledger = _load()
    events = ledger.setdefault("events", {})

    if key in events:
        return {
            "sent": False,
            "mode": "already_dispatched",
            "key": key,
            "category": kind,
            "first_dispatched_at": events[key].get("dispatched_at"),
            "result": events[key].get("result"),
        }

    result = dispatcher(payload)

    events[key] = {
        "kind": kind,
        "key": key,
        "external_id": external_id,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }

    _save(ledger)

    return {
        "sent": True,
        "mode": "dispatched",
        "key": key,
        "category": kind,
        "result": result,
    }
