"""Core domain models for Recall — the entity graph."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, Integer, Float, ForeignKey, Enum, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import BaseModel, TenantModel


# ── Enums ──


class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class IntegrationProvider(str, enum.Enum):
    SLACK = "slack"
    GOOGLE = "google"
    GITHUB = "github"
    NOTION = "notion"
    JIRA = "jira"
    LINEAR = "linear"
    CONFLUENCE = "confluence"
    GITLAB = "gitlab"
    MICROSOFT365 = "microsoft365"
    DROPBOX = "dropbox"
    ZOOM = "zoom"
    FIGMA = "figma"
    ASANA = "asana"
    HUBSPOT = "hubspot"
    CLAUDE = "claude"
    WHATSAPP = "whatsapp"
    CURSOR = "cursor"


class IntegrationStatus(str, enum.Enum):
    CONNECTED = "connected"
    ACTIVE = "active"
    PENDING = "pending"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SYNCING = "syncing"


class EntityType(str, enum.Enum):
    DOCUMENT = "document"
    MESSAGE = "message"
    TASK = "task"
    PERSON = "person"
    DECISION = "decision"
    SKILL = "skill"
    THREAD = "thread"
    FILE = "file"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskSource(str, enum.Enum):
    JIRA = "jira"
    GITHUB = "github"
    LINEAR = "linear"
    NOTION = "notion"
    MANUAL = "manual"
    AI = "ai"


class DelegationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class AuditAction(str, enum.Enum):
    AI_QUERY = "ai_query"
    AI_RESPONSE = "ai_response"
    TOOL_CALL = "tool_call"
    SKILL_EXECUTION = "skill_execution"
    DELEGATION_PROPOSED = "delegation_proposed"
    DELEGATION_APPROVED = "delegation_approved"
    DELEGATION_REJECTED = "delegation_rejected"
    DELEGATION_EXECUTED = "delegation_executed"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    DATA_ACCESSED = "data_accessed"


# ── Organizations ──


class LicenseTier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Organization(BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # License
    license_tier: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    license_key: Mapped[str | None] = mapped_column(String(255))
    license_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Platform API keys (OpenAI, Anthropic, Composio, etc.) — stored per-org
    platform_keys: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Token budget (monthly)
    token_budget_monthly: Mapped[int | None] = mapped_column(Integer)
    tokens_used_this_month: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    members: Mapped[list["OrgMembership"]] = relationship(back_populates="organization")
    integrations: Mapped[list["Integration"]] = relationship(back_populates="organization")


# ── Users ──


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    memberships: Mapped[list["OrgMembership"]] = relationship(back_populates="user")


class OrgMembership(BaseModel):
    __tablename__ = "org_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole, values_callable=lambda e: [m.value for m in e]), default=OrgRole.MEMBER)

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="members")


# ── Integrations ──


class Integration(TenantModel):
    __tablename__ = "integrations"

    provider: Mapped[IntegrationProvider] = mapped_column(Enum(IntegrationProvider, values_callable=lambda e: [m.value for m in e]), nullable=False)
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, values_callable=lambda e: [m.value for m in e]), default=IntegrationStatus.DISCONNECTED
    )
    connected_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # Encrypted credentials stored separately — never in plain JSON
    credential_ref: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    last_synced_at: Mapped[datetime | None] = mapped_column()

    organization: Mapped["Organization"] = relationship(back_populates="integrations")


# ── Context Engine: Entity Graph ──


class ContextEntity(TenantModel):
    """A node in the unified context graph — any piece of enterprise knowledge."""

    __tablename__ = "context_entities"

    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType, values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    source_integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="SET NULL")
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_id: Mapped[str | None] = mapped_column(String(500), index=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Vector embedding reference (stored in Weaviate, ID here for linking)
    vector_id: Mapped[str | None] = mapped_column(String(255))

    # Permissions inherited from source
    access_user_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    access_everyone: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class EntityRelation(TenantModel):
    """An edge in the context graph — connects two entities."""

    __tablename__ = "entity_relations"

    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("context_entities.id", ondelete="CASCADE"),
        index=True,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("context_entities.id", ondelete="CASCADE"),
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


# ── Conversations & Chat ──


class Conversation(TenantModel):
    __tablename__ = "conversations"

    title: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.created_at"
    )


class Message(TenantModel):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    model: Mapped[str | None] = mapped_column(String(100))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# ── Skills ──


class Skill(TenantModel):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Skill definition
    trigger: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    steps: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    required_context: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    output_schema: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Feedback
    upvotes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    downvotes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    execution_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


# ── Governance: Audit Log ──


class AuditLog(TenantModel):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, values_callable=lambda e: [m.value for m in e]), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    model_used: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(45))


# ── Token Budgets ──


class TokenBudget(TenantModel):
    __tablename__ = "token_budgets"

    scope: Mapped[str] = mapped_column(String(20), nullable=False)  # org, team, user
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Flow: Tasks ──


class Task(TenantModel):
    """A work item in Flow — synced from external tools or created manually/by AI."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.TODO,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, values_callable=lambda e: [m.value for m in e]),
        default=TaskPriority.MEDIUM,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource, values_callable=lambda e: [m.value for m in e]),
        default=TaskSource.MANUAL,
    )
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_id: Mapped[str | None] = mapped_column(String(500), index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    blockers: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    labels: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ── Pilot: Delegations ──


class Delegation(TenantModel):
    """An AI-proposed action in Pilot — awaiting human approval."""

    __tablename__ = "delegations"

    action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[DelegationStatus] = mapped_column(
        Enum(DelegationStatus, values_callable=lambda e: [m.value for m in e]),
        default=DelegationStatus.PENDING,
    )
    proposed_for_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_result: Mapped[dict | None] = mapped_column(JSONB)


# ── Waitlist ──


class WaitlistEntry(BaseModel):
    """Early access waitlist signup — no org/tenant scoping needed."""

    __tablename__ = "waitlist_entries"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
