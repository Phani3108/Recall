"""add new integration providers (zoom, figma, asana, hubspot, claude, whatsapp, cursor)

Revision ID: 006
Revises: 005
Create Date: 2026-04-07 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PROVIDERS = ["zoom", "figma", "asana", "hubspot", "claude", "whatsapp", "cursor"]


def upgrade() -> None:
    for val in NEW_PROVIDERS:
        op.execute(f"ALTER TYPE integrationprovider ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    pass  # Cannot remove enum values in PostgreSQL
