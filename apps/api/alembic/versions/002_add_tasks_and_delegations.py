"""add tasks and delegations tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tasks (Flow)
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.Enum("todo", "in_progress", "in_review", "done", name="taskstatus"), default="todo"),
        sa.Column("priority", sa.Enum("critical", "high", "medium", "low", name="taskpriority"), default="medium"),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("source", sa.Enum("jira", "github", "linear", "notion", "manual", "ai", name="tasksource"), default="manual"),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("source_id", sa.String(500), index=True),
        sa.Column("ai_summary", sa.Text),
        sa.Column("blockers", postgresql.JSONB, server_default="[]"),
        sa.Column("labels", postgresql.JSONB, server_default="[]"),
        sa.Column("due_date", sa.DateTime(timezone=True)),
    )

    # Delegations (Pilot)
    op.create_table(
        "delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("tool", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", "executed", name="delegationstatus"), default="pending"),
        sa.Column("proposed_for_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("execution_result", postgresql.JSONB),
    )


def downgrade() -> None:
    op.drop_table("delegations")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS delegationstatus")
    op.execute("DROP TYPE IF EXISTS tasksource")
    op.execute("DROP TYPE IF EXISTS taskpriority")
    op.execute("DROP TYPE IF EXISTS taskstatus")
