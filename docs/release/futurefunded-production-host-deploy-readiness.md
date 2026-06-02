# FutureFunded Production Host / Deploy Readiness

FutureFunded is locally demo-safe and proof-backed. Before real users or live money flows, the production host must be explicitly configured, documented, and proven.

## Current boundary

Local development is allowed for:

- founder demos
- local smoke tests
- screenshot boards
- proof gates
- non-production payment testing
- campaign polish review

Local development is not a production hosting plan.

## Production host requirements

Before live users:

- production host/provider selected
- production app URL configured
- custom domain configured
- TLS/HTTPS enabled
- production environment values stored privately
- deploy command documented
- rollback command documented
- logs checked for secret safety
- health endpoint verified over production URL
- generated files excluded from git
- static assets served correctly
- live money gates run after deploy

## Required private production metadata

Set privately in the production host:

- `FF_PRODUCTION_HOST_PROVIDER`
- `FF_PRODUCTION_APP_URL`
- `FF_PRODUCTION_DOMAIN`
- `FF_PRODUCTION_TLS_ENABLED`
- `FF_DEPLOY_COMMAND`
- `FF_ROLLBACK_COMMAND`
- `FF_DEPLOY_OWNER`

Optional but recommended:

- `FF_LOG_PROVIDER`
- `FF_HOST_REGION`
- `FF_STATIC_ASSET_STRATEGY`
- `FF_RUNTIME_PROCESS_MANAGER`
- `FF_ERROR_TRACKING_PROVIDER`

## Strict mode

Strict mode blocks production launch until host metadata is configured:

    FF_REQUIRE_PRODUCTION_HOST=1 python scripts/release/ff_production_host_readiness_gate.py

Expected current state is boundary mode:

    python scripts/release/ff_production_host_readiness_gate.py

## Live deploy checklist

1. Configure production host.
2. Set private production env values.
3. Configure domain.
4. Confirm HTTPS/TLS.
5. Deploy app.
6. Confirm `/healthz`.
7. Confirm platform route.
8. Confirm campaign route.
9. Run production host readiness gate.
10. Run production ops gate.
11. Run money ops gate.
12. Run managed DB backup gate in strict mode only after real DB is configured.

## Boundary statement

FutureFunded can remain demo-safe locally, but live users require a documented production host, TLS, rollback path, and private environment configuration.
