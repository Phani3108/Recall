"use client";

import { useState, useEffect } from "react";
import {
  Bell,
  Loader2,
  CheckCheck,
  Trash2,
  Github,
  Bot,
  CheckCircle,
  Zap,
  AlertTriangle,
  Info,
} from "lucide-react";
import { notifications as notifApi, type NotificationItem } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoNotifications } from "@/lib/demo-data";

/* ── helpers ── */

const iconMap: Record<string, typeof Bell> = {
  github: Github,
  bot: Bot,
  check: CheckCircle,
  zap: Zap,
  alert: AlertTriangle,
};

function NotificationRow({
  item,
  onRead,
  onDismiss,
}: {
  item: NotificationItem;
  onRead: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  const Icon = iconMap[item.icon || ""] || Info;
  const isUnread = !item.read_at;

  return (
    <div
      className={`flex items-start gap-4 p-4 border-b border-white/5 last:border-0 transition-colors ${
        isUnread ? "bg-[var(--accent)]/[0.03]" : ""
      }`}
    >
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
          isUnread ? "bg-[var(--accent)]/20 text-[var(--accent)]" : "bg-white/5 text-gray-500"
        }`}
      >
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-white">{item.title}</div>
        {item.body && <div className="text-xs text-gray-400 mt-0.5">{item.body}</div>}
        <div className="text-[10px] text-gray-600 mt-1">
          {new Date(item.created_at).toLocaleString()}
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        {isUnread && (
          <button
            onClick={() => onRead(item.id)}
            className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-[var(--accent)] transition-colors"
            title="Mark as read"
          >
            <CheckCheck className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          onClick={() => onDismiss(item.id)}
          className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-red-400 transition-colors"
          title="Dismiss"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

/* ── main ── */

type Filter = "all" | "unread";

export default function NotificationsPage() {
  const { isDemo } = useDemo();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [filter, setFilter] = useState<Filter>("all");

  const load = async () => {
    setLoading(true);
    try {
      if (isDemo) {
        setItems(demoNotifications);
      } else {
        const res = await notifApi.list();
        setItems(res.notifications);
      }
    } catch {
      setItems(demoNotifications);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [isDemo]);

  const markRead = async (id: string) => {
    if (!isDemo) await notifApi.markRead(id);
    setItems((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)),
    );
  };

  const markAllRead = async () => {
    if (!isDemo) await notifApi.markAllRead();
    setItems((prev) => prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() })));
  };

  const dismiss = async (id: string) => {
    if (!isDemo) await notifApi.dismiss(id);
    setItems((prev) => prev.filter((n) => n.id !== id));
  };

  const filtered = filter === "unread" ? items.filter((n) => !n.read_at) : items;
  const unreadCount = items.filter((n) => !n.read_at).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading notifications…
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bell className="w-6 h-6 text-[var(--accent)]" /> Notifications
            {unreadCount > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-[var(--accent)]/20 text-[var(--accent)] text-xs rounded-full">
                {unreadCount}
              </span>
            )}
          </h1>
          <p className="text-sm text-gray-400 mt-1">Activity feed and alerts.</p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-[var(--accent)] bg-white/5 rounded-lg transition-colors"
          >
            <CheckCheck className="w-3.5 h-3.5" /> Mark all read
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {(["all", "unread"] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-md text-sm capitalize transition-colors ${
              filter === f
                ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {f}{f === "unread" && unreadCount > 0 ? ` (${unreadCount})` : ""}
          </button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Bell className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <div className="text-gray-400 text-sm">
            {filter === "unread" ? "All caught up!" : "No notifications yet."}
          </div>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          {filtered.map((n) => (
            <NotificationRow key={n.id} item={n} onRead={markRead} onDismiss={dismiss} />
          ))}
        </div>
      )}
    </div>
  );
}
