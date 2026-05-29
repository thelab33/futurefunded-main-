#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

OUT="docs/release-proof/secret-hygiene-latest.md"
TMP="$(mktemp)"

MASK_SED='s/(sk_live_|sk_test_|pk_live_|pk_test_|rk_live_|rk_test_|whsec_|SG\.|xox[baprs]-|gh[pousr]_|github_pat_)[A-Za-z0-9_./+=:-]+/\1…MASKED/g'

{
  echo "# FutureFunded Secret Hygiene Audit"
  echo
  echo "Generated: $(date -Is)"
  echo
  echo "## Tracked env/runtime files"
  git ls-files | grep -E '(^|/)\.env($|\.|/)|\.stripe-local-whsec|secret|credential|token' || true

  echo
  echo "## Tracked high-risk literal scan"
  git grep -nE \
    'sk_live_[A-Za-z0-9_]+|sk_test_[A-Za-z0-9_]+|rk_live_[A-Za-z0-9_]+|rk_test_[A-Za-z0-9_]+|whsec_[A-Za-z0-9_]+|SG\.[A-Za-z0-9_.-]+|github_pat_[A-Za-z0-9_]+' \
    -- . \
    ':!docs/release-proof/secret-hygiene-latest.md' \
    ':!docs/release-proof/active-repo-map-latest.json' \
    ':!docs/release-proof/active-repo-map-latest.md' \
    || true

  echo
  echo "## Untracked/private runtime files present locally"
  find . \
    -path './.git' -prune -o \
    -path './.venv' -prune -o \
    -path './node_modules' -prune -o \
    -type f \
    \( -name '.env' -o -name '.env.*' -o -name '.stripe-local-whsec' \) \
    -print | sort || true

  echo
  echo "## Gitignore coverage"
  grep -nE '(^|/)\.env|\.stripe-local-whsec|secret|credential|token' .gitignore 2>/dev/null || true
} > "$TMP"

sed -E "$MASK_SED" "$TMP" > "$OUT"
rm -f "$TMP"

echo "Wrote $OUT"
sed -n '1,220p' "$OUT"
