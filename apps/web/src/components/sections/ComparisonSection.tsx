import { X, Check } from 'lucide-react';

const boltOn = [
  'Each tool adds AI as a feature layer on top of legacy data models',
  'AI can search one tool at a time — no cross-functional reasoning',
  'No unified governance, no audit trail, no token budgets',
  'Requires engineering effort to connect tools',
];

const aiNative = [
  'Built from scratch for AI — context is the data model',
  'Unified graph across every tool — AI sees the full picture',
  'Governance by design: RBAC, audit trails, token budgets built in',
  'Connect in 2 clicks — AI starts learning in minutes',
];

export default function ComparisonSection() {
  return (
    <section className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            Why bolt-on AI will <span className="text-[var(--color-danger)]">never</span> work
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--color-text-secondary)]">
            Adding AI to legacy tools is like adding the Internet to Lotus Notes. It produces
            widgets, not Gmail.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-2">
          {/* Bolt-on AI */}
          <div className="glass-card rounded-2xl border-[var(--color-danger)]/20 p-8">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-[var(--color-danger)]/10 px-4 py-1.5 text-sm font-medium text-[var(--color-danger)]">
              Bolt-On AI
            </div>
            <h3 className="text-xl font-semibold text-[var(--color-text-secondary)]">
              What exists today
            </h3>
            <ul className="mt-6 space-y-4">
              {boltOn.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <X className="mt-0.5 h-5 w-5 shrink-0 text-[var(--color-danger)]" />
                  <span className="text-[var(--color-text-secondary)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* AI Native */}
          <div className="glass-card glow-accent rounded-2xl border-[var(--color-accent)]/30 p-8">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-[var(--color-accent)]/10 px-4 py-1.5 text-sm font-medium text-[var(--color-accent-light)]">
              AI-Native
            </div>
            <h3 className="text-xl font-semibold">Recall&apos;s approach</h3>
            <ul className="mt-6 space-y-4">
              {aiNative.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <Check className="mt-0.5 h-5 w-5 shrink-0 text-[var(--color-success)]" />
                  <span className="text-[var(--color-text-primary)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <p className="mx-auto mt-12 max-w-2xl text-center text-[var(--color-text-muted)]">
          AI-native workflows require AI-native design, not retrofitted ones.
        </p>
      </div>
    </section>
  );
}
