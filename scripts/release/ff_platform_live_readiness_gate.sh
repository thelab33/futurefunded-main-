#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${FF_BASE_URL:-http://127.0.0.1:5000}"
OUT="${FF_LIVE_READINESS_OUT:-audit_outputs/platform-live-readiness-manual}"
mkdir -p "$OUT"

failures=0
warnings=0

pass() { echo "✅ PASS: $1"; }
warn() { echo "⚠️ WARN: $1"; warnings=$((warnings + 1)); }
fail() { echo "❌ FAIL: $1"; failures=$((failures + 1)); }

check_url() {
  local label="$1"
  local path="$2"
  local expected="${3:-200}"
  local code

  code="$(curl -fsS -o /dev/null -w "%{http_code}" "$BASE_URL$path" || true)"

  if [ "$code" = "$expected" ]; then
    pass "$label [$path] status=$code"
  else
    fail "$label [$path] expected=$expected got=$code"
  fi
}

echo "== FutureFunded Platform Live Readiness Gate =="
echo "BASE_URL=$BASE_URL"
echo

echo "== 1. Core routes =="
check_url "Health" "/healthz" "200"
check_url "Platform homepage" "/platform/" "200"
check_url "Campaign page" "/c/connect-atx-elite" "200"
check_url "Launch onboarding" "/platform/onboarding" "200"
check_url "Operator login" "/platform/login" "200"
code="$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/platform/dashboard" || true)"
if [ "$code" = "200" ] || [ "$code" = "302" ]; then
  pass "Dashboard guard [/platform/dashboard] status=$code"
else
  fail "Dashboard guard [/platform/dashboard] expected 200 or 302 got=$code"
fi

echo
echo "== 2. Public legal/trust routes =="
for path in /privacy /terms /robots.txt /sitemap.xml /static/site.webmanifest /.well-known/security.txt; do
  code="$(curl -fsS -o /dev/null -w "%{http_code}" "$BASE_URL$path" || true)"
  if [ "$code" = "200" ]; then
    pass "$path"
  else
    warn "$path missing or non-200: $code"
  fi
done

echo
echo "== 3. Money ops current gate =="
if FF_BASE_URL="$BASE_URL" bash scripts/release/ff_money_ops_current_gate.sh > "$OUT/money-ops-current-gate.txt" 2>&1; then
  pass "Current money ops gate"
else
  fail "Current money ops gate"
fi

tail -60 "$OUT/money-ops-current-gate.txt" || true

echo
echo "== 4. Surface board =="
if FF_BASE_URL="$BASE_URL" FF_SURFACE_BOARD_STRICT=1 node scripts/release/ff_surface_lock_board.mjs > "$OUT/surface-board.txt" 2>&1; then
  pass "Surface board"
else
  fail "Surface board"
fi

tail -40 "$OUT/surface-board.txt" || true

echo
echo "== 5. Dashboard board =="
if FF_BASE_URL="$BASE_URL" FF_DASHBOARD_BOARD_STRICT=1 node scripts/release/ff_dashboard_screenshot_board.mjs > "$OUT/dashboard-board.txt" 2>&1; then
  pass "Dashboard board"
else
  fail "Dashboard board"
fi

tail -40 "$OUT/dashboard-board.txt" || true

echo
echo "== 6. Env sanity =="
if [ -f scripts/release/ff_env_sanity_check.sh ]; then
  if scripts/release/ff_env_sanity_check.sh .env > "$OUT/env-sanity.txt" 2>&1; then
    pass "Local env sanity"
  else
    warn "Local env sanity has warnings/blockers; review $OUT/env-sanity.txt"
  fi
  cat "$OUT/env-sanity.txt"
else
  warn "Missing env sanity checker"
fi

echo
echo "== 7. Production blockers snapshot =="
python - <<'PY' | tee "$OUT/prod-blockers.txt"
import os
from pathlib import Path

def env(key):
    return os.environ.get(key, "")

# Soft-load .env without printing secrets.
p = Path(".env")
if p.exists():
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

checks = {
    "DATABASE_URL_present": bool(env("DATABASE_URL")),
    "DATABASE_URL_current_repo_sqlite": env("DATABASE_URL") == "sqlite:///instance/futurefunded-dev.db",
    "STRIPE_PUBLIC_KEY_test_present": env("STRIPE_PUBLIC_KEY").startswith("pk_test_"),
    "STRIPE_SECRET_KEY_test_present": env("STRIPE_SECRET_KEY").startswith("sk_test_"),
    "STRIPE_WEBHOOK_SECRET_present": env("STRIPE_WEBHOOK_SECRET").startswith("whsec_"),
    "FORBID_LIVE_KEYS_enabled": env("FF_FORBID_LIVE_KEYS") == "1",
    "SMTP_host_present": bool(env("FF_SMTP_HOST")),
    "SMTP_username_present": bool(env("FF_SMTP_USERNAME")),
    "EMAIL_dry_run_enabled": env("FF_EMAIL_DRY_RUN") == "1",
    "PAYPAL_disabled_or_missing": env("PAYPAL_MODE") in {"", "disabled"},
}

for key, value in checks.items():
    print(f"{key}={value}")

print()
print("BOUNDARY:")
if not checks["SMTP_host_present"]:
    print("- Real email delivery is not enabled yet.")
if checks["FORBID_LIVE_KEYS_enabled"]:
    print("- Live Stripe payments are intentionally blocked.")
if checks["DATABASE_URL_current_repo_sqlite"]:
    print("- Local DB is clean for dev/demo; production should use managed DB.")
if checks["PAYPAL_disabled_or_missing"]:
    print("- PayPal is optional and currently disabled/not configured.")
PY

echo
echo "== 8. Git safety =="
git status --short | tee "$OUT/git-status.txt"

if git status --short | grep -E '^.. \.env$|^\?\? \.env$|^.. \.env\.email\.local$|^\?\? \.env\.email\.local$|audit_outputs/|\.ff_backups/' >/dev/null; then
  warn "Local/generated files are present or ignored. Do not commit them."
else
  pass "No obvious local/generated files in git status"
fi

echo
echo "== 9. Verdict =="
if [ "$failures" -eq 0 ]; then
  echo "✅ PLATFORM_LIVE_READINESS_GATE=PASS_WITH_BOUNDARIES"
  echo "Warnings: $warnings"
else
  echo "❌ PLATFORM_LIVE_READINESS_GATE=FAIL"
  echo "Failures: $failures"
  echo "Warnings: $warnings"
  exit 1
fi
