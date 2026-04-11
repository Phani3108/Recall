/**
 * Recall API client — typed fetch wrapper with auth token management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Token Storage ──

const TOKEN_KEY = "recall_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ── API Types ──

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  is_active: boolean;
  role: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  token_budget_monthly: number | null;
  tokens_used_this_month: number;
  created_at: string;
}

export interface OrgMember {
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: string;
  joined_at: string;
}

export interface Integration {
  id: string;
  provider: string;
  status: string;
  connected_by: string;
  last_synced_at: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  user_id: string;
  is_shared: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources: Source[];
  tool_calls: unknown[];
  tokens_used: number;
  model: string | null;
  created_at: string;
}

export interface Source {
  entity_id: string;
  title: string;
  source_url: string;
  source_integration: string;
  relevance_score: number;
}

export interface ContextEntity {
  id: string;
  entity_type: string;
  title: string;
  content: string | null;
  source_url: string | null;
  metadata: Record<string, unknown>;
  relevance_score: number | null;
  created_at: string | null;
}

export interface ContextSearchResponse {
  results: ContextEntity[];
  total: number;
  query: string;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: Record<string, unknown>;
  tokens_consumed: number;
  cost_usd: number;
  model_used: string | null;
  created_at: string;
}

export interface GovernanceDashboard {
  total_tokens_used: number;
  total_cost_usd: number;
  active_integrations: number;
  total_conversations: number;
  total_skill_executions: number;
  budget_utilization_pct: number;
}

// ── Flow: Tasks ──

export interface FlowTask {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  source: string;
  source_url: string | null;
  source_id: string | null;
  ai_summary: string | null;
  blockers: string[];
  labels: string[];
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskStats {
  todo: number;
  in_progress: number;
  in_review: number;
  done: number;
  total: number;
}

// ── Pilot: Delegations ──

export interface DelegationItem {
  id: string;
  action: string;
  reason: string;
  tool: string;
  confidence: number;
  status: string;
  proposed_for_user_id: string;
  resolved_by_user_id: string | null;
  resolved_at: string | null;
  execution_result: Record<string, unknown> | null;
  created_at: string;
}

export interface DelegationStats {
  pending: number;
  approved: number;
  rejected: number;
  executed: number;
  total: number;
  approval_rate: number;
}

// ── Skills ──

export interface SkillItem {
  id: string;
  name: string;
  description: string;
  version: number;
  is_builtin: boolean;
  is_published: boolean;
  execution_count: number;
  upvotes: number;
  downvotes: number;
  created_at: string;
}

// ── API Error ──

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// ── Fetch Wrapper ──

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const data = await res.json();

  if (!res.ok) {
    throw new ApiError(res.status, data.detail || "Request failed");
  }

  return data as T;
}

// ── Auth ──

export const auth = {
  login: (email: string, password: string) =>
    apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, name: string, password: string, org_name: string) =>
    apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, name, password, org_name }),
    }),

  me: () => apiFetch<User>("/auth/me"),
};

// ── Organizations ──

export const orgs = {
  current: () => apiFetch<Organization>("/orgs/current"),
  members: () => apiFetch<OrgMember[]>("/orgs/members"),
};

// ── Integrations ──

export const integrations = {
  list: () => apiFetch<Integration[]>("/integrations/"),
  create: (provider: string) =>
    apiFetch<Integration>("/integrations/", {
      method: "POST",
      body: JSON.stringify({ provider }),
    }),
  connect: (id: string, config: Record<string, string>) =>
    apiFetch<{ status: string; synced: number; error: string | null }>(`/integrations/${id}/connect`, {
      method: "POST",
      body: JSON.stringify({ config }),
    }),
  sync: (id: string) =>
    apiFetch<{ status: string; synced: number; error: string | null }>(`/integrations/${id}/sync`, {
      method: "POST",
    }),
  disconnect: (id: string) =>
    apiFetch<{ status: string }>(`/integrations/${id}/disconnect`, {
      method: "POST",
    }),
  status: (id: string) =>
    apiFetch<{ status: string; provider: string }>(`/integrations/${id}/status`),
  delete: (id: string) =>
    apiFetch<void>(`/integrations/${id}`, { method: "DELETE" }),
  oauthUrl: (provider: string) =>
    apiFetch<{ auth_url: string }>(`/integrations/${provider}/oauth-url`),
  providerFields: () =>
    apiFetch<Record<string, {
      fields: Array<{ key: string; label: string; placeholder: string }>;
      help_url: string;
      auth_method: "oauth" | "api_key" | "coming_soon";
      oauth_configured: boolean;
    }>>("/integrations/providers/fields"),
};

// ── Context ──

export const context = {
  search: (query: string, entityTypes?: string[], limit = 20) =>
    apiFetch<ContextSearchResponse>("/context/search", {
      method: "POST",
      body: JSON.stringify({ query, entity_types: entityTypes, limit }),
    }),
};

// ── Chat / Agents ──

export const chat = {
  listConversations: () =>
    apiFetch<Conversation[]>("/agents/conversations"),

  createConversation: (title?: string) =>
    apiFetch<Conversation>("/agents/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),

  getMessages: (conversationId: string) =>
    apiFetch<Message[]>(`/agents/conversations/${conversationId}/messages`),

  sendMessage: (conversationId: string, content: string) =>
    apiFetch<Message>(`/agents/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  sendMessageStream: (conversationId: string, content: string) => {
    const token = getToken();
    return fetch(`${API_BASE}/agents/conversations/${conversationId}/messages/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    });
  },
};

// ── Flow: Tasks ──

export const flow = {
  listTasks: (filters?: { status?: string; priority?: string; assignee_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set("status", filters.status);
    if (filters?.priority) params.set("priority", filters.priority);
    if (filters?.assignee_id) params.set("assignee_id", filters.assignee_id);
    const qs = params.toString();
    return apiFetch<FlowTask[]>(`/flow/tasks${qs ? `?${qs}` : ""}`);
  },

  createTask: (task: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    assignee_id?: string;
    source?: string;
    source_url?: string;
    ai_summary?: string;
    blockers?: string[];
    labels?: string[];
  }) =>
    apiFetch<FlowTask>("/flow/tasks", {
      method: "POST",
      body: JSON.stringify(task),
    }),

  updateTask: (taskId: string, updates: Partial<FlowTask>) =>
    apiFetch<FlowTask>(`/flow/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    }),

  deleteTask: (taskId: string) =>
    apiFetch<void>(`/flow/tasks/${taskId}`, { method: "DELETE" }),

  stats: () => apiFetch<TaskStats>("/flow/tasks/stats/summary"),
};

// ── Pilot: Delegations ──

export const pilot = {
  listDelegations: (status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return apiFetch<DelegationItem[]>(`/pilot/delegations${qs}`);
  },

  createDelegation: (delegation: {
    action: string;
    reason: string;
    tool: string;
    confidence: number;
  }) =>
    apiFetch<DelegationItem>("/pilot/delegations", {
      method: "POST",
      body: JSON.stringify(delegation),
    }),

  approve: (delegationId: string) =>
    apiFetch<DelegationItem>(`/pilot/delegations/${delegationId}/approve`, {
      method: "POST",
    }),

  reject: (delegationId: string) =>
    apiFetch<DelegationItem>(`/pilot/delegations/${delegationId}/reject`, {
      method: "POST",
    }),

  undo: (delegationId: string) =>
    apiFetch<DelegationItem>(`/pilot/delegations/${delegationId}/undo`, {
      method: "POST",
    }),

  execute: (delegationId: string) =>
    apiFetch<{ success: boolean; action: string; message: string; url: string | null; data: Record<string, unknown> }>(
      `/pilot/delegations/${delegationId}/execute`,
      { method: "POST" },
    ),

  stats: () => apiFetch<DelegationStats>("/pilot/delegations/stats/summary"),
};

// ── Skills ──

export const skills = {
  list: (publishedOnly = false) =>
    apiFetch<SkillItem[]>(`/skills/?published_only=${publishedOnly}`),

  create: (skill: { name: string; description: string; steps?: object[]; trigger?: object }) =>
    apiFetch<SkillItem>("/skills/", {
      method: "POST",
      body: JSON.stringify(skill),
    }),

  vote: (skillId: string, direction: "up" | "down") =>
    apiFetch<{ upvotes: number; downvotes: number }>(
      `/skills/${skillId}/vote?direction=${direction}`,
      { method: "POST" },
    ),

  delete: (skillId: string) =>
    apiFetch<void>(`/skills/${skillId}`, { method: "DELETE" }),
};

// ── Governance ──

export const governance = {
  dashboard: () => apiFetch<GovernanceDashboard>("/governance/dashboard"),
  auditLog: (limit = 50, offset = 0) =>
    apiFetch<AuditEntry[]>(`/governance/audit-logs?limit=${limit}&offset=${offset}`),
};

// ── Users ──

export const users = {
  updateMe: (updates: { name?: string; avatar_url?: string }) =>
    apiFetch<User>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(updates),
    }),
  deleteMe: () =>
    apiFetch<void>("/users/me", { method: "DELETE" }),
};

// ── Org Settings (API Keys / License) ──

export interface PlatformKeys {
  openai_api_key: string | null;
  anthropic_api_key: string | null;
  composio_api_key: string | null;
}

export interface LicenseInfo {
  tier: string;
  license_key_set: boolean;
  valid_until: string | null;
}

export interface OrgSettings {
  id: string;
  name: string;
  slug: string;
  license: LicenseInfo;
  platform_keys: PlatformKeys;
  token_budget_monthly: number | null;
  tokens_used_this_month: number;
}

export const orgSettings = {
  get: () => apiFetch<OrgSettings>("/orgs/settings"),

  updatePlatformKeys: (keys: { openai_api_key?: string; anthropic_api_key?: string; composio_api_key?: string }) =>
    apiFetch<{ status: string; platform_keys: PlatformKeys }>("/orgs/settings/platform-keys", {
      method: "PUT",
      body: JSON.stringify(keys),
    }),

  removePlatformKey: (keyName: string) =>
    apiFetch<{ status: string }>(`/orgs/settings/platform-keys/${keyName}`, {
      method: "DELETE",
    }),

  activateLicense: (licenseKey: string) =>
    apiFetch<LicenseInfo>("/orgs/settings/activate-license", {
      method: "POST",
      body: JSON.stringify({ license_key: licenseKey }),
    }),
};

// ── Admin ──

export interface AdminOverview {
  total_users: number;
  total_orgs: number;
  total_conversations: number;
  total_tokens_used: number;
  total_cost_usd: number;
  total_integrations: number;
  total_tasks: number;
  total_delegations: number;
}

export interface AdminUserRow {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminActivityRow {
  id: string;
  user_email: string | null;
  user_name: string | null;
  action: string;
  resource_type: string | null;
  detail: Record<string, unknown>;
  tokens_consumed: number;
  cost_usd: number;
  created_at: string;
}

export const admin = {
  overview: () => apiFetch<AdminOverview>("/admin/overview"),
  users: () => apiFetch<AdminUserRow[]>("/admin/users"),
  activity: (limit = 100, offset = 0) =>
    apiFetch<AdminActivityRow[]>(`/admin/activity?limit=${limit}&offset=${offset}`),
};
