"""Pydantic schemas for API request/response models."""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Shared ──


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


# ── Auth ──


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    org_name: str = Field(min_length=1, max_length=255)


# ── Organizations ──


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    token_budget_monthly: int | None
    tokens_used_this_month: int
    created_at: datetime


class OrgMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str
    role: str
    joined_at: datetime


# ── Users ──


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


# ── Integrations ──


class IntegrationCreate(BaseModel):
    provider: str


class IntegrationResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    connected_by: uuid.UUID
    last_synced_at: datetime | None
    created_at: datetime


# ── Context ──


class ContextSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    entity_types: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ContextEntityResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    title: str
    content: str | None
    source_url: str | None
    metadata: dict
    relevance_score: float | None = None
    created_at: datetime | None = None


class ContextSearchResponse(BaseModel):
    results: list[ContextEntityResponse]
    total: int
    query: str


# ── Conversations ──


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    user_id: uuid.UUID
    is_shared: bool
    created_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    sources: list
    tool_calls: list
    tokens_used: int
    model: str | None
    created_at: datetime


# ── Skills ──


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    steps: list[dict] = Field(default_factory=list)
    trigger: dict = Field(default_factory=dict)


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    version: int
    is_builtin: bool
    is_published: bool
    execution_count: int
    upvotes: int
    downvotes: int
    created_at: datetime


# ── Flow: Tasks ──


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: uuid.UUID | None = None
    source: str = "manual"
    source_url: str | None = None
    source_id: str | None = None
    ai_summary: str | None = None
    blockers: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None
    ai_summary: str | None = None
    blockers: list[str] | None = None
    labels: list[str] | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: uuid.UUID | None
    source: str
    source_url: str | None
    source_id: str | None
    ai_summary: str | None
    blockers: list
    labels: list
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Pilot: Delegations ──


class DelegationCreate(BaseModel):
    action: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    tool: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    proposed_for_user_id: uuid.UUID | None = None


class DelegationResponse(BaseModel):
    id: uuid.UUID
    action: str
    reason: str
    tool: str
    confidence: float
    status: str
    proposed_for_user_id: uuid.UUID
    resolved_by_user_id: uuid.UUID | None
    resolved_at: datetime | None
    execution_result: dict | None
    created_at: datetime


# ── Governance ──


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    detail: dict
    tokens_consumed: int
    cost_usd: float
    model_used: str | None
    created_at: datetime


class TokenBudgetResponse(BaseModel):
    scope: str
    scope_id: uuid.UUID
    monthly_limit: int
    tokens_used: int
    period_start: datetime
    utilization_pct: float


class GovernanceDashboard(BaseModel):
    total_tokens_used: int
    total_cost_usd: float
    active_integrations: int
    total_conversations: int
    total_skill_executions: int
    budget_utilization_pct: float
