#!/usr/bin/env bash
set -Eeuo pipefail
PY_BIN="${PY_BIN:-.venv/bin/python}"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="$(command -v python)"
fi
"$PY_BIN" scripts/release/ff_production_ops_gate.py "$@"
