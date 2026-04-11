"""add sync_cursor and execution tracking columns

Revision ID: 007
Revises: 006
Create Date: 2026-04-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sync_cursor to integrations for incremental sync tracking
    op.add_column(
        "integrations",
        sa.Column("sync_cursor", sa.JSON(), nullable=True, server_default=None,
                  comment="Provider-specific sync cursor for incremental sync"),
    )

    # Add synced_entity_count for tracking
    op.add_column(
        "integrations",
        sa.Column("synced_entity_count", sa.Integer(), nullable=False, server_default="0",
                  comment="Total number of entities synced from this integration"),
    )

    # Ensure context_entities has an index on source_id + org_id for fast upserts
    op.create_index(
        "ix_context_entities_org_source",
        "context_entities",
        ["org_id", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_context_entities_org_source", table_name="context_entities")
    op.drop_column("integrations", "synced_entity_count")
    op.drop_column("integrations", "sync_cursor")
