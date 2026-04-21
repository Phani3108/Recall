"""Add structured execution_payload to delegations for Pilot."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delegations",
        sa.Column("execution_payload", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delegations", "execution_payload")
