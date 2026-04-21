"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Zap,
  DollarSign,
  Plug,
  Users,
  Activity,
  Loader2,
  Lock,
  Trash2,
  CheckCircle,
  XCircle,
  BarChart3,
  Clock,
  Database,
  Download,
} from "lucide-react";
import {
  governance,
  type GovernanceDashboard,
  type AuditEntry,
  type RetentionStats,
  type SecurityStatus,
  type MetricsSnapshot,
} from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { isStrictApiMode } from "@/lib/strict-api";
import {
  demoDashboard,
  demoAuditLog,
  demoRetentionStats,
  demoSecurityStatus,
  demoMetrics,
} from "@/lib/demo-data";

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

function SecurityBadge({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className="flex items-center gap-2 py-2">
      {enabled ? (
        <CheckCircle className="w-4 h-4 text-green-400" />
      ) : (
        <XCircle className="w-4 h-4 text-red-400" />
      )}
      <span className="text-sm text-gray-300">{label}</span>
    </div>
  );
}

export default function GovernancePage() {
  const { isDemo, markBackendDown, setApiReachabilityError } = useDemo();
  const [dashboard, setDashboard] = useState<GovernanceDashboard | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [retention, setRetention] = useState<RetentionStats | null>(null);
  const [security, setSecurity] = useState<SecurityStatus | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "security" | "retention" | "metrics">("overview");

  useEffect(() => {
    if (isDemo) {
      setDashboard(demoDashboard);
      setAuditLog(demoAuditLog);
      setRetention(demoRetentionStats);
      setSecurity(demoSecurityStatus);
      setMetricsData(demoMetrics);
      setLoading(false);
      return;
    }
    Promise.all([
      governance.dashboard(),
      governance.auditLog(),
      governance.retentionStats().catch(() => demoRetentionStats),
      governance.securityStatus().catch(() => demoSecurityStatus),
      governance.metrics().catch(() => demoMetrics),
    ])
      .then(([d, a, r, s, m]) => {
        setDashboard(d);
        setAuditLog(a);
        setRetention(r);
        setSecurity(s);
        setMetricsData(m);
      })
      .catch(() => {
        if (isStrictApiMode()) {
          setApiReachabilityError(
            "Cannot reach the Recall API — check NEXT_PUBLIC_API_URL and that the backend is running.",
          );
        } else {
          markBackendDown();
          setDashboard(demoDashboard);
          setAuditLog(demoAuditLog);
          setRetention(demoRetentionStats);
          setSecurity(demoSecurityStatus);
          setMetricsData(demoMetrics);
        }
      })
      .finally(() => setLoading(false));
  }, [isDemo, markBackendDown, setApiReachabilityError]);

  const handleExportAudit = useCallback(async () => {
    if (isDemo) return;
    try {
      const blob = await governance.exportAuditJsonl();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "recall-audit.jsonl";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Audit export failed:", e);
    }
  }, [isDemo]);

  if (loading) {
    return (
      <div className="p-6 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  const tabs = [
    { key: "overview" as const, label: "Overview", icon: Activity },
    { key: "security" as const, label: "Security", icon: Lock },
    { key: "retention" as const, label: "Retention", icon: Trash2 },
    { key: "metrics" as const, label: "Metrics", icon: BarChart3 },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Governance</h1>
      <p className="text-gray-400 mb-6">
        Monitor AI usage, security posture, data retention, and system metrics.
      </p>

      {/* Tab bar */}
      <div className="flex gap-1 mb-8 bg-white/5 rounded-lg p-1 w-fit">
        {tabs.map(({ key, label, icon: TabIcon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${
              activeTab === key
                ? "bg-[var(--accent)] text-white"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <TabIcon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === "overview" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <StatCard icon={Zap} label="Conversations" value={dashboard?.total_conversations ?? 0} />
            <StatCard
              icon={Activity}
              label="Tokens Used"
              value={dashboard?.total_tokens_used ? `${(dashboard.total_tokens_used / 1000).toFixed(1)}k` : "0"}
              color="text-purple-400"
            />
            <StatCard
              icon={DollarSign}
              label="Total Cost"
              value={`$${(dashboard?.total_cost_usd ?? 0).toFixed(2)}`}
              color="text-green-400"
            />
            <StatCard icon={Plug} label="Integrations" value={dashboard?.active_integrations ?? 0} color="text-blue-400" />
            <StatCard
              icon={Users}
              label="Budget Used"
              value={`${(dashboard?.budget_utilization_pct ?? 0).toFixed(1)}%`}
              color="text-orange-400"
            />
          </div>

          <div className="glass-card p-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Shield className="w-5 h-5 text-[var(--accent)]" />
                Audit Log
              </h2>
              {!isDemo && (
                <button
                  type="button"
                  onClick={handleExportAudit}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/5 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export JSONL
                </button>
              )}
            </div>
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
        </>
      )}

      {/* ── Security Tab ── */}
      {activeTab === "security" && security && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-green-400" />
              Security Posture
            </h2>
            <SecurityBadge label="Rate Limiting" enabled={security.rate_limiting_enabled} />
            <SecurityBadge label="Security Headers (OWASP)" enabled={security.security_headers_enabled} />
            <SecurityBadge label="Credential Encryption" enabled={security.credential_encryption_enabled} />
            <SecurityBadge label="Token Budget Enforcement" enabled={security.token_budget_enforced} />
            <SecurityBadge label="Permission-Based Filtering" enabled={security.permission_filtering_enabled} />
            <SecurityBadge label="Metrics Collection" enabled={security.metrics_collection_enabled} />
            <SecurityBadge label="Secrets Masking" enabled={security.secrets_masked} />
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-[var(--accent)]" />
              Protection Layers
            </h2>
            <div className="space-y-3 text-sm text-gray-300">
              <div className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <span><strong className="text-white">Rate Limiting</strong> — 120 req/min API, 20 req/min AI, 10 req/min auth</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <span><strong className="text-white">HSTS</strong> — Strict-Transport-Security enforced (2 years)</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <span><strong className="text-white">Fernet Encryption</strong> — Integration tokens encrypted at rest</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <span><strong className="text-white">Access Control</strong> — Per-entity permission filtering on all queries</span>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <span><strong className="text-white">Token Budget</strong> — 429 enforcement on AI paths when budget exceeded</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Retention Tab ── */}
      {activeTab === "retention" && retention && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Database} label="Total Entities" value={retention.total_entities.toLocaleString()} color="text-blue-400" />
            <StatCard icon={Clock} label="Older than 90d" value={retention.entities_older_than_90d.toLocaleString()} color="text-yellow-400" />
            <StatCard icon={Trash2} label="Orphan Relations" value={retention.orphan_relations} color="text-red-400" />
            <StatCard icon={Activity} label="Audit Logs" value={retention.total_audit_logs.toLocaleString()} color="text-purple-400" />
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-yellow-400" />
              Retention Policy
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Current Configuration</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-gray-300">
                    <span>Entity retention</span>
                    <span className="text-white font-medium">{retention.entity_retention_days} days</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Audit log retention</span>
                    <span className="text-white font-medium">{retention.audit_retention_days} days</span>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Eligible for Purge</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-gray-300">
                    <span>Entities older than {retention.entity_retention_days}d</span>
                    <span className="text-yellow-400 font-medium">{retention.entities_older_than_90d}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Audit logs older than {retention.audit_retention_days}d</span>
                    <span className="text-yellow-400 font-medium">{retention.audit_logs_older_than_365d}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Orphan relations</span>
                    <span className="text-red-400 font-medium">{retention.orphan_relations}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Metrics Tab ── */}
      {activeTab === "metrics" && metricsData && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Activity} label="Total Requests" value={metricsData.total_requests.toLocaleString()} />
            <StatCard
              icon={Zap}
              label="Error Rate"
              value={`${(metricsData.error_rate * 100).toFixed(2)}%`}
              color={metricsData.error_rate > 0.01 ? "text-red-400" : "text-green-400"}
            />
            <StatCard
              icon={Clock}
              label="Uptime"
              value={`${Math.floor(metricsData.uptime_seconds / 3600)}h ${Math.floor((metricsData.uptime_seconds % 3600) / 60)}m`}
              color="text-blue-400"
            />
            <StatCard icon={BarChart3} label="AI Requests" value={metricsData.ai.total_requests.toLocaleString()} color="text-purple-400" />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="glass-card p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Top Endpoints</h2>
              <div className="space-y-2">
                {Object.entries(metricsData.top_endpoints).map(([endpoint, count]) => (
                  <div key={endpoint} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-400 truncate">{endpoint}</div>
                      <div className="h-1.5 bg-white/5 rounded-full mt-1 overflow-hidden">
                        <div
                          className="h-full bg-[var(--accent)] rounded-full"
                          style={{
                            width: `${(count / Math.max(...Object.values(metricsData.top_endpoints))) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                    <span className="text-xs text-white font-medium shrink-0">{count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Status Codes</h2>
              <div className="space-y-2">
                {Object.entries(metricsData.status_codes).map(([code, count]) => {
                  const codeNum = parseInt(code, 10);
                  const color =
                    codeNum < 300 ? "bg-green-400" : codeNum < 400 ? "bg-blue-400" : codeNum < 500 ? "bg-yellow-400" : "bg-red-400";
                  return (
                    <div key={code} className="flex items-center gap-3">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded ${color} text-black`}>{code}</span>
                      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${color} rounded-full`}
                          style={{
                            width: `${(count / Math.max(...Object.values(metricsData.status_codes))) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-white font-medium">{count.toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Latency Distribution</h2>
            <div className="flex items-end gap-1 h-32">
              {Object.entries(metricsData.latency.buckets).map(([bucket, count], i, arr) => {
                const prevCount = i > 0 ? Object.values(metricsData.latency.buckets)[i - 1] : 0;
                const sliceCount = count - prevCount;
                const maxSlice = Math.max(
                  ...arr.map(([, c], j) => c - (j > 0 ? Object.values(metricsData.latency.buckets)[j - 1] : 0)),
                  1,
                );
                return (
                  <div key={bucket} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-[var(--accent)] rounded-t opacity-80"
                      style={{ height: `${(sliceCount / maxSlice) * 100}%`, minHeight: sliceCount > 0 ? 2 : 0 }}
                    />
                    <span className="text-[10px] text-gray-500">{bucket}s</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 text-xs text-gray-400 text-center">
              Avg latency: {((metricsData.latency.sum / Math.max(metricsData.latency.count, 1)) * 1000).toFixed(0)}ms
              &nbsp;·&nbsp; p50 ≈ 50ms &nbsp;·&nbsp; {metricsData.latency.count.toLocaleString()} total
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
