#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"

echo "== inline-style audit =="
python3 scripts/check_no_inline_css.py

echo
echo "== manifest/css ref audit =="
rg -n --glob '!*.bak*' "site\.webmanifest|manifest_url|ff-campaign\.css" apps/web/app/templates apps/web/app/static || true

echo
echo "== static asset existence =="
test -f apps/web/app/static/site.webmanifest
test -f apps/web/app/static/css/ff.tokens.css
test -f apps/web/app/static/css/ff.base.css
test -f apps/web/app/static/css/ff.pages.css
echo "assets present"

echo
echo "== live HTTP smoke =="
curl -fsSI http://127.0.0.1:5000/static/site.webmanifest | sed -n '1,12p'

curl -fsS http://127.0.0.1:5000/platform/ > /tmp/ff-platform.html
curl -fsS http://127.0.0.1:5000/c/connect-atx-elite > /tmp/ff-campaign.html

for f in /tmp/ff-platform.html /tmp/ff-campaign.html; do
  echo
  echo "-- checking $f --"

  test "$(rg -c 'href="/static/site\.webmanifest"' "$f")" = "1"
  test "$(rg -c 'href="/static/css/ff\.tokens\.css"' "$f")" = "1"
  test "$(rg -c 'href="/static/css/ff\.base\.css"' "$f")" = "1"
  test "$(rg -c 'href="/static/css/ff\.pages\.css"' "$f")" = "1"

  if rg -q 'ff-campaign\.css' "$f"; then
    echo "unexpected legacy css ref in $f"
    exit 1
  fi

  rg 'ff\.tokens\.css|ff\.base\.css|ff\.pages\.css|site\.webmanifest' "$f"
done

echo
echo "== pass =="
