#!/usr/bin/env bash
set -euo pipefail

# FF_DASHBOARD_AUDIT_TOKEN_BRIDGE_START
# Use the current private dashboard token for local audit seeds.
# Never commit the real token into this script.
if [ -z "${FF_DASHBOARD_AUDIT_TOKEN:-}" ]; then
  if [ -s /tmp/ff_operator_token ]; then
    FF_DASHBOARD_AUDIT_TOKEN="$(tr -d '\r\n\t ' < /tmp/ff_operator_token)"
  elif [ -n "${FF_OPERATOR_ACCESS_TOKEN:-}" ]; then
    FF_DASHBOARD_AUDIT_TOKEN="${FF_OPERATOR_ACCESS_TOKEN}"
  elif [ -f .env.local ]; then
    FF_DASHBOARD_AUDIT_TOKEN="$(
      grep -E '^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=' .env.local 2>/dev/null \
        | tail -n 1 \
        | sed -E 's/^[[:space:]]*FF_OPERATOR_ACCESS_TOKEN=//' \
        | sed -E 's/^["'\"'"']|["'\"'"']$//g' \
        | tr -d '\r\n'
    )"
  fi
fi

if [ -z "${FF_DASHBOARD_AUDIT_TOKEN:-}" ]; then
  FF_DASHBOARD_AUDIT_TOKEN="${FF_DASHBOARD_AUDIT_TOKEN}"
fi

export FF_DASHBOARD_AUDIT_TOKEN
# FF_DASHBOARD_AUDIT_TOKEN_BRIDGE_END


BASE="${FF_AUDIT_BASE_URL:-http://127.0.0.1:5000}"
STAMP="$(date +%Y%m%d%H%M%S)"
OUT="audit_outputs/served-url-lite-${STAMP}"
mkdir -p "$OUT/rendered"

echo "== FutureFunded served URL lite audit =="
echo "BASE=$BASE"
echo "OUT=$OUT"

if ! curl -fsS "$BASE/healthz" >/dev/null; then
  echo "Server not healthy. Restarting..."
  ffserver restart
fi

cat > "$OUT/seed_urls.txt" <<EOF
/
 /healthz
/platform/
/platform/onboarding
/platform/login
/platform/dashboard?access_token=${FF_DASHBOARD_AUDIT_TOKEN}
/c/connect-atx-elite
/static/css/ff.css
/static/css/onboarding.css
/static/js/ff-app.js
/static/js/ff-onboarding.js
/site.webmanifest
/static/site.webmanifest
EOF

sed -i 's/^ *//' "$OUT/seed_urls.txt"
sort -u "$OUT/seed_urls.txt" -o "$OUT/seed_urls.txt"

echo "type,url,status,bytes,content_type,source" > "$OUT/served_urls.csv"
echo "type,url,status,bytes,content_type,source" > "$OUT/missing_or_broken.csv"
: > "$OUT/discovered_assets.txt"
: > "$OUT/discovered_links.txt"

fetch_one() {
  local type="$1"
  local path="$2"
  local source="${3:-seed}"
  local url="$path"

  case "$url" in
    http*) ;;
    *) url="${BASE}${path}" ;;
  esac

  local safe
  safe="$(echo "$url" | sed -E 's#https?://##; s#[^A-Za-z0-9_.=-]+#_#g' | cut -c1-170)"
  local body="$OUT/rendered/${safe}.body"
  local head="$OUT/rendered/${safe}.headers"

  local meta
  meta="$(curl -k -L -sS --max-time 12 \
    -D "$head" \
    -o "$body" \
    -w "%{http_code}|%{size_download}|%{content_type}" \
    "$url" || true)"

  local status bytes ctype
  status="${meta%%|*}"
  meta="${meta#*|}"
  bytes="${meta%%|*}"
  ctype="${meta#*|}"

  echo "$type,$url,$status,$bytes,$ctype,$source" >> "$OUT/served_urls.csv"

  if [ -z "$status" ] || [ "$status" = "000" ] || [ "$status" -ge 400 ] 2>/dev/null; then
    echo "$type,$url,$status,$bytes,$ctype,$source" >> "$OUT/missing_or_broken.csv"
  fi

  if grep -qiE '<html|<!doctype' "$body" 2>/dev/null; then
    grep -Eoi '(href|src|poster|content)=["'\''][^"'\'' ]+["'\'']' "$body" \
      | sed -E 's/^[^=]+=//; s/^["'\'']//; s/["'\'']$//' \
      | grep -Ev '^(#|mailto:|tel:|sms:|javascript:|data:|blob:)' \
      >> "$OUT/discovered_assets.txt" || true

    grep -Eoi '<a[^>]+href=["'\''][^"'\'' ]+["'\'']' "$body" \
      | sed -E 's/^.*href=//; s/^["'\'']//; s/["'\'']$//' \
      | grep -Ev '^(#|mailto:|tel:|sms:|javascript:|data:|blob:)' \
      >> "$OUT/discovered_links.txt" || true
  fi

  if echo "$ctype $url" | grep -qiE 'text/css|\.css($|\?)'; then
    grep -Eo 'url\([^)]+\)' "$body" \
      | sed -E 's/^url\(//; s/\)$//; s/^["'\'']//; s/["'\'']$//' \
      | grep -Ev '^(#|mailto:|tel:|sms:|javascript:|data:|blob:)' \
      >> "$OUT/discovered_assets.txt" || true
  fi
}

echo
echo "== Fetch seed URLs =="
while IFS= read -r path; do
  [ -n "$path" ] || continue
  fetch_one "seed" "$path" "seed"
done < "$OUT/seed_urls.txt"

echo
echo "== Normalize discovered assets =="
python - "$BASE" "$OUT" <<'PY'
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import sys

base = sys.argv[1].rstrip("/") + "/"
out = Path(sys.argv[2])

items = []
for name in ["discovered_assets.txt", "discovered_links.txt"]:
    p = out / name
    if p.exists():
        items += p.read_text(errors="replace").splitlines()

seen = []
for raw in items:
    raw = raw.strip()
    if not raw:
        continue
    url, _ = urldefrag(urljoin(base, raw))
    if url not in seen:
        seen.append(url)

(out / "discovered_all_urls.txt").write_text("\n".join(seen) + ("\n" if seen else ""))
PY

echo
echo "== Fetch discovered internal static/assets =="
while IFS= read -r url; do
  [ -n "$url" ] || continue

  case "$url" in
    "$BASE"/static/*|"$BASE"/site.webmanifest|"$BASE"/robots.txt|"$BASE"/favicon.ico)
      fetch_one "asset" "$url" "discovered"
      ;;
  esac
done < "$OUT/discovered_all_urls.txt"

echo
echo "== Flask route map =="
python - <<'PY' > "$OUT/flask_url_map.txt" 2>"$OUT/flask_url_map_errors.txt" || true
from apps.web.app import create_app
app = create_app()
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    print(f"{r.rule:55s} {','.join(sorted(r.methods or [])):35s} {r.endpoint}")
PY

echo
echo "== Static files on disk =="
find apps/web/app/static -type f | sort > "$OUT/static_files_on_disk.txt" 2>/dev/null || true

echo
echo "== Summary =="
{
  echo "# FutureFunded served URL lite audit"
  echo
  echo "Generated: $STAMP"
  echo "Base: $BASE"
  echo
  echo "Served rows: $(($(wc -l < "$OUT/served_urls.csv") - 1))"
  echo "Broken rows: $(($(wc -l < "$OUT/missing_or_broken.csv") - 1))"
  echo "Discovered URLs: $(wc -l < "$OUT/discovered_all_urls.txt")"
  echo "Static files on disk: $(wc -l < "$OUT/static_files_on_disk.txt" 2>/dev/null || echo 0)"
  echo
  echo "## Broken / missing"
  tail -n +2 "$OUT/missing_or_broken.csv" | sed 's/^/- /' | head -80
} > "$OUT/README.md"

sed -n '1,180p' "$OUT/README.md"

echo
echo "== Broken CSV preview =="
column -s, -t "$OUT/missing_or_broken.csv" | sed -n '1,140p'

echo
echo "== Served URL preview =="
column -s, -t "$OUT/served_urls.csv" | sed -n '1,120p'

echo
echo "✅ Audit folder:"
echo "$OUT"
