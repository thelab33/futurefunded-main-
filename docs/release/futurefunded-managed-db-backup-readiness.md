# FutureFunded Managed DB / Backup Readiness

FutureFunded is currently demo-safe with local SQLite.

Before live donors, sponsors, families, teams, operators, or production money flows are enabled, FutureFunded must use a managed production database with provider-managed backups and a documented restore path.

## Current boundary

Local SQLite is acceptable for:

- local development
- local demos
- screenshot boards
- smoke tests
- founder walkthroughs
- non-production campaign proofing

Local SQLite is not acceptable for:

- live donor records
- sponsor payments
- family/team production use
- operator dashboard production use
- audit-grade ledger retention
- multi-tenant customer data

## Production DB requirements

Before live users:

- Use managed PostgreSQL or another managed production-grade relational database.
- Set `DATABASE_URL` privately in the production host.
- Keep `DATABASE_URL` out of git.
- Enable provider-managed backups.
- Confirm backup retention.
- Confirm point-in-time recovery if available.
- Confirm restore procedure.
- Run at least one restore drill before live launch.
- Confirm migration owner and rollback procedure.
- Confirm production DB credentials are never printed in logs.

## Required private production metadata

Configure these privately before strict production mode:

- `DATABASE_URL`
- `FF_REQUIRE_MANAGED_DB=1`
- `FF_DB_BACKUP_PROVIDER`
- `FF_DB_BACKUP_POLICY`
- `FF_DB_BACKUP_RETENTION_DAYS`
- `FF_DB_RESTORE_TESTED_AT`
- `FF_DB_MIGRATION_OWNER`

Optional but recommended:

- `FF_DB_PITR_ENABLED`
- `FF_DB_BACKUP_REGION`
- `FF_DB_BACKUP_RUNBOOK_URL`
- `FF_DB_ROLLBACK_OWNER`

## Commands

Boundary/demo mode:

    python scripts/release/ff_managed_db_backup_gate.py

Strict production preview:

    FF_REQUIRE_MANAGED_DB=1 python scripts/release/ff_managed_db_backup_gate.py

Expected current result is `PASS_WITH_BOUNDARIES`.

Strict mode should fail until managed DB and backup metadata are configured.
