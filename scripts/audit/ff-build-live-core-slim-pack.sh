#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
STAMP="$(date +%Y%m%d%H%M%S)"
PARENT="${FF_LIVE_CORE_PARENT:-$HOME/futurefunded-live-core-builds}"
OUT="$PARENT/futurefunded-live-core-slim-${STAMP}"
SECRETS="$PARENT/futurefunded-secrets-slim-${STAMP}"
REPORT="audit_outputs/live-core-slim-pack-${STAMP}"

mkdir -p "$OUT" "$SECRETS" "$REPORT"

echo "== FutureFunded slim live-core pack builder =="
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

copy_dir_clean() {
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
echo "== Copy active web platform =="
copy_dir_clean "apps/web"

echo
echo "== Decide whether apps/api sidecar is required =="
API_REF_REPORT="$REPORT/apps-api-reference-check.txt"
{
  grep -RInE 'apps/api|apps\.api|uvicorn .*apps|/api|api:' \
    Dockerfile Dockerfile.web docker-compose.yml docker-compose.yaml pyproject.toml package.json Makefile \
    2>/dev/null || true
} > "$API_REF_REPORT"

if [ -s "$API_REF_REPORT" ]; then
  echo "Including apps/api because root deployment files reference API-related contracts."
  copy_dir_clean "apps/api"
  echo "included" > "$REPORT/apps-api-inclusion.txt"
else
  echo "Skipping apps/api; no root deployment reference found."
  echo "excluded" > "$REPORT/apps-api-inclusion.txt"
fi

echo
echo "== Copy migrations and runtime config =="
copy_dir_clean "migrations"
copy_file "alembic.ini"

echo
echo "== Copy dependency/build/deploy files =="
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
echo "== Copy only current launch docs =="
copy_file "docs/launch/LAUNCH_SURFACE_REGISTRY.md"
copy_file "docs/demo/sister-demo-handoff.md"

echo
echo "== Copy active audit/demo/proof scripts =="
ACTIVE_SCRIPTS=(
  "scripts/audit/ff-served-url-lite.sh"
  "scripts/visual/ff-launch-surface-board.py"
  "scripts/visual/ff-all-page-boards.py"
  "scripts/visual/ff-platform-dashboard-board.py"
  "scripts/visual/ff_dashboard_access.py"
  "scripts/audit/ff-route-census.sh"
  "scripts/audit/ff-route-governance.sh"
  "scripts/audit/ff-production-checklist.sh"
  "scripts/audit/ff-launch-control.sh"
  "scripts/audit/ff-build-live-core-pack.sh"
  "scripts/audit/ff-build-live-core-slim-pack.sh"

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
echo "== Copy env templates; move real env files to private secrets folder only =="
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
.venv/
venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/

node_modules/
npm-debug.log*
pnpm-debug.log*
yarn-debug.log*

.env
.env.*
!.env.example
!.env.local.example
!.env.production.example
!.env.staging.example
!.flaskenv.example
_secrets_local_DO_NOT_COMMIT/

instance/
*.db
*.sqlite
*.sqlite3

audit_outputs/
reports/
coverage/
dist/
build/

.DS_Store
*.swp
*~
GITIGNORE

cat > "$OUT/README_LIVE_CORE.md" <<MD
# FutureFunded Slim Live Core

Generated from: \`$ROOT\`  
Generated at: \`$STAMP\`

## Canonical launch surfaces

| Surface | URL |
|---|---|
| Homepage | \`/\` |
| Campaign | \`/c/connect-atx-elite\` |
| Onboarding | \`/platform/onboarding\` |
| Private Dashboard | \`/platform/dashboard?access_token=...\` |

## First user path

This pack is intended for:
1. Connect ATX Elite / sister-team launch
2. sponsor/donor demo readiness
3. then white-label SaaS reuse

## Secrets

Real env files were not copied into Git-safe source. They were copied separately to:

\`$SECRETS\`

Use \`.env.example.generated\` as the deployment env checklist.
MD

echo

echo
echo "== Copy active ops proof helpers =="
# FF_SLIM_PACK_OPS_HELPERS_20260604
for f in \
  scripts/ops/ff-install-visual-board-deps.sh \
  scripts/ops/ff-main-fresh-board-proof.sh
do
  if [ -f "$ROOT/$f" ]; then
    mkdir -p "$OUT/$(dirname "$f")"
    cp "$ROOT/$f" "$OUT/$f"
    chmod +x "$OUT/$f" 2>/dev/null || true
    echo "✅ copied $f"
  else
    echo "⚠️ missing optional ops helper: $f"
  fi
done

echo "== Build slim manifest =="
(
  cd "$OUT"
  find . -type f | sort
) > "$OUT/LIVE_CORE_FILELIST.txt"

echo
echo "== Secret guard =="
if grep -RInE 'access_token=[0-9a-fA-F]{64}|FF_OPERATOR_ACCESS_TOKEN=[0-9a-fA-F]{64}' \
  "$OUT" \
  --exclude-dir='.git' \
  --exclude='.env*' \
  > "$REPORT/secret-guard.txt"; then
  echo "❌ Possible token/secrets found in slim pack."
  cat "$REPORT/secret-guard.txt"
  exit 1
else
  echo "✅ No 64-char operator token found in slim source."
fi

echo
echo "== Backup/noise guard =="
find "$OUT" -type f \( -name '*.bak*' -o -name '*.before' -o -name '*.orig' -o -name '*~' \) \
  > "$REPORT/backup-noise.txt"

if [ -s "$REPORT/backup-noise.txt" ]; then
  echo "❌ Backup/noise files found in slim pack:"
  cat "$REPORT/backup-noise.txt"
  exit 1
else
  echo "✅ No backup/noise files found."
fi

echo
echo "== Syntax proof =="
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

cat > "$REPORT/live-core-slim-pack.md" <<MD
# FutureFunded Slim Live-Core Pack

## Output

- Slim live-core source: \`$OUT\`
- Private env backup: \`$SECRETS\`
- Report folder: \`$REPORT\`

## Included

- active web app
- active static assets/templates
- migrations
- root dependency/build/deploy files
- launch registry
- sister demo handoff
- active audit/demo scripts
- generated env checklist

## API sidecar

\`$(cat "$REPORT/apps-api-inclusion.txt")\`

## Excluded

- audit outputs
- virtualenv
- node_modules
- old proof docs
- closeout docs
- backup files
- local DB files
- real env files from Git-safe source

## Proof

- secret guard: passed
- backup/noise guard: passed
- syntax proof: passed
MD

echo
echo "✅ Slim live-core pack created:"
echo "$OUT"
echo
echo "✅ Private env backup:"
echo "$SECRETS"
echo
echo "✅ Report:"
echo "$REPORT/live-core-slim-pack.md"
