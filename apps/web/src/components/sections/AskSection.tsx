import { MessageSquare, Workflow, Sparkles, Send } from 'lucide-react';

const features = [
  {
    icon: MessageSquare,
    title: 'Ask anything — get answers with sources',
    description: 'Every response cites its sources with links back to the original tool.',
  },
  {
    icon: Workflow,
    title: 'Build AI workflows visually — no code',
    description: 'Drag-and-drop canvas for non-technical users. Triggers, conditions, AI steps, actions.',
  },
  {
    icon: Sparkles,
    title: 'Share skills across teams',
    description: 'Encode what works as reusable AI skills. Propagate from one team to another.',
  },
  {
    icon: Send,
    title: 'Deploy anywhere — Slack, browser, email, API',
    description: 'AI where you already work. Ambient intelligence across every surface.',
  },
];

export default function AskSection() {
  return (
    <section id="ask" className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="grid items-center gap-16 md:grid-cols-2">
          {/* Left — Product mockup */}
          <div className="glass-card glow-accent rounded-2xl p-6">
            {/* Chat mockup */}
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent)]/20 text-sm text-[var(--color-accent-light)]">
                  U
                </div>
                <div className="rounded-xl rounded-tl-none bg-[var(--color-bg-card-hover)] px-4 py-3 text-sm">
                  Who on the team has context on the billing exception flow?
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] text-sm font-bold text-white">
                  R
                </div>
                <div className="space-y-2 rounded-xl rounded-tl-none bg-[var(--color-bg-secondary)] px-4 py-3 text-sm">
                  <p>
                    Based on recent activity, <strong>Sarah Chen</strong> has the most context:
                  </p>
                  <ul className="ml-4 space-y-1 text-[var(--color-text-secondary)]">
                    <li>• Updated the billing SOP in Notion (3 days ago)</li>
                    <li>• Resolved 4 billing exception tickets in Jira this sprint</li>
                    <li>• Active in #billing-edge-cases Slack channel</li>
                  </ul>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded bg-[var(--color-accent)]/10 px-2 py-0.5 text-xs text-[var(--color-accent-light)]">
                      Notion · Billing SOP
                    </span>
                    <span className="rounded bg-[var(--color-accent)]/10 px-2 py-0.5 text-xs text-[var(--color-accent-light)]">
                      Jira · 4 tickets
                    </span>
                    <span className="rounded bg-[var(--color-accent)]/10 px-2 py-0.5 text-xs text-[var(--color-accent-light)]">
                      Slack · #billing
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right — Description */}
          <div id="products">
            <div className="inline-flex items-center gap-2 rounded-full bg-[var(--color-accent)]/10 px-4 py-1.5 text-sm font-medium text-[var(--color-accent-light)]">
              Ask
            </div>
            <h2 className="mt-4 text-3xl font-bold md:text-4xl">
              Your Enterprise AI that Actually{' '}
              <span className="gradient-text">Knows Your Business</span>
            </h2>
            <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
              Not a chatbot with a knowledge base. An AI teammate with full context across every
              tool your organization uses.
            </p>

            <div className="mt-8 space-y-6">
              {features.map((f) => (
                <div key={f.title} className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-bg-card)]">
                    <f.icon className="h-5 w-5 text-[var(--color-accent-light)]" />
                  </div>
                  <div>
                    <h4 className="font-semibold">{f.title}</h4>
                    <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{f.description}</p>
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
