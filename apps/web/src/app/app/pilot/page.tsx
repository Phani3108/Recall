"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
  Undo2,
  Zap,
  TrendingUp,
  Loader2,
  Play,
  ExternalLink,
  AlertCircle,
} from "lucide-react";
import { pilot, type DelegationItem } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoDelegations } from "@/lib/demo-data";

function formatTimeAgo(dateString: string): string {
  const diff = Date.now() - new Date(dateString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs > 1 ? "s" : ""} ago`;
  const days = Math.floor(hrs / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 90
      ? "text-green-400 bg-green-400/10"
      : pct >= 80
        ? "text-yellow-400 bg-yellow-400/10"
        : "text-orange-400 bg-orange-400/10";

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${color}`}>
      {pct}%
    </span>
  );
}

function ToolBadge({ tool }: { tool: string }) {
  const colors: Record<string, string> = {
    "Google Calendar": "text-blue-400 bg-blue-400/10",
    Gmail: "text-red-400 bg-red-400/10",
    Jira: "text-indigo-400 bg-indigo-400/10",
    Slack: "text-pink-400 bg-pink-400/10",
    GitHub: "text-purple-400 bg-purple-400/10",
  };

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs ${colors[tool] || "text-gray-400 bg-gray-400/10"}`}
    >
      {tool}
    </span>
  );
}

export default function PilotPage() {
  const { isDemo, markBackendDown } = useDemo();
  const [delegations, setDelegations] = useState<DelegationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDelegations = useCallback(async () => {
    if (isDemo) {
      setDelegations(demoDelegations);
      setLoading(false);
      return;
    }
    try {
      const data = await pilot.listDelegations();
      setDelegations(data);
    } catch (err) {
      console.error("Failed to load delegations:", err);
      markBackendDown();
      setDelegations(demoDelegations);
    } finally {
      setLoading(false);
    }
  }, [isDemo, markBackendDown]);

  useEffect(() => {
    loadDelegations();
  }, [loadDelegations]);

  const handleAction = async (id: string, action: "approve" | "reject") => {
    if (isDemo) {
      setDelegations((prev) => prev.map((d) => {
        if (d.id !== id) return d;
        if (action === "reject") return { ...d, status: "rejected", resolved_at: new Date().toISOString() };
        // Simulate execution on approve
        return {
          ...d,
          status: "executed",
          resolved_at: new Date().toISOString(),
          execution_result: {
            success: true,
            action: d.tool.toLowerCase(),
            message: `Executed: ${d.action}`,
            executed_at: new Date().toISOString(),
          },
        };
      }));
      return;
    }
    try {
      const updated = action === "approve"
        ? await pilot.approve(id)
        : await pilot.reject(id);
      setDelegations((prev) =>
        prev.map((d) => (d.id === id ? updated : d)),
      );
    } catch (err) {
      console.error(`Failed to ${action} delegation:`, err);
    }
  };

  const handleExecute = async (id: string) => {
    if (isDemo) {
      setDelegations((prev) => prev.map((d) => d.id === id ? {
        ...d,
        status: "executed",
        execution_result: {
          success: true,
          action: d.tool.toLowerCase(),
          message: `Executed: ${d.action}`,
          executed_at: new Date().toISOString(),
        },
      } : d));
      return;
    }
    try {
      const result = await pilot.execute(id);
      // Reload to get updated delegation
      await loadDelegations();
    } catch (err) {
      console.error("Failed to execute delegation:", err);
    }
  };

  const handleUndo = async (id: string) => {
    if (isDemo) {
      setDelegations((prev) => prev.map((d) => d.id === id ? { ...d, status: "pending", resolved_at: null, resolved_by_user_id: null } : d));
      return;
    }
    try {
      const updated = await pilot.undo(id);
      setDelegations((prev) =>
        prev.map((d) => (d.id === id ? updated : d)),
      );
    } catch (err) {
      console.error("Failed to undo delegation:", err);
    }
  };

  const pending = delegations.filter((d) => d.status === "pending");
  const resolved = delegations.filter((d) => d.status !== "pending");
  const approvalRate =
    resolved.length > 0
      ? Math.round(
          (resolved.filter((d) => d.status === "approved").length /
            resolved.length) *
            100,
        )
      : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-white">Pilot</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Clock className="w-4 h-4" />
            <span>{pending.length} pending</span>
          </div>
          {resolved.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <TrendingUp className="w-4 h-4" />
              <span>{approvalRate}% approved</span>
            </div>
          )}
        </div>
      </div>
      <p className="text-gray-400 mb-8">
        AI-proposed actions across your tools. Review, approve, or reject —
        Pilot learns from your decisions.
      </p>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="glass-card p-4 text-center">
          <Inbox className="w-5 h-5 text-[var(--accent)] mx-auto mb-1" />
          <div className="text-2xl font-bold text-white">{pending.length}</div>
          <div className="text-xs text-gray-400">Pending</div>
        </div>
        <div className="glass-card p-4 text-center">
          <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto mb-1" />
          <div className="text-2xl font-bold text-white">
            {resolved.filter((d) => d.status === "approved").length}
          </div>
          <div className="text-xs text-gray-400">Approved</div>
        </div>
        <div className="glass-card p-4 text-center">
          <Play className="w-5 h-5 text-blue-400 mx-auto mb-1" />
          <div className="text-2xl font-bold text-white">
            {resolved.filter((d) => d.status === "executed").length}
          </div>
          <div className="text-xs text-gray-400">Executed</div>
        </div>
        <div className="glass-card p-4 text-center">
          <XCircle className="w-5 h-5 text-red-400 mx-auto mb-1" />
          <div className="text-2xl font-bold text-white">
            {resolved.filter((d) => d.status === "rejected").length}
          </div>
          <div className="text-xs text-gray-400">Rejected</div>
        </div>
      </div>

      {/* Pending delegations */}
      {pending.length > 0 && (
        <div className="space-y-4 mb-8">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Awaiting Your Decision
          </h2>
          {pending.map((item) => (
            <div key={item.id} className="glass-card p-5">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <ToolBadge tool={item.tool} />
                    <ConfidenceBadge value={item.confidence} />
                    <span className="text-xs text-gray-500">{formatTimeAgo(item.created_at)}</span>
                  </div>
                  <p className="text-sm font-medium text-white">{item.action}</p>
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                    {item.reason}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 pt-3 border-t border-white/5">
                <button
                  onClick={() => handleAction(item.id, "approve")}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 text-green-400 text-xs hover:bg-green-500/20 transition-colors"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approve
                </button>
                <button
                  onClick={() => handleAction(item.id, "reject")}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs hover:bg-red-500/20 transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Reject
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 text-gray-400 text-xs hover:bg-white/10 transition-colors ml-auto">
                  <ChevronRight className="w-3.5 h-3.5" />
                  Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Resolved */}
      {resolved.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Resolved
          </h2>
          {resolved.map((item) => (
            <div
              key={item.id}
              className={`glass-card p-4 ${item.status === "executed" ? "opacity-80" : "opacity-60"} flex items-start gap-4`}
            >
              {item.status === "executed" ? (
                <Play className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              ) : item.status === "approved" ? (
                <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{item.action}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <ToolBadge tool={item.tool} />
                  <span className="text-xs text-gray-500">{formatTimeAgo(item.created_at)}</span>
                </div>
                {/* Execution result */}
                {item.execution_result && (
                  <div className={`mt-2 text-xs px-3 py-1.5 rounded-lg ${
                    item.execution_result.success
                      ? "bg-blue-500/10 text-blue-300"
                      : "bg-red-500/10 text-red-300"
                  }`}>
                    <div className="flex items-center gap-1.5">
                      {item.execution_result.success ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <AlertCircle className="w-3 h-3" />
                      )}
                      <span>{String(item.execution_result.message || "")}</span>
                      {typeof item.execution_result.url === "string" && item.execution_result.url && (
                        <a
                          href={String(item.execution_result.url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-auto text-blue-400 hover:text-blue-300"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {item.status === "approved" && !item.execution_result && (
                  <button
                    onClick={() => handleExecute(item.id)}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    <Play className="w-3 h-3" />
                    Execute
                  </button>
                )}
                {item.status !== "executed" && (
                  <button
                    onClick={() => handleUndo(item.id)}
                    className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
                  >
                    <Undo2 className="w-3 h-3" />
                    Undo
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {pending.length === 0 && resolved.length === 0 && (
        <div className="text-center py-16">
          <Zap className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">All caught up</h3>
          <p className="text-gray-400 text-sm">
            Pilot will surface actions as it learns from your connected tools.
          </p>
        </div>
      )}
    </div>
  );
}
