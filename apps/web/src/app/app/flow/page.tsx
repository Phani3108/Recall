"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Layers,
  Bot,
  CheckCircle2,
  Circle,
  Clock,
  AlertTriangle,
  ArrowUpRight,
  Plus,
  Filter,
  Loader2,
  X,
} from "lucide-react";
import { flow, type FlowTask } from "@/lib/api";

type TaskStatus = "todo" | "in_progress" | "in_review" | "done";
type TaskPriority = "critical" | "high" | "medium" | "low";

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; icon: typeof Circle; color: string }
> = {
  todo: { label: "To Do", icon: Circle, color: "text-gray-400" },
  in_progress: { label: "In Progress", icon: Clock, color: "text-blue-400" },
  in_review: { label: "In Review", icon: ArrowUpRight, color: "text-purple-400" },
  done: { label: "Done", icon: CheckCircle2, color: "text-green-400" },
};

const PRIORITY_CONFIG: Record<TaskPriority, { color: string }> = {
  critical: { color: "text-red-400 bg-red-400/10" },
  high: { color: "text-orange-400 bg-orange-400/10" },
  medium: { color: "text-yellow-400 bg-yellow-400/10" },
  low: { color: "text-gray-400 bg-gray-400/10" },
};

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

function TaskCard({ task, onStatusChange }: { task: FlowTask; onStatusChange: (id: string, status: string) => void }) {
  const status = STATUS_CONFIG[task.status as TaskStatus] || STATUS_CONFIG.todo;
  const StatusIcon = status.icon;
  const isAI = task.source === "ai";
  const timeAgo = formatTimeAgo(task.updated_at);

  return (
    <div className="glass-card p-4 hover:bg-white/[0.04] transition-colors">
      <div className="flex items-start gap-3">
        <StatusIcon className={`w-4 h-4 mt-0.5 shrink-0 ${status.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500 font-mono">{task.source_id || task.id.slice(0, 8)}</span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${PRIORITY_CONFIG[task.priority as TaskPriority]?.color || "text-gray-400 bg-gray-400/10"}`}
            >
              {task.priority}
            </span>
            {task.blockers.length > 0 && (
              <span className="flex items-center gap-0.5 text-[10px] text-red-400">
                <AlertTriangle className="w-3 h-3" />
                Blocked
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-white">{task.title}</p>

          {/* AI Summary */}
          {task.ai_summary && (
            <div className="mt-2 flex items-start gap-2 bg-white/[0.03] rounded-lg p-2">
              <Bot className="w-3.5 h-3.5 text-[var(--accent)] mt-0.5 shrink-0" />
              <p className="text-xs text-gray-400 leading-relaxed">
                {task.ai_summary}
              </p>
            </div>
          )}

          <div className="flex items-center gap-3 mt-2">
            <span className="flex items-center gap-1 text-xs text-gray-500">
              {isAI ? (
                <>
                  <Bot className="w-3 h-3 text-[var(--accent)]" />
                  <span className="text-[var(--accent)]">Ask AI</span>
                </>
              ) : (
                task.assignee_id ? "Assigned" : "Unassigned"
              )}
            </span>
            <span className="text-xs text-gray-600">·</span>
            <span className="text-xs text-gray-500">{task.source}</span>
            <span className="text-xs text-gray-600">·</span>
            <span className="text-xs text-gray-500">{timeAgo}</span>

            {/* Quick status change */}
            {task.status !== "done" && (
              <button
                onClick={() => {
                  const next: Record<string, string> = {
                    todo: "in_progress",
                    in_progress: "in_review",
                    in_review: "done",
                  };
                  onStatusChange(task.id, next[task.status] || "done");
                }}
                className="ml-auto text-xs text-gray-500 hover:text-[var(--accent)] transition-colors"
              >
                → {STATUS_CONFIG[(
                  { todo: "in_progress", in_progress: "in_review", in_review: "done" } as Record<string, TaskStatus>
                )[task.status] || "done"]?.label}
              </button>
            )}
          </div>

          {task.blockers.length > 0 && (
            <div className="mt-2 px-2 py-1.5 rounded bg-red-500/5 border border-red-500/10">
              <p className="text-xs text-red-400">
                Blocker: {task.blockers[0]}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function FlowPage() {
  const [tasks, setTasks] = useState<FlowTask[]>([]);
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState<TaskPriority>("medium");
  const [creating, setCreating] = useState(false);

  const loadTasks = useCallback(async () => {
    try {
      const data = await flow.listTasks();
      setTasks(data);
    } catch (err) {
      console.error("Failed to load tasks:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleStatusChange = async (taskId: string, newStatus: string) => {
    try {
      const updated = await flow.updateTask(taskId, { status: newStatus } as Partial<FlowTask>);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
    } catch (err) {
      console.error("Failed to update task:", err);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const task = await flow.createTask({
        title: newTitle.trim(),
        priority: newPriority,
        source: "manual",
      });
      setTasks((prev) => [task, ...prev]);
      setNewTitle("");
      setShowNewTask(false);
    } catch (err) {
      console.error("Failed to create task:", err);
    } finally {
      setCreating(false);
    }
  };

  const filteredTasks =
    filter === "all"
      ? tasks
      : tasks.filter((t) => t.status === filter);

  const statusCounts = {
    todo: tasks.filter((t) => t.status === "todo").length,
    in_progress: tasks.filter((t) => t.status === "in_progress").length,
    in_review: tasks.filter((t) => t.status === "in_review").length,
    done: tasks.filter((t) => t.status === "done").length,
  };

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
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            Flow
          </h1>
        </div>
        <button
          onClick={() => setShowNewTask(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] text-sm hover:bg-[var(--accent)]/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New task
        </button>
      </div>
      <p className="text-gray-400 mb-6">
        AI-native work management. Tasks carry full context, AI surfaces blockers
        and updates progress automatically.
      </p>

      {/* New task form */}
      {showNewTask && (
        <form onSubmit={handleCreateTask} className="glass-card p-4 mb-6">
          <div className="flex items-center gap-3">
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Task title..."
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
              autoFocus
            />
            <select
              value={newPriority}
              onChange={(e) => setNewPriority(e.target.value as TaskPriority)}
              className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <button
              type="submit"
              disabled={creating || !newTitle.trim()}
              className="px-3 py-2 rounded-lg bg-[var(--accent)] text-white text-sm disabled:opacity-50"
            >
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : "Add"}
            </button>
            <button
              type="button"
              onClick={() => { setShowNewTask(false); setNewTitle(""); }}
              className="text-gray-500 hover:text-gray-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </form>
      )}

      {/* Status filter pills */}
      <div className="flex items-center gap-2 mb-6">
        <Filter className="w-4 h-4 text-gray-500" />
        {(["all", "todo", "in_progress", "in_review", "done"] as const).map(
          (s) => {
            const isActive = filter === s;
            const count =
              s === "all" ? tasks.length : statusCounts[s];
            const label =
              s === "all" ? "All" : STATUS_CONFIG[s].label;

            return (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`px-3 py-1 rounded-full text-xs transition-colors ${
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                }`}
              >
                {label}{" "}
                <span className="opacity-60">{count}</span>
              </button>
            );
          },
        )}
      </div>

      {/* Kanban-lite: status groups */}
      <div className="space-y-6">
        {(["in_progress", "in_review", "todo", "done"] as TaskStatus[]).map(
          (status) => {
            const tasks = filteredTasks.filter((t) => t.status === status);
            if (tasks.length === 0) return null;
            const cfg = STATUS_CONFIG[status];
            const Icon = cfg.icon;

            return (
              <div key={status}>
                <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  <Icon className={`w-4 h-4 ${cfg.color}`} />
                  {cfg.label}
                  <span className="text-xs font-normal text-gray-600">
                    {tasks.length}
                  </span>
                </h2>
                <div className="space-y-3">
                  {tasks.map((task) => (
                    <TaskCard key={task.id} task={task} onStatusChange={handleStatusChange} />
                  ))}
                </div>
              </div>
            );
          },
        )}
      </div>

      {filteredTasks.length === 0 && (
        <div className="text-center py-16">
          <Layers className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">
            No tasks match this filter
          </h3>
          <p className="text-gray-400 text-sm">
            Try selecting a different status filter.
          </p>
        </div>
      )}
    </div>
  );
}
