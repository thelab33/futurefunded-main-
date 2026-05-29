#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

MASK_SED='
s/(sk_live_|sk_test_|pk_live_|pk_test_|whsec_)[A-Za-z0-9_]+/\1…MASKED/g;
s/(FF_SMTP_PASSWORD=).+/\1…MASKED/g;
s/(FF_SMTP_USERNAME=).+/\1…MASKED/g;
s/(FF_SMTP_PASSWORD: ).+/\1…MASKED/g;
s/(FF_SMTP_USERNAME: ).+/\1…MASKED/g;
s/([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})/…UUID_TOKEN_MASKED/g
'

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1) Tracked env/config files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git ls-files | grep -Ei '(^|/)(\.env|.*\.env|.*postmark.*|.*smtp.*|.*stripe.*|.*cloudflare.*|.*operator.*)$' || true

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2) Current working tree secret-like references, masked"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
rg -n --hidden --pcre2 \
  --glob '!node_modules/**' \
  --glob '!.git/**' \
  --glob '!audit_outputs/**' \
  --glob '!instance/email-spool/**' \
  --glob '!*.pyc' \
  '(POSTMARK|postmarkapp\.com|FF_SMTP|SMTP_PASSWORD|SMTP_USERNAME|FF_EMAIL_FROM|FF_EMAIL_REPLY_TO|FF_EMAIL_TEST_TO|whsec_|sk_live_|sk_test_|pk_live_|pk_test_|[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})' \
  . 2>/dev/null | sed -E "$MASK_SED" || true

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3) Git history secret-like references, masked"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git log --all --full-history --date=iso --pretty=format:'COMMIT %h %ad %s' \
  -G '(POSTMARK|postmarkapp\.com|FF_SMTP|SMTP_PASSWORD|SMTP_USERNAME|whsec_|sk_live_|sk_test_|pk_live_|pk_test_|[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})' \
  -- . ':(exclude)node_modules/**' ':(exclude)audit_outputs/**' ':(exclude)instance/email-spool/**' \
  | sed -E "$MASK_SED" || true

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4) Local non-repo Postmark env file presence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lah ~/.config/futurefunded/postmark.env 2>/dev/null || true

echo
echo "Secret scan complete."
