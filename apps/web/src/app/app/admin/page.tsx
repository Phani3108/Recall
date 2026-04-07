"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import {
  admin,
  type AdminOverview,
  type AdminUserRow,
  type AdminActivityRow,
} from "@/lib/api";
import {
  Users,
  MessageSquare,
  Zap,
  DollarSign,
  Plug,
  Layers,
  Inbox,
  Activity,
  Shield,
  Loader2,
  Crown,
  Clock,
} from "lucide-react";

type Tab = "overview" | "users" | "activity";

export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [activity, setActivity] = useState<AdminActivityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [ov, us, ac] = await Promise.all([
        admin.overview(),
        admin.users(),
        admin.activity(100),
      ]);
      setOverview(ov);
      setUsers(us);
      setActivity(ac);
    } catch (err: any) {
      setError(err?.detail || "Access denied. Admin role required.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <div className="glass-card p-8 text-center">
          <Shield className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: "overview" as Tab, label: "Overview", icon: Activity },
    { id: "users" as Tab, label: "Users", icon: Users },
    { id: "activity" as Tab, label: "Activity Log", icon: Clock },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-6 h-6 text-[var(--accent)]" />
        <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-[var(--accent)]/20 text-[var(--accent)]">
          {user?.role}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white/5 rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.id
                ? "bg-[var(--accent)] text-white"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && overview && <OverviewTab overview={overview} />}
      {tab === "users" && <UsersTab users={users} />}
      {tab === "activity" && <ActivityTab activity={activity} />}
    </div>
  );
}

/* ── Overview Tab ── */
function OverviewTab({ overview }: { overview: AdminOverview }) {
  const stats = [
    { label: "Total Users", value: overview.total_users, icon: Users, color: "text-blue-400" },
    { label: "Conversations", value: overview.total_conversations, icon: MessageSquare, color: "text-green-400" },
    { label: "Tokens Used", value: overview.total_tokens_used.toLocaleString(), icon: Zap, color: "text-yellow-400" },
    { label: "Total Cost", value: `$${overview.total_cost_usd.toFixed(2)}`, icon: DollarSign, color: "text-emerald-400" },
    { label: "Integrations", value: overview.total_integrations, icon: Plug, color: "text-purple-400" },
    { label: "Tasks", value: overview.total_tasks, icon: Layers, color: "text-cyan-400" },
    { label: "Delegations", value: overview.total_delegations, icon: Inbox, color: "text-orange-400" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((s) => (
        <div key={s.label} className="glass-card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className={`p-2 rounded-lg bg-white/5 ${s.color}`}>
              <s.icon className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white">{s.value}</div>
          <div className="text-sm text-gray-400 mt-1">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Users Tab ── */
function UsersTab({ users }: { users: AdminUserRow[] }) {
  const roleColors: Record<string, string> = {
    owner: "text-yellow-400 bg-yellow-400/10",
    admin: "text-blue-400 bg-blue-400/10",
    member: "text-gray-400 bg-gray-400/10",
    guest: "text-gray-500 bg-gray-500/10",
  };

  return (
    <div className="glass-card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left text-xs font-medium text-gray-400 px-4 py-3">User</th>
            <th className="text-left text-xs font-medium text-gray-400 px-4 py-3">Email</th>
            <th className="text-left text-xs font-medium text-gray-400 px-4 py-3">Role</th>
            <th className="text-left text-xs font-medium text-gray-400 px-4 py-3">Status</th>
            <th className="text-left text-xs font-medium text-gray-400 px-4 py-3">Joined</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-xs text-[var(--accent)] font-bold">
                    {u.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm text-white font-medium">{u.name}</span>
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-400">{u.email}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${roleColors[u.role] || roleColors.member}`}>
                  {u.role === "owner" && <Crown className="w-3 h-3" />}
                  {u.role}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-block w-2 h-2 rounded-full ${u.is_active ? "bg-green-400" : "bg-red-400"}`} />
                <span className="text-sm text-gray-400 ml-2">{u.is_active ? "Active" : "Inactive"}</span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {users.length === 0 && (
        <div className="text-center py-8 text-gray-500">No users found.</div>
      )}
    </div>
  );
}

/* ── Activity Tab ── */
function ActivityTab({ activity }: { activity: AdminActivityRow[] }) {
  const actionColors: Record<string, string> = {
    ai_query: "text-blue-400",
    ai_response: "text-green-400",
    tool_call: "text-purple-400",
    delegation_proposed: "text-orange-400",
    delegation_approved: "text-green-400",
    delegation_rejected: "text-red-400",
    integration_connected: "text-cyan-400",
    integration_disconnected: "text-gray-400",
    data_accessed: "text-yellow-400",
  };

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return "just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="max-h-[600px] overflow-y-auto">
        {activity.map((a) => (
          <div
            key={a.id}
            className="flex items-start gap-4 px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs font-bold text-gray-400 flex-shrink-0">
              {a.user_name ? a.user_name.charAt(0).toUpperCase() : "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm text-white font-medium">
                  {a.user_name || "System"}
                </span>
                <span className={`text-xs font-mono ${actionColors[a.action] || "text-gray-400"}`}>
                  {a.action.replace(/_/g, " ")}
                </span>
              </div>
              {a.resource_type && (
                <span className="text-xs text-gray-500">
                  {a.resource_type}
                  {a.tokens_consumed > 0 && ` · ${a.tokens_consumed} tokens`}
                  {a.cost_usd > 0 && ` · $${a.cost_usd.toFixed(4)}`}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-600 flex-shrink-0">{formatTime(a.created_at)}</span>
          </div>
        ))}
        {activity.length === 0 && (
          <div className="text-center py-8 text-gray-500">No activity recorded yet.</div>
        )}
      </div>
    </div>
  );
}
