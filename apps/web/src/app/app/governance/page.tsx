"use client";

import { useState, useEffect } from "react";
import {
  Shield,
  Zap,
  DollarSign,
  Plug,
  Users,
  Activity,
  Loader2,
} from "lucide-react";
import { governance, type GovernanceDashboard, type AuditEntry } from "@/lib/api";

function StatCard({
  icon: Icon,
  label,
  value,
  color = "text-[var(--accent)]",
}: {
  icon: typeof Zap;
  label: string;
  value: string | number;
  color?: string;
}) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const actionLabels: Record<string, string> = {
    ai_query: "AI Query",
    ai_response: "AI Response",
    tool_call: "Tool Call",
    integration_connected: "Integration Connected",
    data_accessed: "Data Accessed",
  };

  return (
    <div className="flex items-center gap-4 py-3 border-b border-white/5 last:border-0">
      <div className="w-2 h-2 rounded-full bg-[var(--accent)]" />
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white">
          {actionLabels[entry.action] || entry.action}
        </div>
        <div className="text-xs text-gray-500">
          {entry.resource_type && `${entry.resource_type}`}
          {entry.model_used && ` · ${entry.model_used}`}
          {entry.tokens_consumed > 0 && ` · ${entry.tokens_consumed} tokens`}
        </div>
      </div>
      {entry.cost_usd > 0 && (
        <span className="text-xs text-gray-400">${entry.cost_usd.toFixed(4)}</span>
      )}
      <span className="text-xs text-gray-500 shrink-0">
        {new Date(entry.created_at).toLocaleTimeString()}
      </span>
    </div>
  );
}

export default function GovernancePage() {
  const [dashboard, setDashboard] = useState<GovernanceDashboard | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([governance.dashboard(), governance.auditLog()])
      .then(([d, a]) => {
        setDashboard(d);
        setAuditLog(a);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-6 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Governance</h1>
      <p className="text-gray-400 mb-8">
        Monitor AI usage, costs, and audit trail across your organization.
      </p>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard
          icon={Zap}
          label="Conversations"
          value={dashboard?.total_conversations ?? 0}
        />
        <StatCard
          icon={Activity}
          label="Tokens Used"
          value={
            dashboard?.total_tokens_used
              ? `${(dashboard.total_tokens_used / 1000).toFixed(1)}k`
              : "0"
          }
          color="text-purple-400"
        />
        <StatCard
          icon={DollarSign}
          label="Total Cost"
          value={`$${(dashboard?.total_cost_usd ?? 0).toFixed(2)}`}
          color="text-green-400"
        />
        <StatCard
          icon={Plug}
          label="Integrations"
          value={dashboard?.active_integrations ?? 0}
          color="text-blue-400"
        />
        <StatCard
          icon={Users}
          label="Budget Used"
          value={`${(dashboard?.budget_utilization_pct ?? 0).toFixed(1)}%`}
          color="text-orange-400"
        />
      </div>

      {/* Audit log */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-[var(--accent)]" />
          Audit Log
        </h2>
        <div>
          {auditLog.length === 0 ? (
            <div className="text-gray-400 text-sm py-8 text-center">
              No audit entries yet. Start chatting with Ask to generate activity.
            </div>
          ) : (
            auditLog.map((entry) => <AuditRow key={entry.id} entry={entry} />)
          )}
        </div>
      </div>
    </div>
  );
}
