import { Inbox, ShieldCheck, TrendingUp, Undo2 } from 'lucide-react';

const features = [
  {
    icon: Inbox,
    title: 'Surfaces what needs your attention — with recommendations',
    description: 'Pilot scans your tools, identifies actionable items, and proposes what to do.',
  },
  {
    icon: ShieldCheck,
    title: 'Executes approved actions across tools',
    description: 'Email, calendar, tickets, docs — one click to approve, Pilot handles the rest.',
  },
  {
    icon: TrendingUp,
    title: 'Learns your preferences — gets better every week',
    description: 'Approval rate climbs as Pilot calibrates to your judgment and style.',
  },
  {
    icon: Undo2,
    title: 'Full accountability — every action is reversible',
    description: 'Complete audit trail with reasoning. Undo any action within the reversal window.',
  },
];

export default function PilotSection() {
  return (
    <section id="pilot" className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="grid items-center gap-16 md:grid-cols-2">
          {/* Left — Description */}
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-[var(--color-success)]/10 px-4 py-1.5 text-sm font-medium text-[var(--color-success)]">
              Pilot
            </div>
            <h2 className="mt-4 text-3xl font-bold md:text-4xl">
              Your AI That Takes{' '}
              <span className="gradient-text">Ownership</span>
            </h2>
            <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
              Shift from doing to deciding. Pilot handles the execution — you stay in control.
              Responsible and Accountable goes to AI. You&apos;re Consulted and Informed.
            </p>

            <div className="mt-8 space-y-6">
              {features.map((f) => (
                <div key={f.title} className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-bg-card)]">
                    <f.icon className="h-5 w-5 text-[var(--color-success)]" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{f.title}</h4>
                    <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{f.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — Delegation inbox mockup */}
          <div className="glass-card rounded-2xl p-6">
            <div className="mb-4 flex items-center justify-between">
              <h4 className="text-sm font-semibold text-[var(--color-text-muted)]">DELEGATION INBOX</h4>
              <span className="rounded-full bg-[var(--color-success)]/10 px-3 py-1 text-xs text-[var(--color-success)]">
                3 pending
              </span>
            </div>

            <div className="space-y-3">
              {[
                {
                  action: 'Decline meeting: "Q2 Budget Review Sync"',
                  reason: 'Conflicts with deep work block. No action items for you in agenda.',
                  confidence: 92,
                },
                {
                  action: 'Reply to Sarah\'s email re: billing exception',
                  reason: 'Draft based on your previous responses and the updated SOP.',
                  confidence: 78,
                },
                {
                  action: 'Update JIRA-1234 status to "In Review"',
                  reason: 'PR #89 was merged 2 hours ago. Linked ticket still says "In Progress".',
                  confidence: 95,
                },
              ].map((item) => (
                <div key={item.action} className="rounded-xl bg-[var(--color-bg-secondary)] p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.action}</p>
                      <p className="mt-1 text-xs text-[var(--color-text-muted)]">{item.reason}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <div
                        className={`text-sm font-bold ${
                          item.confidence >= 90 ? 'text-[var(--color-success)]' : 'text-[var(--color-warning)]'
                        }`}
                      >
                        {item.confidence}%
                      </div>
                      <div className="text-[10px] text-[var(--color-text-muted)]">confidence</div>
                    </div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button className="rounded-md bg-[var(--color-success)]/10 px-3 py-1  text-xs font-medium text-[var(--color-success)]">
                      Approve
                    </button>
                    <button className="rounded-md bg-[var(--color-bg-card)] px-3 py-1 text-xs text-[var(--color-text-muted)]">
                      Modify
                    </button>
                    <button className="rounded-md bg-[var(--color-danger)]/10 px-3 py-1 text-xs text-[var(--color-danger)]">
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
