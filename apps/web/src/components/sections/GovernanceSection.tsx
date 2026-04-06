import { Shield, Gauge, FileSearch, Lock, Key, Server } from 'lucide-react';

const features = [
  {
    icon: Shield,
    title: 'Permission-Aware AI',
    description:
      'AI only accesses data the user is authorized to see. Permissions inherited from your source tools — Slack channels, Drive sharing, GitHub repos.',
    mockup: (
      <div className="mt-4 space-y-2 rounded-lg bg-[var(--color-bg-secondary)] p-4 text-xs">
        <div className="flex items-center justify-between">
          <span>Billing SOP</span>
          <span className="rounded bg-[var(--color-success)]/10 px-2 py-0.5 text-[var(--color-success)]">Access ✓</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Executive Comp Sheet</span>
          <span className="rounded bg-[var(--color-danger)]/10 px-2 py-0.5 text-[var(--color-danger)]">Restricted</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Engineering Wiki</span>
          <span className="rounded bg-[var(--color-success)]/10 px-2 py-0.5 text-[var(--color-success)]">Access ✓</span>
        </div>
      </div>
    ),
  },
  {
    icon: Gauge,
    title: 'Token Budgets & Cost Control',
    description:
      'Set spending limits per team, per user, per workflow. Real-time cost attribution dashboard — no surprise bills.',
    mockup: (
      <div className="mt-4 space-y-3 rounded-lg bg-[var(--color-bg-secondary)] p-4 text-xs">
        <div>
          <div className="mb-1 flex justify-between">
            <span>Engineering</span>
            <span>72%</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--color-bg-card)]">
            <div className="h-2 w-[72%] rounded-full bg-[var(--color-accent)]" />
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between">
            <span>Operations</span>
            <span>34%</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--color-bg-card)]">
            <div className="h-2 w-[34%] rounded-full bg-[var(--color-success)]" />
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between">
            <span>Sales</span>
            <span>91%</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--color-bg-card)]">
            <div className="h-2 w-[91%] rounded-full bg-[var(--color-warning)]" />
          </div>
        </div>
      </div>
    ),
  },
  {
    icon: FileSearch,
    title: 'Complete Audit Trail',
    description:
      'Every AI interaction logged: prompt, response, tools used, data accessed, tokens consumed. Export to your SIEM.',
    mockup: (
      <div className="mt-4 space-y-2 rounded-lg bg-[var(--color-bg-secondary)] p-4 font-mono text-[10px] text-[var(--color-text-muted)]">
        <div>[14:23:01] user:sarah → query: "billing exception flow"</div>
        <div>[14:23:01] context: 3 entities retrieved (notion, jira, slack)</div>
        <div>[14:23:02] model: claude-3.5 → tokens: 847 → cost: $0.003</div>
        <div>[14:23:02] response delivered → sources: 3 cited</div>
      </div>
    ),
  },
];

const badges = [
  { icon: Lock, label: 'SSO / SAML' },
  { icon: Key, label: 'SCIM' },
  { icon: Shield, label: 'RBAC' },
  { icon: Lock, label: 'Encryption at Rest' },
  { icon: Server, label: 'Self-Hosted Option' },
];

export default function GovernanceSection() {
  return (
    <section id="governance" className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            Enterprise governance, <span className="gradient-text">built in</span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--color-text-secondary)]">
            Not bolted on. Every AI interaction is governed, budgeted, and auditable from day one.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="glass-card rounded-2xl p-6">
              <f.icon className="h-7 w-7 text-[var(--color-accent-light)]" />
              <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{f.description}</p>
              {f.mockup}
            </div>
          ))}
        </div>

        {/* Compliance badges */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-4">
          {badges.map((b) => (
            <div
              key={b.label}
              className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-card)] px-4 py-2 text-sm text-[var(--color-text-secondary)]"
            >
              <b.icon className="h-4 w-4" />
              {b.label}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
