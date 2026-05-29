# FutureFunded Secret Hygiene Audit

Generated: 2026-05-20T13:40:07-05:00

## Tracked env/runtime files
.env.example
.env.production.example
apps/web/app/static/css/_quarantine/wave2e-20260511-185014/ff.tokens.css
scripts/audit/ff_wave7a_secret_hygiene.py
scripts/security/ff_secret_scan_postmark.sh

## Tracked high-risk literal scan
.env.example:4:STRIPE_SECRET_KEY=sk_test_…MASKED
.env.example:15:STRIPE_SECRET_KEY=sk_test_…MASKED
.env.example:17:STRIPE_WEBHOOK_SECRET=whsec_…MASKED
.env.production.example:18:STRIPE_SECRET_KEY=sk_live_…MASKED
.env.production.example:20:STRIPE_WEBHOOK_SECRET=whsec_…MASKED
scripts/ff_live_runtime_audit.py:63:_whsec_…MASKED = ROOT / ".stripe-local-whsec"
scripts/ff_live_runtime_audit.py:64:if _whsec_…MASKED():
scripts/ff_live_runtime_audit.py:65:    _whsec = _whsec_…MASKED().strip()
scripts/ff_process_env_audit.py:91:    whsec_…MASKED = (
scripts/ff_process_env_audit.py:104:            ".stripe-local-whsec_…MASKED": (ROOT / ".stripe-local-whsec").exists(),
scripts/ff_process_env_audit.py:107:            ".stripe-local-whsec": mask(whsec_…MASKED),
scripts/ff_process_env_audit.py:175:        f"| .stripe-local-whsec | — | {mask(whsec_…MASKED)['valid_webhook_secret']} | — |",
scripts/ff_repo_audit.py:185:    whsec_…MASKED = [
scripts/ff_repo_audit.py:209:    if not any(v.startswith("whsec_") for v in whsec_…MASKED):

## Untracked/private runtime files present locally
./.env
./.env.bak-headline-20260428-140011
./.env.example
./.env.example.bak-identity-extract-20260510-100709
./.env.example.bak-provider-readiness-20260510-030655
./.env.local
./.env.local.example
./.env.local.stripe-test
./.env.production
./.env.production.example
./.stripe-local-whsec

## Gitignore coverage
27:# Environment / secrets
29:.env
30:.env.*
118:# FutureFunded local secrets
119:.env
120:.env.*
153:.env.local
157:.stripe-local-whsec
170:.env.local.stripe-test
