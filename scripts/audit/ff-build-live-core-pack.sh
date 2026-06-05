#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
STAMP="$(date +%Y%m%d%H%M%S)"
PARENT="${FF_LIVE_CORE_PARENT:-$HOME/futurefunded-live-core-builds}"
OUT="$PARENT/futurefunded-live-core-${STAMP}"
SECRETS="$PARENT/futurefunded-secrets-${STAMP}"
REPORT="audit_outputs/live-core-pack-${STAMP}"

mkdir -p "$OUT" "$SECRETS" "$REPORT"

echo "== FutureFunded live-core pack builder =="
echo "ROOT=$ROOT"
echo "OUT=$OUT"
echo "SECRETS=$SECRETS"
echo "REPORT=$REPORT"

copy_file() {
  local src="$1"
  [ -f "$src" ] || return 0
  mkdir -p "$OUT/$(dirname "$src")"
  cp -p "$src" "$OUT/$src"
}

copy_dir() {
  local src="$1"
  [ -d "$src" ] || return 0

  mkdir -p "$OUT"

  rsync -a \
    --prune-empty-dirs \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'venv/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '.pytest_cache/' \
    --exclude '.mypy_cache/' \
    --exclude '.ruff_cache/' \
    --exclude '.DS_Store' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '*.bak*' \
    --exclude '*.before' \
    --exclude '*.orig' \
    --exclude '*.tmp' \
    --exclude '*.swp' \
    --exclude '*~' \
    --exclude 'app.db' \
    --exclude '*.sqlite' \
    --exclude '*.sqlite3' \
    --exclude 'instance/' \
    "$src" "$OUT/$(dirname "$src")/"
}

echo
echo "== Copy active app =="
copy_dir "apps"

echo
echo "== Copy migrations and runtime config =="
copy_dir "migrations"
copy_file "alembic.ini"

echo
echo "== Copy dependency/build files =="
for f in \
  requirements.txt requirements-dev.txt constraints.txt \
  pyproject.toml setup.cfg setup.py \
  package.json package-lock.json npm-shrinkwrap.json pnpm-lock.yaml yarn.lock \
  postcss.config.js postcss.config.cjs tailwind.config.js tailwind.config.cjs \
  vite.config.js vite.config.ts playwright.config.js playwright.config.ts \
  Dockerfile Dockerfile.web docker-compose.yml docker-compose.yaml \
  Makefile README.md
do
  copy_file "$f"
done

echo
echo "== Copy launch governance docs =="
copy_dir "docs/launch"
copy_file "docs/demo/sister-demo-handoff.md"

echo
echo "== Copy active audit / test / demo scripts only =="
ACTIVE_SCRIPTS=(
  "scripts/audit/ff-served-url-lite.sh"
  "scripts/audit/ff-dashboard-board.sh"
  "scripts/audit/ff-launch-surface-board.sh"
  "scripts/audit/ff-route-census.sh"
  "scripts/audit/ff-route-governance.sh"
  "scripts/audit/ff-production-checklist.sh"
  "scripts/audit/ff-launch-control.sh"
  "scripts/audit/ff-build-live-core-pack.sh"

  "scripts/demo/ff-start-local-demo.sh"
  "scripts/demo/ff-demo-start.sh"
  "scripts/demo/ff-demo-day.sh"
  "scripts/demo/ff-fast-proof-strict.sh"
  "scripts/demo/ff-money-proof.sh"

  "scripts/ops/ff-prod-doctor.sh"
  "scripts/release/ff_onboarding_source_locator.sh"
)

for f in "${ACTIVE_SCRIPTS[@]}"; do
  copy_file "$f"
done

find "$OUT/scripts" -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

echo
echo "== Copy safe env templates, move real env files to private secrets folder =="
for f in \
  .env.example .env.local.example .env.production.example .env.staging.example .flaskenv.example
do
  copy_file "$f"
done

for f in .env .env.local .flaskenv; do
  if [ -f "$f" ]; then
    cp -p "$f" "$SECRETS/$f"
    chmod 600 "$SECRETS/$f"
    echo "$f copied to private secrets folder only" >> "$REPORT/env-secrets.txt"
  fi
done

{
  for f in .env .env.local .flaskenv "$SECRETS"/.env "$SECRETS"/.env.local "$SECRETS"/.flaskenv; do
    [ -f "$f" ] || continue
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$f" | sed 's/=.*//' || true
  done
} | sort -u | awk 'NF { print $0"=" }' > "$OUT/.env.example.generated"

cat > "$OUT/.gitignore" <<'GITIGNORE'
# Python
.venv/
venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
npm-debug.log*
pnpm-debug.log*
yarn-debug.log*

# Local secrets
.env
.env.*
!.env.example
!.env.local.example
!.env.production.example
!.env.staging.example
!.flaskenv.example
_secrets_local_DO_NOT_COMMIT/

# Local runtime data
instance/
*.db
*.sqlite
*.sqlite3

# Generated audits/builds
audit_outputs/
reports/
coverage/
dist/
build/

# Editor/system
.DS_Store
*.swp
*~
GITIGNORE

cat > "$OUT/README_LIVE_CORE.md" <<MD
# FutureFunded Live Core

Generated from: \`$ROOT\`  
Generated at: \`$STAMP\`

## Canonical launch surfaces

| Surface | URL |
|---|---|
| Homepage | \`/\` |
| Campaign | \`/c/connect-atx-elite\` |
| Onboarding | \`/platform/onboarding\` |
| Private Dashboard | \`/platform/dashboard?access_token=...\` |

## Important

Real env files were **not committed into this pack**. They were copied separately to:

\`$SECRETS\`

Use \`.env.example.generated\` as the deployment/env checklist.
MD

echo
echo "== Build live-core manifest =="
(
  cd "$OUT"
  find . -type f | sort
) > "$OUT/LIVE_CORE_FILELIST.txt"

echo
echo "== Build cleanup candidate report for original repo =="
{
  echo "# FutureFunded Cleanup Candidates"
  echo
  echo "Do not delete automatically. Review after live-core pack is verified."
  echo
  echo "## Backup / historical files"
  find . \
    -path './.git' -prune -o \
    -path './.venv' -prune -o \
    -path './node_modules' -prune -o \
    -path './audit_outputs' -prune -o \
    -type f \( \
      -name '*.bak*' -o \
      -name '*.before' -o \
      -name '*.orig' -o \
      -name '*~' \
    \) -print | sort

  echo
  echo "## Large/noisy folders to keep out of clean repo"
  find . -maxdepth 2 -type d \( \
    -name audit_outputs -o \
    -name reports -o \
    -name node_modules -o \
    -name .venv -o \
    -name __pycache__ -o \
    -name .pytest_cache \
  \) -print | sort
} > "$REPORT/cleanup-candidates.md"

echo
echo "== Secret guard in live-core source =="
if grep -RInE 'access_token=[0-9a-fA-F]{64}|FF_OPERATOR_ACCESS_TOKEN=[0-9a-fA-F]{64}' \
  "$OUT" \
  --exclude-dir='.git' \
  --exclude='.env*' \
  > "$REPORT/secret-guard.txt"; then
  echo "❌ Possible token/secrets found in live-core pack."
  cat "$REPORT/secret-guard.txt"
  exit 1
else
  echo "✅ No 64-char operator token found in live-core source."
fi

echo
echo "== Syntax proof in live-core pack =="
(
  cd "$OUT"

  python -m py_compile apps/web/app/__init__.py

  for f in \
    scripts/audit/ff-served-url-lite.sh \
    scripts/audit/ff-dashboard-board.sh \
    scripts/audit/ff-launch-surface-board.sh \
    scripts/audit/ff-route-census.sh \
    scripts/audit/ff-route-governance.sh \
    scripts/audit/ff-production-checklist.sh \
    scripts/audit/ff-launch-control.sh
  do
    [ -f "$f" ] && bash -n "$f"
  done
)

cat > "$REPORT/live-core-pack.md" <<MD
# FutureFunded Live-Core Pack

## Output

- Live-core source: \`$OUT\`
- Private env backup: \`$SECRETS\`
- Report folder: \`$REPORT\`

## Included

- \`apps/\`
- \`migrations/\`
- active dependency/build files
- launch governance docs
- active audit/test/demo scripts
- env examples / generated env checklist

## Excluded

- \`audit_outputs/\`
- \`.venv/\`
- \`node_modules/\`
- backup files
- local DB files
- real env files from committed source

## Next steps

1. Open the live-core folder.
2. Review \`LIVE_CORE_FILELIST.txt\`.
3. Copy private env values from \`$SECRETS\` into deployment secrets, not Git.
4. Run server proof from the live-core folder.
5. Create a fresh GitHub repo or branch only after the proof is green.
MD

echo
echo "✅ Live-core pack created:"
echo "$OUT"
echo
echo "✅ Private env backup:"
echo "$SECRETS"
echo
echo "✅ Report:"
echo "$REPORT/live-core-pack.md"
