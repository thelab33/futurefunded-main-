"""create ff_campaign_setups

Revision ID: 20260506_0001
Revises:
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ff_campaign_setups",
        sa.Column("setup_id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_slug", sa.String(length=160), nullable=False),
        sa.Column("organization_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("organization_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("campaign_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("goal_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("primary_sponsor_package", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("payment_stack", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="platform_onboarding"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index(
        "ix_ff_campaign_setups_campaign_slug_updated",
        "ff_campaign_setups",
        ["campaign_slug", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ff_campaign_setups_campaign_slug_updated", table_name="ff_campaign_setups")
    op.drop_table("ff_campaign_setups")
