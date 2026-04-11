"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
  Zap,
  Check,
  X,
  Eye,
  Loader2,
  AlertTriangle,
  GitPullRequest,
  Ticket,
  Clock,
  TrendingUp,
  Settings,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Brain,
  Shield,
} from "lucide-react";
import {
  agentLoop,
  type AgentProposal,
  type AgentStats,
  type AgentConfigData,
} from "@/lib/api";
import { useDemo } from "@/lib/demo";
import {
  demoAgentProposals,
  demoAgentStats,
  demoAgentConfig,
} from "@/lib/demo-data";

/* ── Pattern display config ── */

const PATTERN_META: Record<
  string,
  { icon: typeof Bot; label: string; color: string }
> = {
  stale_pr: { icon: GitPullRequest, label: "Stale PR", color: "#f59e0b" },
  blocked_ticket: { icon: AlertTriangle, label: "Blocked", color: "#ef4444" },
  missed_deadline: { icon: Clock, label: "Overdue", color: "#dc2626" },
  unreviewed_pr: { icon: Eye, label: "Needs Review", color: "#8b5cf6" },
  idle_sprint_item: { icon: Ticket, label: "Idle", color: "#6366f1" },
  knowledge_gap: { icon: Brain, label: "Knowledge Gap", color: "#06b6d4" },
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400",
  high: "bg-orange-500/20 text-orange-400",
  medium: "bg-yellow-500/20 text-yellow-400",
  low: "bg-gray-500/20 text-gray-400",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-blue-500/20 text-blue-400",
  approved: "bg-green-500/20 text-green-400",
  rejected: "bg-red-500/20 text-red-400",
  dismissed: "bg-gray-500/20 text-gray-400",
  executed: "bg-emerald-500/20 text-emerald-400",
};

/* ── Stat card ── */

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
        <div
          className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center ${color}`}
        >
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  );
}

/* ── Proposal card ── */

function ProposalCard({
  proposal,
  onApprove,
  onReject,
  onDismiss,
}: {
  proposal: AgentProposal;
  onApprove: () => void;
  onReject: () => void;
  onDismiss: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = PATTERN_META[proposal.pattern_type] || {
    icon: Bot,
    label: proposal.pattern_type,
    color: "#6b7280",
  };
  const Icon = meta.icon;
  const isPending = proposal.status === "pending";
  const ctx = proposal.context_snapshot || {};

  return (
    <div className="glass-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: meta.color + "25" }}
        >
          <Icon className="w-4 h-4" style={{ color: meta.color }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider"
              style={{ background: meta.color + "25", color: meta.color }}
            >
              {meta.label}
            </span>
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider ${
                PRIORITY_COLORS[proposal.priority] || ""
              }`}
            >
              {proposal.priority}
            </span>
            <span
              className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wider ${
                STATUS_COLORS[proposal.status] || ""
              }`}
            >
              {proposal.status}
            </span>
          </div>
          <h3 className="text-sm font-semibold text-white mt-1 leading-snug">
            {proposal.title}
          </h3>
          <p className="text-xs text-gray-400 mt-1">{proposal.description}</p>
        </div>

        <div className="text-[10px] text-gray-500 shrink-0">
          {Math.round(proposal.confidence * 100)}% conf
        </div>
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        Suggested action
      </button>

      {expanded && (
        <div className="text-xs text-gray-300 bg-white/5 rounded-lg p-3 leading-relaxed">
          {proposal.suggested_action}
          {typeof ctx.source_url === "string" && ctx.source_url && (
            <a
              href={ctx.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[var(--accent)] hover:underline mt-2"
            >
              <ExternalLink className="w-3 h-3" />
              View source
            </a>
          )}
        </div>
      )}

      {/* Actions */}
      {isPending && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={onApprove}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 text-xs font-medium transition-colors"
          >
            <Check className="w-3 h-3" />
            Approve
          </button>
          <button
            onClick={onReject}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 text-xs font-medium transition-colors"
          >
            <X className="w-3 h-3" />
            Reject
          </button>
          <button
            onClick={onDismiss}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-gray-400 hover:bg-white/10 text-xs transition-colors ml-auto"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Learning panel ── */

function LearningPanel({ stats }: { stats: AgentStats }) {
  const learning = stats.learning;
  return (
    <div className="glass-card p-4 space-y-3">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
        <Brain className="w-4 h-4 text-purple-400" />
        Learning Progress
      </h3>
      <p className="text-xs text-gray-400">
        {learning.total_feedback} feedback signals ·{" "}
        {Math.round(learning.overall_approval_rate * 100)}% overall approval rate
      </p>
      <div className="space-y-2">
        {Object.entries(learning.patterns).map(([pattern, data]) => {
          const meta = PATTERN_META[pattern];
          const rate = Math.round(data.approval_rate * 100);
          return (
            <div key={pattern} className="flex items-center gap-3">
              <span className="text-xs text-gray-400 w-28 truncate">
                {meta?.label || pattern}
              </span>
              <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${rate}%`,
                    background:
                      rate >= 70
                        ? "#10b981"
                        : rate >= 40
                          ? "#f59e0b"
                          : "#ef4444",
                  }}
                />
              </div>
              <span className="text-xs text-gray-300 w-16 text-right">
                {rate}% ({data.total})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Main page ── */

export default function AgentPage() {
  const { isDemo } = useDemo();

  const [proposals, setProposals] = useState<AgentProposal[]>([]);
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [config, setConfig] = useState<AgentConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [showConfig, setShowConfig] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (isDemo) {
        const filtered = statusFilter
          ? demoAgentProposals.filter((p) => p.status === statusFilter)
          : demoAgentProposals;
        setProposals(filtered);
        setStats(demoAgentStats);
        setConfig(demoAgentConfig);
      } else {
        const [p, s, c] = await Promise.all([
          agentLoop.proposals(statusFilter || undefined),
          agentLoop.stats(),
          agentLoop.config(),
        ]);
        setProposals(p);
        setStats(s);
        setConfig(c);
      }
    } catch {
      setProposals(
        statusFilter
          ? demoAgentProposals.filter((p) => p.status === statusFilter)
          : demoAgentProposals,
      );
      setStats(demoAgentStats);
      setConfig(demoAgentConfig);
    } finally {
      setLoading(false);
    }
  }, [isDemo, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAction = async (
    id: string,
    action: "approve" | "reject" | "dismiss",
  ) => {
    if (isDemo) {
      setProposals((prev) =>
        prev.map((p) =>
          p.id === id
            ? { ...p, status: action === "approve" ? "approved" : action === "reject" ? "rejected" : "dismissed" }
            : p,
        ),
      );
      return;
    }
    try {
      if (action === "approve") await agentLoop.approve(id);
      else if (action === "reject") await agentLoop.reject(id);
      else await agentLoop.dismiss(id);
      await fetchData();
    } catch {
      /* swallow */
    }
  };

  const handleScan = async () => {
    if (isDemo) return;
    setScanning(true);
    try {
      await agentLoop.scan();
      await fetchData();
    } finally {
      setScanning(false);
    }
  };

  const pendingCount = isDemo
    ? demoAgentProposals.filter((p) => p.status === "pending").length
    : stats?.by_status?.pending ?? 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="w-6 h-6 text-[var(--accent)]" />
            Autonomous Agent
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Observes your engineering workflow and proposes actions. Learns from
            your approvals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={handleScan}
            disabled={scanning || isDemo}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)]/20 text-[var(--accent)] hover:bg-[var(--accent)]/30 transition-colors disabled:opacity-40"
          >
            <RefreshCw
              className={`w-4 h-4 ${scanning ? "animate-spin" : ""}`}
            />
            {scanning ? "Scanning…" : "Run Scan"}
          </button>
        </div>
      </div>

      {/* Config panel */}
      {showConfig && config && (
        <div className="glass-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Settings className="w-4 h-4 text-gray-400" />
            Agent Configuration
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-gray-500">Mode</span>
              <div className="text-white font-medium capitalize">{config.mode}</div>
            </div>
            <div>
              <span className="text-gray-500">Status</span>
              <div className={`font-medium ${config.enabled ? "text-green-400" : "text-red-400"}`}>
                {config.enabled ? "Enabled" : "Disabled"}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Min Confidence</span>
              <div className="text-white font-medium">{Math.round(config.confidence_threshold * 100)}%</div>
            </div>
            <div>
              <span className="text-gray-500">Auto-approve Above</span>
              <div className="text-white font-medium">{Math.round(config.auto_approve_threshold * 100)}%</div>
            </div>
          </div>
          <div>
            <span className="text-xs text-gray-500">Active Patterns</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {config.patterns_enabled.map((p) => (
                <span
                  key={p}
                  className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-gray-300"
                >
                  {PATTERN_META[p]?.label || p}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={Bot}
            label="Total Proposals"
            value={stats.total_proposals}
          />
          <StatCard
            icon={AlertTriangle}
            label="Pending Review"
            value={pendingCount}
            color="text-yellow-400"
          />
          <StatCard
            icon={TrendingUp}
            label="Approval Rate"
            value={`${stats.approval_rate}%`}
            color="text-green-400"
          />
          <StatCard
            icon={Shield}
            label="Learning Signals"
            value={stats.learning.total_feedback}
            color="text-purple-400"
          />
        </div>
      )}

      {/* Learning panel */}
      {stats && stats.learning.total_feedback > 0 && (
        <LearningPanel stats={stats} />
      )}

      {/* Filter tabs + proposals */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          {["pending", "approved", "rejected", "dismissed", ""].map((s) => (
            <button
              key={s || "all"}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                  : "text-gray-400 hover:text-white bg-white/5 hover:bg-white/10"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>

        {proposals.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <Bot className="w-10 h-10 mx-auto mb-3 text-gray-600" />
            <p className="text-sm text-gray-400">
              {statusFilter === "pending"
                ? "No pending proposals. Run a scan or wait for the next sync cycle."
                : "No proposals match this filter."}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {proposals.map((p) => (
              <ProposalCard
                key={p.id}
                proposal={p}
                onApprove={() => handleAction(p.id, "approve")}
                onReject={() => handleAction(p.id, "reject")}
                onDismiss={() => handleAction(p.id, "dismiss")}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
