#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:?usage: scripts/check_dns_ready.sh futurefunded.com}"
API_DOMAIN="${2:-api.${DOMAIN}}"

echo "== local resolver check =="
getent hosts "$DOMAIN" || true
getent hosts "$API_DOMAIN" || true
echo

for RESOLVER in 1.1.1.1 8.8.8.8; do
  echo "== public DNS via $RESOLVER =="
  echo "-- $DOMAIN --"
  dig @"$RESOLVER" +short "$DOMAIN" A || true
  dig @"$RESOLVER" +short "$DOMAIN" AAAA || true
  echo "-- $API_DOMAIN --"
  dig @"$RESOLVER" +short "$API_DOMAIN" A || true
  dig @"$RESOLVER" +short "$API_DOMAIN" AAAA || true
  echo
done

echo "== HTTPS reachability =="
curl -I --max-time 15 "https://$DOMAIN" || true
curl -I --max-time 15 "https://$API_DOMAIN" || true
