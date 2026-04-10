/**
 * Demo data layer — realistic mock content for all pages.
 * Allows the frontend to render rich UI without a running backend.
 */

import type {
  User,
  Organization,
  OrgMember,
  Integration,
  Conversation,
  Message,
  Source,
  ContextEntity,
  ContextSearchResponse,
  AuditEntry,
  GovernanceDashboard,
  FlowTask,
  TaskStats,
  DelegationItem,
  DelegationStats,
  SkillItem,
  AdminOverview,
  AdminUserRow,
  AdminActivityRow,
  OrgSettings,
} from "./api";

// ── Helpers ──

const id = (prefix: string, n: number) => `${prefix}-${String(n).padStart(4, "0")}`;
const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();

// ── User & Org ──

export const demoUser: User = {
  id: id("usr", 1),
  email: "alex@acme.dev",
  name: "Alex Chen",
  avatar_url: null,
  is_active: true,
  role: "owner",
  created_at: ago(60 * 24 * 30),
};

export const demoOrg: Organization = {
  id: id("org", 1),
  name: "Acme Engineering",
  slug: "acme-eng",
  logo_url: null,
  token_budget_monthly: 500_000,
  tokens_used_this_month: 123_456,
  created_at: ago(60 * 24 * 60),
};

export const demoMembers: OrgMember[] = [
  { id: id("mem", 1), user_id: id("usr", 1), email: "alex@acme.dev", name: "Alex Chen", role: "owner", joined_at: ago(60 * 24 * 60) },
  { id: id("mem", 2), user_id: id("usr", 2), email: "sara@acme.dev", name: "Sara Kim", role: "admin", joined_at: ago(60 * 24 * 45) },
  { id: id("mem", 3), user_id: id("usr", 3), email: "james@acme.dev", name: "James Park", role: "member", joined_at: ago(60 * 24 * 20) },
  { id: id("mem", 4), user_id: id("usr", 4), email: "lin@acme.dev", name: "Lin Wei", role: "member", joined_at: ago(60 * 24 * 10) },
  { id: id("mem", 5), user_id: id("usr", 5), email: "maya@acme.dev", name: "Maya Rodriguez", role: "guest", joined_at: ago(60 * 24 * 3) },
];

// ── Integrations ──

export const demoIntegrations: Integration[] = [
  { id: id("int", 1), provider: "slack", status: "connected", connected_by: id("usr", 1), last_synced_at: ago(15), created_at: ago(60 * 24 * 30) },
  { id: id("int", 2), provider: "github", status: "connected", connected_by: id("usr", 1), last_synced_at: ago(5), created_at: ago(60 * 24 * 28) },
  { id: id("int", 3), provider: "notion", status: "connected", connected_by: id("usr", 2), last_synced_at: ago(60), created_at: ago(60 * 24 * 20) },
  { id: id("int", 4), provider: "jira", status: "connected", connected_by: id("usr", 2), last_synced_at: ago(30), created_at: ago(60 * 24 * 15) },
  { id: id("int", 5), provider: "linear", status: "pending", connected_by: id("usr", 3), last_synced_at: null, created_at: ago(60 * 2) },
];

// ── Conversations & Messages ──

export const demoConversations: Conversation[] = [
  { id: id("conv", 1), title: "Q3 sprint planning summary", user_id: id("usr", 1), is_shared: false, created_at: ago(30) },
  { id: id("conv", 2), title: "API rate limiting discussion", user_id: id("usr", 1), is_shared: false, created_at: ago(120) },
  { id: id("conv", 3), title: "Customer feedback analysis", user_id: id("usr", 1), is_shared: true, created_at: ago(60 * 24) },
];

export const demoMessages: Record<string, Message[]> = {
  [id("conv", 1)]: [
    {
      id: id("msg", 1), role: "user", content: "Summarize what was discussed in the #engineering channel about the Q3 sprint planning",
      sources: [], tool_calls: [], tokens_used: 0, model: null, created_at: ago(28),
    },
    {
      id: id("msg", 2), role: "assistant",
      content: "Based on the #engineering Slack channel discussions from the past week, here's a summary of Q3 sprint planning:\n\n**Key Decisions:**\n1. **Auth migration** — Moving from session-based to JWT tokens. Sara is leading this, estimated 2 sprints.\n2. **API v2 rollout** — James proposed a phased rollout with feature flags. Team agreed on gradual migration.\n3. **Performance improvements** — Lin identified 3 slow queries in the dashboard. Added to sprint backlog.\n\n**Open Items:**\n- Need product sign-off on the new onboarding flow\n- CI pipeline optimization blocked on DevOps team availability\n- Design review for settings page scheduled for Thursday",
      sources: [
        { entity_id: id("ent", 1), title: "#engineering — Sprint Planning Thread", source_url: "https://slack.com/archives/C01/p123", source_integration: "slack", relevance_score: 0.95 },
        { entity_id: id("ent", 2), title: "Q3 Sprint Board", source_url: "https://linear.app/acme/project/q3", source_integration: "linear", relevance_score: 0.88 },
        { entity_id: id("ent", 3), title: "Auth Migration RFC", source_url: "https://notion.so/acme/auth-rfc", source_integration: "notion", relevance_score: 0.82 },
      ],
      tool_calls: [], tokens_used: 847, model: "gpt-4o", created_at: ago(27),
    },
    {
      id: id("msg", 3), role: "user", content: "What are the blockers James mentioned?",
      sources: [], tool_calls: [], tokens_used: 0, model: null, created_at: ago(25),
    },
    {
      id: id("msg", 4), role: "assistant",
      content: "James mentioned two specific blockers in the sprint planning thread:\n\n1. **CI Pipeline Bottleneck** — Build times have increased to ~18 minutes due to the new integration test suite. The DevOps team needs to set up parallel runners but they're occupied with the infrastructure migration until next Tuesday.\n\n2. **Third-party API Deprecation** — The payment provider is deprecating their v1 API on July 15th. James created a Jira ticket (ACME-2847) for the migration but it requires changes across 3 services and hasn't been scheduled yet.\n\nHe suggested addressing the CI issue asynchronously and flagging the payment API migration as high priority in the next sprint.",
      sources: [
        { entity_id: id("ent", 4), title: "ACME-2847: Payment API migration", source_url: "https://acme.atlassian.net/browse/ACME-2847", source_integration: "jira", relevance_score: 0.93 },
        { entity_id: id("ent", 1), title: "#engineering — Sprint Planning Thread", source_url: "https://slack.com/archives/C01/p456", source_integration: "slack", relevance_score: 0.87 },
      ],
      tool_calls: [], tokens_used: 623, model: "gpt-4o", created_at: ago(24),
    },
  ],
};

// ── Flow: Tasks ──

export const demoTasks: FlowTask[] = [
  {
    id: id("task", 1), title: "Migrate payment provider to v2 API", description: "Payment provider deprecating v1 on July 15. Affects billing, subscriptions, and checkout services.",
    status: "in_progress", priority: "critical", assignee_id: id("usr", 3), source: "jira", source_url: "https://acme.atlassian.net/browse/ACME-2847", source_id: "ACME-2847",
    ai_summary: "3 services affected. James started billing service migration. Checkout and subscription services remain.", blockers: ["Needs staging payment sandbox credentials"], labels: ["payments", "deadline"], due_date: ago(-60 * 24 * 5), created_at: ago(60 * 24 * 3), updated_at: ago(60 * 2),
  },
  {
    id: id("task", 2), title: "Implement JWT auth token rotation", description: "Replace session-based auth with JWT + refresh token rotation for all API endpoints.",
    status: "in_progress", priority: "high", assignee_id: id("usr", 2), source: "linear", source_url: "https://linear.app/acme/issue/ACM-142", source_id: "ACM-142",
    ai_summary: "Sara has completed the token generation and validation layer. Middleware integration next.", blockers: [], labels: ["auth", "security"], due_date: ago(-60 * 24 * 10), created_at: ago(60 * 24 * 7), updated_at: ago(60 * 4),
  },
  {
    id: id("task", 3), title: "Optimize dashboard slow queries", description: "Three queries in the analytics dashboard take >2s. Need indexing and query rewrite.",
    status: "todo", priority: "high", assignee_id: id("usr", 4), source: "github", source_url: "https://github.com/acme/core/issues/312", source_id: "#312",
    ai_summary: "Lin identified N+1 query in user activity feed, missing composite index on events table, and unoptimized aggregation in metrics endpoint.", blockers: [], labels: ["performance", "database"], due_date: null, created_at: ago(60 * 24 * 2), updated_at: ago(60 * 24),
  },
  {
    id: id("task", 4), title: "Design review: Settings page redesign", description: "Review new settings page mockups from design team.",
    status: "in_review", priority: "medium", assignee_id: id("usr", 1), source: "notion", source_url: "https://notion.so/acme/settings-redesign", source_id: null,
    ai_summary: "Design team submitted 3 variants. Team leaning toward Option B with sidebar navigation.", blockers: [], labels: ["design", "ux"], due_date: ago(-60 * 24 * 2), created_at: ago(60 * 24 * 5), updated_at: ago(60 * 12),
  },
  {
    id: id("task", 5), title: "Set up CI parallel test runners", description: "Reduce CI build time from 18min to under 8min.",
    status: "todo", priority: "medium", assignee_id: null, source: "manual", source_url: null, source_id: null,
    ai_summary: "Blocked until DevOps completes infra migration (estimated next Tuesday).", blockers: ["DevOps team availability"], labels: ["devops", "ci"], due_date: null, created_at: ago(60 * 24), updated_at: ago(60 * 24),
  },
  {
    id: id("task", 6), title: "Add rate limiting to public API", description: "Implement token bucket rate limiter for all public-facing endpoints.",
    status: "todo", priority: "medium", assignee_id: id("usr", 3), source: "github", source_url: "https://github.com/acme/core/issues/298", source_id: "#298",
    ai_summary: null, blockers: [], labels: ["api", "security"], due_date: null, created_at: ago(60 * 24 * 4), updated_at: ago(60 * 24 * 3),
  },
  {
    id: id("task", 7), title: "Customer onboarding flow v2", description: "New onboarding flow with progressive profiling and tool connections.",
    status: "done", priority: "high", assignee_id: id("usr", 2), source: "linear", source_url: "https://linear.app/acme/issue/ACM-128", source_id: "ACM-128",
    ai_summary: "Shipped in v2.3.0. Conversion rate improved by 23%.", blockers: [], labels: ["onboarding", "growth"], due_date: ago(60 * 24 * 2), created_at: ago(60 * 24 * 14), updated_at: ago(60 * 24 * 2),
  },
];

export const demoTaskStats: TaskStats = {
  todo: 3, in_progress: 2, in_review: 1, done: 1, total: 7,
};

// ── Pilot: Delegations ──

export const demoDelegations: DelegationItem[] = [
  {
    id: id("del", 1), action: "Schedule a 30-min sync with Sara about the auth migration timeline",
    reason: "Sara's JWT implementation is ahead of schedule. A sync could unblock the middleware integration sooner.",
    tool: "Google Calendar", confidence: 0.92, status: "pending", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: null, resolved_at: null, execution_result: null, created_at: ago(15),
  },
  {
    id: id("del", 2), action: "Move ACME-2847 to 'In Review' and notify James",
    reason: "James pushed the billing service migration branch and all CI checks have passed.",
    tool: "Jira", confidence: 0.88, status: "pending", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: null, resolved_at: null, execution_result: null, created_at: ago(45),
  },
  {
    id: id("del", 3), action: "Post weekly engineering digest to #engineering",
    reason: "It's Friday 4 PM. The team has a weekly digest tradition. Summary of 7 PRs merged, 2 incidents resolved, and 3 new issues created this week.",
    tool: "Slack", confidence: 0.95, status: "pending", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: null, resolved_at: null, execution_result: null, created_at: ago(60),
  },
  {
    id: id("del", 4), action: "Create GitHub issue for updating API docs after v2 auth changes",
    reason: "The auth migration will change 12 API endpoints. Documentation should be updated before the rollout.",
    tool: "GitHub", confidence: 0.85, status: "approved", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: id("usr", 1), resolved_at: ago(120), execution_result: { issue_url: "https://github.com/acme/docs/issues/89" }, created_at: ago(180),
  },
  {
    id: id("del", 5), action: "Flag CI build time degradation in #devops",
    reason: "Average build time increased from 12min to 18min over the past 5 days. DevOps team should be aware.",
    tool: "Slack", confidence: 0.91, status: "executed", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: id("usr", 1), resolved_at: ago(60 * 24), execution_result: { message_ts: "1234567890.123456" }, created_at: ago(60 * 25),
  },
  {
    id: id("del", 6), action: "Reject the auto-merge on PR #387 (needs security review)",
    reason: "PR #387 modifies authentication middleware but hasn't been reviewed by Sara (security lead).",
    tool: "GitHub", confidence: 0.82, status: "rejected", proposed_for_user_id: id("usr", 1),
    resolved_by_user_id: id("usr", 1), resolved_at: ago(60 * 3), execution_result: null, created_at: ago(60 * 4),
  },
];

export const demoDelegationStats: DelegationStats = {
  pending: 3, approved: 1, rejected: 1, executed: 1, total: 6, approval_rate: 0.67,
};

// ── Governance ──

export const demoDashboard: GovernanceDashboard = {
  total_tokens_used: 123_456,
  total_cost_usd: 18.42,
  active_integrations: 4,
  total_conversations: 47,
  total_skill_executions: 23,
  budget_utilization_pct: 24.7,
};

export const demoAuditLog: AuditEntry[] = [
  { id: id("aud", 1), user_id: id("usr", 1), action: "ai_query", resource_type: "conversation", resource_id: id("conv", 1), detail: { query_length: 42 }, tokens_consumed: 847, cost_usd: 0.0127, model_used: "gpt-4o", created_at: ago(27) },
  { id: id("aud", 2), user_id: id("usr", 1), action: "ai_query", resource_type: "conversation", resource_id: id("conv", 1), detail: { query_length: 28 }, tokens_consumed: 623, cost_usd: 0.0093, model_used: "gpt-4o", created_at: ago(24) },
  { id: id("aud", 3), user_id: id("usr", 2), action: "integration_connected", resource_type: "integration", resource_id: id("int", 3), detail: { provider: "notion" }, tokens_consumed: 0, cost_usd: 0, model_used: null, created_at: ago(60) },
  { id: id("aud", 4), user_id: id("usr", 3), action: "tool_call", resource_type: "delegation", resource_id: id("del", 5), detail: { tool: "slack", action: "post_message" }, tokens_consumed: 156, cost_usd: 0.0023, model_used: "gpt-4o-mini", created_at: ago(60 * 24) },
  { id: id("aud", 5), user_id: id("usr", 1), action: "data_accessed", resource_type: "context_entity", resource_id: id("ent", 1), detail: { entity_type: "message" }, tokens_consumed: 0, cost_usd: 0, model_used: null, created_at: ago(60 * 24 * 2) },
  { id: id("aud", 6), user_id: id("usr", 4), action: "ai_query", resource_type: "conversation", resource_id: id("conv", 3), detail: { query_length: 65 }, tokens_consumed: 1230, cost_usd: 0.0185, model_used: "gpt-4o", created_at: ago(60 * 24 * 2) },
];

// ── Context Search ──

export const demoSearchResults: ContextEntity[] = [
  { id: id("ent", 1), entity_type: "message", title: "#engineering — Sprint Planning Thread", content: "Sara: JWT implementation is ahead of schedule. I'll have the middleware integration ready by Wednesday.", source_url: "https://slack.com/archives/C01/p123", metadata: {}, relevance_score: 0.95, created_at: ago(60 * 24) },
  { id: id("ent", 2), entity_type: "task", title: "ACME-2847: Migrate payment provider to v2 API", content: "Payment provider deprecating v1 on July 15. Affects billing, subscriptions, and checkout services.", source_url: "https://acme.atlassian.net/browse/ACME-2847", metadata: {}, relevance_score: 0.88, created_at: ago(60 * 24 * 3) },
  { id: id("ent", 3), entity_type: "document", title: "Auth Migration RFC", content: "This RFC proposes migrating from session-based authentication to JWT tokens with refresh token rotation.", source_url: "https://notion.so/acme/auth-rfc", metadata: {}, relevance_score: 0.82, created_at: ago(60 * 24 * 7) },
  { id: id("ent", 4), entity_type: "document", title: "Q3 OKRs — Engineering", content: "Objective: Improve platform reliability to 99.9% uptime. Key Results: Reduce p95 latency below 200ms, Zero critical incidents.", source_url: "https://notion.so/acme/q3-okrs", metadata: {}, relevance_score: 0.75, created_at: ago(60 * 24 * 14) },
  { id: id("ent", 5), entity_type: "person", title: "Sara Kim", content: "Engineering lead. Owns auth, security, and API infrastructure.", source_url: null, metadata: {}, relevance_score: 0.70, created_at: ago(60 * 24 * 45) },
];

// ── Admin ──

export const demoAdminOverview: AdminOverview = {
  total_users: 5,
  total_orgs: 1,
  total_conversations: 47,
  total_tokens_used: 123_456,
  total_cost_usd: 18.42,
  total_integrations: 5,
  total_tasks: 7,
  total_delegations: 6,
};

export const demoAdminUsers: AdminUserRow[] = demoMembers.map((m) => ({
  id: m.user_id,
  email: m.email,
  name: m.name,
  role: m.role,
  is_active: true,
  created_at: m.joined_at,
}));

export const demoAdminActivity: AdminActivityRow[] = demoAuditLog.map((a) => ({
  id: a.id,
  user_email: demoMembers.find((m) => m.user_id === a.user_id)?.email ?? null,
  user_name: demoMembers.find((m) => m.user_id === a.user_id)?.name ?? null,
  action: a.action,
  resource_type: a.resource_type,
  detail: a.detail,
  tokens_consumed: a.tokens_consumed,
  cost_usd: a.cost_usd,
  created_at: a.created_at,
}));

// ── Settings ──

export const demoOrgSettings: OrgSettings = {
  id: demoOrg.id,
  name: demoOrg.name,
  slug: demoOrg.slug,
  token_budget_monthly: demoOrg.token_budget_monthly,
  tokens_used_this_month: demoOrg.tokens_used_this_month,
  platform_keys: {
    openai_api_key: "sk-••••••••••••••••3aB7",
    anthropic_api_key: null,
    composio_api_key: null,
  },
  license: {
    tier: "team",
    license_key_set: false,
    valid_until: null,
  },
};

// ── Skills ──

export const demoSkills: SkillItem[] = [
  { id: id("skill", 1), name: "Standup Summary", description: "Generates a daily standup summary from Slack messages and Jira updates.", version: 3, is_builtin: true, is_published: true, execution_count: 142, upvotes: 12, downvotes: 1, created_at: ago(60 * 24 * 30) },
  { id: id("skill", 2), name: "PR Review Digest", description: "Summarizes open pull requests with review status, age, and suggested reviewers.", version: 2, is_builtin: false, is_published: true, execution_count: 67, upvotes: 8, downvotes: 0, created_at: ago(60 * 24 * 14) },
  { id: id("skill", 3), name: "Incident Response", description: "Coordinates incident response by notifying on-call, creating war room, and drafting status page update.", version: 1, is_builtin: true, is_published: true, execution_count: 5, upvotes: 4, downvotes: 0, created_at: ago(60 * 24 * 7) },
];
