"use client";

import { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  DollarSign,
  Zap,
  Users,
  Activity,
  Loader2,
  Plug,
  Bot,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import {
  analytics,
  type TokenTrend,
  type ProductivityStats,
  type CostForecast,
  type TopUser,
  type IntegrationHealthItem,
  type AgentIntelligence,
} from "@/lib/api";
import { useDemo } from "@/lib/demo";
import {
  demoTokenTrends,
  demoProductivity,
  demoCostForecast,
  demoTopUsers,
  demoIntegrationHealth,
  demoAgentIntelligence,
} from "@/lib/demo-data";

/* ── helpers ── */

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = "text-[var(--accent)]",
}: {
  icon: typeof Zap;
  label: string;
  value: string | number;
  sub?: string;
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
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function MiniBar({ value, max }: { value: number; max: number }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
      <div className="h-full bg-[var(--accent)] rounded-full" style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ── page sections ── */

function TokenTrendsChart({ data }: { data: TokenTrend[] }) {
  const maxTokens = Math.max(...data.map((d) => d.tokens), 1);
  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <Activity className="w-4 h-4 text-[var(--accent)]" /> Token Consumption (30 days)
      </h3>
      <div className="flex items-end gap-[2px] h-32">
        {data.map((d) => {
          const h = (d.tokens / maxTokens) * 100;
          return (
            <div
              key={d.day}
              title={`${d.day}: ${d.tokens.toLocaleString()} tokens · $${d.cost.toFixed(4)}`}
              className="flex-1 bg-[var(--accent)]/60 hover:bg-[var(--accent)] transition-colors rounded-t cursor-default"
              style={{ height: `${h}%` }}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] text-gray-600 mt-1">
        <span>{data[0]?.day}</span>
        <span>{data[data.length - 1]?.day}</span>
      </div>
    </div>
  );
}

function ProductivitySection({ data }: { data: ProductivityStats }) {
  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <Zap className="w-4 h-4 text-[var(--accent)]" /> Productivity ({data.period_days}-day)
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-gray-400 mb-1">Tasks completed</div>
          <div className="text-lg font-bold text-white">
            {data.tasks_completed}{" "}
            <span className="text-xs font-normal text-gray-500">/ {data.tasks_created}</span>
          </div>
          <MiniBar value={data.tasks_completed} max={data.tasks_created} />
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Completion rate</div>
          <div className="text-lg font-bold text-green-400">
            {(data.task_completion_rate * 100).toFixed(0)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Delegations executed</div>
          <div className="text-lg font-bold text-white">
            {data.delegations_executed}{" "}
            <span className="text-xs font-normal text-gray-500">/ {data.delegations_total}</span>
          </div>
          <MiniBar value={data.delegations_executed} max={data.delegations_total} />
        </div>
        <div>
          <div className="text-xs text-gray-400 mb-1">Conversations / Messages</div>
          <div className="text-lg font-bold text-white">
            {data.conversations}{" "}
            <span className="text-xs font-normal text-gray-500">/ {data.messages} msgs</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CostForecastCard({ data }: { data: CostForecast }) {
  const TrendIcon =
    data.trend === "increasing" ? TrendingUp : data.trend === "decreasing" ? TrendingDown : Minus;
  const trendColor =
    data.trend === "increasing"
      ? "text-red-400"
      : data.trend === "decreasing"
        ? "text-green-400"
        : "text-gray-400";

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <DollarSign className="w-4 h-4 text-[var(--accent)]" /> Cost Forecast
      </h3>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-white">${data.projected_monthly.toFixed(2)}</span>
        <span className="text-xs text-gray-500">/month</span>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <TrendIcon className={`w-4 h-4 ${trendColor}`} />
        <span className={`text-xs ${trendColor} capitalize`}>{data.trend}</span>
        <span className="text-xs text-gray-600">· ${data.daily_avg.toFixed(2)}/day avg</span>
      </div>
    </div>
  );
}

function TopUsersTable({ users }: { users: TopUser[] }) {
  const maxTokens = Math.max(...users.map((u) => u.tokens), 1);
  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <Users className="w-4 h-4 text-[var(--accent)]" /> Top AI Users
      </h3>
      <div className="space-y-3">
        {users.map((u, i) => (
          <div key={u.user_id} className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-5 text-right">{i + 1}.</span>
            <div className="w-7 h-7 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-xs text-[var(--accent)] font-bold">
              {u.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white truncate">{u.name}</div>
              <MiniBar value={u.tokens} max={maxTokens} />
            </div>
            <div className="text-right">
              <div className="text-xs text-white">{u.tokens.toLocaleString()}</div>
              <div className="text-[10px] text-gray-500">${u.cost.toFixed(2)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function IntegrationHealthSection({ items }: { items: IntegrationHealthItem[] }) {
  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <Plug className="w-4 h-4 text-[var(--accent)]" /> Integration Health
      </h3>
      <div className="space-y-3">
        {items.map((it) => {
          const isOk = it.status === "connected";
          return (
            <div key={it.id} className="flex items-center gap-3">
              {isOk ? (
                <CheckCircle className="w-4 h-4 text-green-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-sm text-white capitalize flex-1">{it.provider}</span>
              <span className="text-xs text-gray-400">{it.entity_count} entities</span>
              <span className="text-[10px] text-gray-600">
                {it.last_synced_at ? new Date(it.last_synced_at).toLocaleTimeString() : "never"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgentIntelligenceSection({ data }: { data: AgentIntelligence }) {
  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <Bot className="w-4 h-4 text-[var(--accent)]" /> Agent Intelligence ({data.period_days}-day)
      </h3>
      <div className="flex items-center gap-6 mb-4">
        <div>
          <div className="text-xs text-gray-400">Proposals</div>
          <div className="text-xl font-bold text-white">{data.total_proposals}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Approved</div>
          <div className="text-xl font-bold text-green-400">{data.total_approved}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Approval rate</div>
          <div className="text-xl font-bold text-white">{(data.approval_rate * 100).toFixed(0)}%</div>
        </div>
      </div>
      <div className="space-y-2">
        {Object.entries(data.patterns).map(([key, p]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="text-xs text-gray-300 flex-1 capitalize">{key.replace(/_/g, " ")}</span>
            <span className="text-xs text-green-400">{p.approved}✓</span>
            <span className="text-xs text-red-400">{p.rejected}✗</span>
            {p.pending > 0 && (
              <span className="text-xs text-yellow-400 flex items-center gap-0.5">
                <Clock className="w-3 h-3" />
                {p.pending}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── main ── */

type Tab = "overview" | "agents";

export default function AnalyticsPage() {
  const { isDemo } = useDemo();
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  const [trends, setTrends] = useState<TokenTrend[]>([]);
  const [productivity, setProductivity] = useState<ProductivityStats | null>(null);
  const [forecast, setForecast] = useState<CostForecast | null>(null);
  const [topUsers, setTopUsers] = useState<TopUser[]>([]);
  const [health, setHealth] = useState<IntegrationHealthItem[]>([]);
  const [agentData, setAgentData] = useState<AgentIntelligence | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        if (isDemo) {
          setTrends(demoTokenTrends);
          setProductivity(demoProductivity);
          setForecast(demoCostForecast);
          setTopUsers(demoTopUsers);
          setHealth(demoIntegrationHealth);
          setAgentData(demoAgentIntelligence);
        } else {
          const [ov, tr, tu, ih, ai] = await Promise.all([
            analytics.overview(),
            analytics.tokenTrends(),
            analytics.topUsers(),
            analytics.integrationHealth(),
            analytics.agentIntelligence(),
          ]);
          if (cancelled) return;
          setTrends(tr);
          setProductivity(ov.productivity);
          setForecast(ov.cost_forecast);
          setTopUsers(tu);
          setHealth(ih);
          setAgentData(ai);
        }
      } catch {
        // fall back to demo
        setTrends(demoTokenTrends);
        setProductivity(demoProductivity);
        setForecast(demoCostForecast);
        setTopUsers(demoTopUsers);
        setHealth(demoIntegrationHealth);
        setAgentData(demoAgentIntelligence);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [isDemo]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading analytics…
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "agents", label: "Agent Intelligence" },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-[var(--accent)]" /> Analytics
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI usage, productivity, and cost insights.</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
              tab === t.key
                ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          {/* Top cards */}
          <div className="grid grid-cols-4 gap-4">
            <StatCard
              icon={Zap}
              label="Total Tokens (30d)"
              value={trends.reduce((s, t) => s + t.tokens, 0).toLocaleString()}
            />
            <StatCard
              icon={DollarSign}
              label="Total Cost (30d)"
              value={`$${trends.reduce((s, t) => s + t.cost, 0).toFixed(2)}`}
              color="text-green-400"
            />
            <StatCard
              icon={Activity}
              label="Requests (30d)"
              value={trends.reduce((s, t) => s + t.requests, 0).toLocaleString()}
              color="text-blue-400"
            />
            <StatCard
              icon={Users}
              label="Active Users"
              value={topUsers.length}
              color="text-purple-400"
            />
          </div>

          {/* Charts row */}
          <TokenTrendsChart data={trends} />

          {/* Lower row */}
          <div className="grid grid-cols-2 gap-6">
            {productivity && <ProductivitySection data={productivity} />}
            {forecast && <CostForecastCard data={forecast} />}
          </div>

          <div className="grid grid-cols-2 gap-6">
            <TopUsersTable users={topUsers} />
            <IntegrationHealthSection items={health} />
          </div>
        </>
      )}

      {tab === "agents" && agentData && <AgentIntelligenceSection data={agentData} />}
    </div>
  );
}
