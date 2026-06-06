#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

# ============================================================================
# FutureFunded • Strict Fast Proof Wrapper
#
# Marker: FF_STRICT_FAST_PROOF_WRAPPER_V2_20260606
#
# Responsibilities:
# - resolves the local/private operator token without printing it
# - starts the local application only when health is unavailable
# - prevents overlapping proof executions
# - runs the canonical fast proof
# - validates the payment and visual-gate artifacts
# - optionally runs campaign modal stability
# - stores a timestamped, redacted execution record
#
# Usage:
#   bash scripts/demo/ff-fast-proof-strict.sh
#
# Optional:
#   FF_AUTO_START_SERVER=0 bash scripts/demo/ff-fast-proof-strict.sh
#   FF_REQUIRE_CLEAN_TREE=1 bash scripts/demo/ff-fast-proof-strict.sh
#   FF_INCLUDE_MODAL_STABILITY=1 bash scripts/demo/ff-fast-proof-strict.sh
#   FF_INCLUDE_CTA_PROOF=1 bash scripts/demo/ff-fast-proof-strict.sh
# ============================================================================

readonly ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1
  pwd -P
)"

cd "$ROOT"

readonly FAST_PROOF="$ROOT/scripts/demo/ff-fast-proof.sh"
readonly MODAL_GATE="$ROOT/scripts/release/ff_campaign_modal_stability_gate.mjs"

FF_BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
FF_BASE_URL="${FF_BASE_URL%/}"

FF_AUTO_START_SERVER="${FF_AUTO_START_SERVER:-1}"
FF_REQUIRE_CLEAN_TREE="${FF_REQUIRE_CLEAN_TREE:-0}"
FF_INCLUDE_MODAL_STABILITY="${FF_INCLUDE_MODAL_STABILITY:-0}"
FF_ALLOW_LOCAL_DEV_TOKEN_FALLBACK="${FF_ALLOW_LOCAL_DEV_TOKEN_FALLBACK:-1}"

readonly FF_BASE_URL
readonly FF_AUTO_START_SERVER
readonly FF_REQUIRE_CLEAN_TREE
readonly FF_INCLUDE_MODAL_STABILITY
readonly FF_ALLOW_LOCAL_DEV_TOKEN_FALLBACK

readonly STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
readonly START_EPOCH="$(date +%s)"
readonly OUT_ROOT="$ROOT/audit_outputs/demo-proof"
readonly OUT="$OUT_ROOT/strict-$STAMP"
readonly RUN_LOG="$OUT/strict-fast-proof.log"
readonly SUMMARY="$OUT/summary.txt"
readonly REPORT="$ROOT/audit_outputs/visual-launch-gate/latest/report.md"
readonly PAYMENT_LOG="$ROOT/audit_outputs/demo-proof/latest/campaign-payment-smoke.log"
readonly LOCK_FILE="$OUT_ROOT/.strict-fast-proof.lock"

mkdir -p "$OUT"

CURRENT_STAGE="initialization"

log() {
  printf '%s\n' "$*"
}

section() {
  printf '\n================================================================\n'
  printf '▶ %s\n' "$*"
  printf '================================================================\n'
}

fail() {
  log
  log "❌ $*"
  exit 1
}

on_error() {
  local exit_code=$?
  local line="${BASH_LINENO[0]:-unknown}"
  local command="${BASH_COMMAND:-unknown}"

  printf '\n❌ Strict proof aborted\n' >&2
  printf 'Stage: %s\n' "$CURRENT_STAGE" >&2
  printf 'Line:  %s\n' "$line" >&2
  printf 'Code:  %s\n' "$exit_code" >&2
  printf 'Log:   %s\n' "$RUN_LOG" >&2

  if [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
    command="${command//${FF_OPERATOR_ACCESS_TOKEN}/<redacted>}"
  fi

  printf 'Command: %s\n' "$command" >&2
  exit "$exit_code"
}

trap on_error ERR
trap 'printf "\n⚠️ Strict proof interrupted during: %s\n" "$CURRENT_STAGE" >&2; exit 130' INT TERM

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

for command_name in bash curl grep sed awk python3 git; do
  require_command "$command_name"
done

test -f "$FAST_PROOF" || fail "Missing canonical proof runner: $FAST_PROOF"

# Prevent overlapping proof runs from fighting over browsers, ports, and reports.
exec 9>"$LOCK_FILE"

if command -v flock >/dev/null 2>&1; then
  if ! flock -n 9; then
    fail "Another strict proof is already running. Lock: $LOCK_FILE"
  fi
fi

is_local_base_url() {
  case "$FF_BASE_URL" in
    http://127.0.0.1:*|http://localhost:*|http://0.0.0.0:*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

read_token_from_env_files() {
  python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])

files = [
    root / ".env",
    root / ".env.local",
    root / ".env.development",
    root / "apps/web/.env",
    root / "apps/web/.env.local",
]

keys = (
    "FF_OPERATOR_ACCESS_TOKEN",
    "OPERATOR_ACCESS_TOKEN",
    "FF_DASHBOARD_ACCESS_TOKEN",
    "FF_DASHBOARD_TOKEN",
)

for path in files:
    if not path.is_file():
        continue

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        continue

    values = {}

    for raw in lines:
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()

        if key not in keys:
            continue

        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]

        if value:
            values[key] = value

    for key in keys:
        if values.get(key):
            print(values[key], end="")
            raise SystemExit(0)

raise SystemExit(1)
PY
}

resolve_operator_token() {
  local token_source=""
  local token=""

  if [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
    token="$FF_OPERATOR_ACCESS_TOKEN"
    token_source="FF_OPERATOR_ACCESS_TOKEN"
  elif [ -n "${OPERATOR_ACCESS_TOKEN:-}" ]; then
    token="$OPERATOR_ACCESS_TOKEN"
    token_source="OPERATOR_ACCESS_TOKEN"
  elif token="$(read_token_from_env_files 2>/dev/null)"; then
    token_source="local env file"
  elif is_local_base_url &&
       [ "$FF_ALLOW_LOCAL_DEV_TOKEN_FALLBACK" = "1" ]; then
    # Local-only compatibility token. Never used for a non-local FF_BASE_URL.
    token="dev-operator-20260529123018"
    token_source="local development fallback"
  else
    fail "No operator token found. Export FF_OPERATOR_ACCESS_TOKEN before running the strict proof."
  fi

  if [ "${#token}" -lt 12 ]; then
    fail "Resolved operator token is unexpectedly short."
  fi

  FF_OPERATOR_ACCESS_TOKEN="$token"
  OPERATOR_ACCESS_TOKEN="$token"
  FF_TOKEN_SOURCE="$token_source"

  export FF_OPERATOR_ACCESS_TOKEN
  export OPERATOR_ACCESS_TOKEN
  export FF_TOKEN_SOURCE
}

redact_stream() {
  FF_REDACT_VALUE="${FF_OPERATOR_ACCESS_TOKEN:-}" \
    python3 -u -c '
import os
import sys
from urllib.parse import quote

token = os.environ.get("FF_REDACT_VALUE", "")
encoded = quote(token, safe="") if token else ""

for line in sys.stdin:
    if token:
        line = line.replace(token, "<redacted>")
    if encoded and encoded != token:
        line = line.replace(encoded, "<redacted>")
    sys.stdout.write(line)
'
}

health_ready() {
  curl \
    --silent \
    --show-error \
    --fail \
    --max-time 4 \
    "$FF_BASE_URL/healthz" \
    >/dev/null 2>&1
}

wait_for_health() {
  local attempt

  for attempt in $(seq 1 40); do
    if health_ready; then
      return 0
    fi

    sleep 0.5
  done

  return 1
}

start_local_server_if_needed() {
  if health_ready; then
    log "✅ Application health check passed."
    return 0
  fi

  if ! is_local_base_url; then
    fail "Health check failed for non-local target: $FF_BASE_URL/healthz"
  fi

  if [ "$FF_AUTO_START_SERVER" != "1" ]; then
    fail "Application is not healthy. Start it with: ffserver restart"
  fi

  command -v ffserver >/dev/null 2>&1 ||
    fail "Application is down and ffserver is unavailable."

  log "Application is not healthy; starting the canonical local server…"
  ffserver restart

  wait_for_health ||
    fail "Application did not become healthy at $FF_BASE_URL/healthz"

  log "✅ Local application started and passed health check."
}

validate_clean_tree() {
  if [ "$FF_REQUIRE_CLEAN_TREE" != "1" ]; then
    return 0
  fi

  local dirty
  dirty="$(git status --short)"

  if [ -n "$dirty" ]; then
    printf '%s\n' "$dirty"
    fail "FF_REQUIRE_CLEAN_TREE=1, but the repository has uncommitted changes."
  fi

  log "✅ Repository working tree is clean."
}

run_logged_command() {
  local label="$1"
  shift

  section "$label"

  local exit_code

  set +e
  "$@" 2>&1 |
    redact_stream |
    tee -a "$RUN_LOG"

  exit_code=${PIPESTATUS[0]}
  set -e

  return "$exit_code"
}

validate_visual_report() {
  local report="${VISUAL_REPORT:-$ROOT/audit_outputs/visual-launch-gate/latest/report.md}"

  test -s "$report" ||
    fail "Visual launch report is missing or empty: $report"

  if grep -Eiq \
    '(^|[^[:alpha:]])PASS(ED)?([^[:alpha:]]|$)' \
    "$report"; then

    log "✅ Visual launch report contains an explicit PASS."
    return 0
  fi

  if grep -Eiq \
    '(^|[^0-9])100[[:space:]]*/[[:space:]]*100([^0-9]|$)' \
    "$report"; then

    log "✅ Visual launch report records the canonical 100/100 passing score."
    return 0
  fi

  fail "Visual launch report contains neither an explicit PASS nor a canonical 100/100 score: $report"
}

validate_payment_smoke() {
  test -s "$PAYMENT_LOG" ||
    fail "Campaign payment-smoke log was not generated: $PAYMENT_LOG"

  if ! grep -Eq \
    'Campaign payment smoke.*PASS|campaign money contract proof: PASS|PASSED: Campaign payment smoke' \
    "$PAYMENT_LOG"; then
    fail "Campaign payment-smoke log does not contain an explicit PASS."
  fi

  cp "$PAYMENT_LOG" "$OUT/campaign-payment-smoke.log"
  log "✅ Campaign payment smoke contains an explicit PASS."
}

write_summary() {
  local end_epoch duration commit branch
  end_epoch="$(date +%s)"
  duration=$((end_epoch - START_EPOCH))
  commit="$(git rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  branch="$(git branch --show-current 2>/dev/null || printf 'unknown')"

  {
    printf 'FutureFunded strict fast proof\n'
    printf 'Marker: FF_STRICT_FAST_PROOF_WRAPPER_V2_20260606\n'
    printf 'Generated UTC: %s\n' "$STAMP"
    printf 'Base URL: %s\n' "$FF_BASE_URL"
    printf 'Branch: %s\n' "$branch"
    printf 'Commit: %s\n' "$commit"
    printf 'Token source: %s\n' "$FF_TOKEN_SOURCE"
    printf 'Token value: <redacted>\n'
    printf 'Duration seconds: %s\n' "$duration"
    printf 'Visual report: %s\n' "$REPORT"
    printf 'Payment log: %s\n' "$PAYMENT_LOG"
    printf 'Modal stability included: %s\n' "$FF_INCLUDE_MODAL_STABILITY"
    printf 'Result: PASS\n'
  } >"$SUMMARY"

  ln -sfn "$(basename "$OUT")" "$OUT_ROOT/strict-latest"
}

CURRENT_STAGE="preflight"
section "Strict proof preflight"

resolve_operator_token
validate_clean_tree
start_local_server_if_needed

log "Root:         $ROOT"
log "Base URL:     $FF_BASE_URL"
log "Token source: $FF_TOKEN_SOURCE"
log "Token value:  <redacted>"
log "Output:       $OUT"

CURRENT_STAGE="canonical fast proof"

if ! run_logged_command \
  "Canonical FutureFunded fast proof" \
  env \
    FF_BASE_URL="$FF_BASE_URL" \
    FF_OPERATOR_ACCESS_TOKEN="$FF_OPERATOR_ACCESS_TOKEN" \
    OPERATOR_ACCESS_TOKEN="$OPERATOR_ACCESS_TOKEN" \
    FF_INCLUDE_CTA_PROOF="${FF_INCLUDE_CTA_PROOF:-0}" \
    bash "$FAST_PROOF"; then

  fail "Canonical fast proof returned a non-zero status. Review: $RUN_LOG"
fi

CURRENT_STAGE="artifact validation"
section "Validate canonical proof artifacts"

validate_payment_smoke
validate_visual_report

if [ "$FF_INCLUDE_MODAL_STABILITY" = "1" ]; then
  CURRENT_STAGE="campaign modal stability"

  require_command node
  test -f "$MODAL_GATE" ||
    fail "Modal stability gate not found: $MODAL_GATE"

  if ! run_logged_command \
    "Campaign modal stability gate" \
    env \
      FF_BASE_URL="$FF_BASE_URL" \
      OUT_DIR="$OUT/modal-stability" \
      node "$MODAL_GATE"; then

    fail "Campaign modal stability gate failed. Review: $RUN_LOG"
  fi
fi

CURRENT_STAGE="summary"
write_summary

section "Strict fast proof complete"
log "✅ Campaign payment smoke: PASS"
log "✅ Visual launch gate: PASS"
if [ "$FF_INCLUDE_MODAL_STABILITY" = "1" ]; then
  log "✅ Campaign modal stability: PASS"
fi
log "✅ Strict fast proof passed with an active operator token."
log
log "Summary: $SUMMARY"
log "Log:     $RUN_LOG"
log "Latest:  $OUT_ROOT/strict-latest"
