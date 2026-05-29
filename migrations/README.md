# FutureFunded migrations

This Alembic scaffold is ready for schema changes.

Right now the app relies mostly on service/domain objects rather than declarative ORM models, so `target_metadata` is intentionally set to `None`.

Use:

- `make makemigration m="init"`
- `make migrate`

When you introduce declarative SQLAlchemy models, wire their metadata into `migrations/env.py`.
