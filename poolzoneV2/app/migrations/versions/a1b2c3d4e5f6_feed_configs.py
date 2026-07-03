"""feed_configs table

Revision ID: a1b2c3d4e5f6
Revises: 304c5aacb3dd
Create Date: 2026-07-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "304c5aacb3dd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feed_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=True),
        sa.Column("update_whitelist", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_feed_configs_kind", "feed_configs", ["kind"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_feed_configs_kind", table_name="feed_configs")
    op.drop_table("feed_configs")
