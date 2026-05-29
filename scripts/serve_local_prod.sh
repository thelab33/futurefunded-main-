#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/apps/web"

source ../../.venv/bin/activate

fuser -k 5000/tcp 2>/dev/null || true
pkill -f 'gunicorn.*5000' 2>/dev/null || true

export FLASK_DEBUG=0
export FLASK_ENV=production
export ENV=production
export APP_ENV=production
export PYTHONUNBUFFERED=1

if [ -z "${SECRET_KEY:-}" ]; then
  export SECRET_KEY="$(python3 - <<'PY2'
import secrets
print(secrets.token_urlsafe(64))
PY2
)"
fi

if [ -z "${WTF_CSRF_SECRET_KEY:-}" ]; then
  export WTF_CSRF_SECRET_KEY="$SECRET_KEY"
fi

if [ -z "${PUBLIC_BASE_URL:-}" ]; then
  export PUBLIC_BASE_URL="https://localhost:5000"
fi

if [ -z "${API_BASE_URL:-}" ]; then
  export API_BASE_URL="https://localhost:8000"
fi

echo "serve_local_prod: using production env with ephemeral local secrets"
echo "serve_local_prod: PUBLIC_BASE_URL=$PUBLIC_BASE_URL"

exec gunicorn -w 2 -b 127.0.0.1:5000 "app:create_app()"
