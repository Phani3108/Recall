import { Link2, Scan, MessageSquare, CheckCircle2 } from 'lucide-react';

const steps = [
  {
    num: 1,
    icon: Link2,
    title: 'Connect Your Tools',
    description:
      'OAuth into Slack, Google, GitHub, Jira, Notion. 2 clicks each. No engineering required.',
  },
  {
    num: 2,
    icon: Scan,
    title: 'AI Learns Your Org',
    description:
      'Recall indexes your knowledge: docs, messages, tickets, people, relationships. Permission-aware from day one.',
  },
  {
    num: 3,
    icon: MessageSquare,
    title: 'Start Asking, Start Building',
    description:
      'Chat with Ask. Build workflows. Share skills. AI gets smarter with every interaction.',
  },
  {
    num: 4,
    icon: CheckCircle2,
    title: 'Delegate with Confidence',
    description:
      'Let Pilot handle the routine. You approve, it executes. Full audit trail, always.',
  },
];

export default function HowItWorksSection() {
  return (
    <section id="how-it-works" className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            Up and running in <span className="gradient-text">minutes</span>, not months
          </h2>
        </div>

        <div className="relative mt-20">
          {/* Connection line */}
          <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-gradient-to-b from-[var(--color-accent)] via-[var(--color-accent)]/50 to-transparent md:block" />

          <div className="space-y-16">
            {steps.map((step, i) => (
              <div
                key={step.num}
                className={`relative flex flex-col items-center gap-8 md:flex-row ${
                  i % 2 === 1 ? 'md:flex-row-reverse' : ''
                }`}
              >
                {/* Content */}
                <div className="flex-1 md:text-right">
                  {i % 2 === 0 ? (
                    <div className="glass-card rounded-2xl p-6">
                      <h3 className="text-lg font-semibold">{step.title}</h3>
                      <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                        {step.description}
                      </p>
                    </div>
                  ) : (
                    <div />
                  )}
                </div>

                {/* Center node */}
                <div className="relative z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] text-lg font-bold text-white shadow-lg shadow-[var(--color-accent)]/20">
                  {step.num}
                </div>

                {/* Content (other side) */}
                <div className="flex-1">
                  {i % 2 === 1 ? (
                    <div className="glass-card rounded-2xl p-6">
                      <h3 className="text-lg font-semibold">{step.title}</h3>
                      <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                        {step.description}
                      </p>
                    </div>
                  ) : (
                    <div />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="mt-16 text-center text-lg text-[var(--color-text-secondary)]">
          Average time to first value:{' '}
          <span className="font-bold text-[var(--color-success)]">under 10 minutes</span>
        </p>
      </div>
    </section>
  );
}
