"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("settings", postgresql.JSONB, server_default="{}"),
        sa.Column("token_budget_monthly", sa.Integer),
        sa.Column("tokens_used_this_month", sa.Integer, server_default="0"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("external_id", sa.String(255), unique=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_external_id", "users", ["external_id"])

    # Org memberships
    op.create_table(
        "org_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "member", "guest", name="orgrole", create_type=True)),
    )
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])

    # Integrations
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Enum("slack", "google", "github", "notion", "jira", "linear", "confluence", "gitlab", "microsoft365", "dropbox", name="integrationprovider", create_type=True), nullable=False),
        sa.Column("status", sa.Enum("connected", "active", "pending", "disconnected", "error", "syncing", name="integrationstatus", create_type=True), server_default="disconnected"),
        sa.Column("connected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("credential_ref", sa.String(255)),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_integrations_org_id", "integrations", ["org_id"])

    # Context entities
    op.create_table(
        "context_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.Enum("document", "message", "task", "person", "decision", "skill", "thread", "file", name="entitytype", create_type=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("source_integration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("integrations.id", ondelete="SET NULL")),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("source_id", sa.String(500)),
        sa.Column("extra_data", postgresql.JSONB, server_default="{}"),
        sa.Column("vector_id", sa.String(255)),
        sa.Column("access_user_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("access_everyone", sa.Boolean, server_default="false"),
    )
    op.create_index("ix_context_entities_org_id", "context_entities", ["org_id"])
    op.create_index("ix_context_entities_entity_type", "context_entities", ["entity_type"])
    op.create_index("ix_context_entities_source_id", "context_entities", ["source_id"])

    # Entity relations
    op.create_table(
        "entity_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("context_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("context_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(100), nullable=False),
        sa.Column("extra_data", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_entity_relations_source", "entity_relations", ["source_entity_id"])
    op.create_index("ix_entity_relations_target", "entity_relations", ["target_entity_id"])

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_shared", sa.Boolean, server_default="false"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_org_id", "conversations", ["org_id"])

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", postgresql.JSONB, server_default="[]"),
        sa.Column("tool_calls", postgresql.JSONB, server_default="[]"),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("model", sa.String(100)),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # Skills
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("is_builtin", sa.Boolean, server_default="false"),
        sa.Column("is_published", sa.Boolean, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trigger", postgresql.JSONB, server_default="{}"),
        sa.Column("steps", postgresql.JSONB, server_default="[]"),
        sa.Column("required_context", postgresql.JSONB, server_default="[]"),
        sa.Column("output_schema", postgresql.JSONB, server_default="{}"),
        sa.Column("upvotes", sa.Integer, server_default="0"),
        sa.Column("downvotes", sa.Integer, server_default="0"),
        sa.Column("execution_count", sa.Integer, server_default="0"),
    )

    # Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.Enum(
            "ai_query", "ai_response", "tool_call", "skill_execution",
            "delegation_proposed", "delegation_approved", "delegation_rejected", "delegation_executed",
            "integration_connected", "integration_disconnected", "data_accessed",
            name="auditaction", create_type=True,
        ), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("detail", postgresql.JSONB, server_default="{}"),
        sa.Column("tokens_consumed", sa.Integer, server_default="0"),
        sa.Column("cost_usd", sa.Float, server_default="0.0"),
        sa.Column("model_used", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"])

    # Token budgets
    op.create_table(
        "token_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monthly_limit", sa.Integer, nullable=False),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_token_budgets_scope_id", "token_budgets", ["scope_id"])


def downgrade() -> None:
    op.drop_table("token_budgets")
    op.drop_table("audit_logs")
    op.drop_table("skills")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("entity_relations")
    op.drop_table("context_entities")
    op.drop_table("integrations")
    op.drop_table("org_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS entitytype")
    op.execute("DROP TYPE IF EXISTS integrationstatus")
    op.execute("DROP TYPE IF EXISTS integrationprovider")
    op.execute("DROP TYPE IF EXISTS orgrole")
