"""Add license tier and platform API keys to organizations.

Revision ID: 003
Revises: 002
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("license_tier", sa.String(20), server_default="free", nullable=False))
    op.add_column("organizations", sa.Column("license_key", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("license_valid_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("platform_keys", JSONB, server_default="{}", nullable=False))


def downgrade() -> None:
    op.drop_column("organizations", "platform_keys")
    op.drop_column("organizations", "license_valid_until")
    op.drop_column("organizations", "license_key")
    op.drop_column("organizations", "license_tier")
