import { Layers, Bot, Eye } from 'lucide-react';

export default function FlowSection() {
  return (
    <section id="flow" className="relative px-6 py-32">
      <div className="mx-auto max-w-5xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-[var(--color-warning)]/10 px-4 py-1.5 text-sm font-medium text-[var(--color-warning)]">
          Flow · Coming Soon
        </div>

        <h2 className="mt-6 text-3xl font-bold md:text-5xl">
          Work Management,{' '}
          <span className="gradient-text">Rebuilt for AI</span>
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--color-text-secondary)]">
          Not another Jira with AI sprinkled on top. Tasks are living entities — AI populates
          context, detects blockers, updates progress, and completes work autonomously.
        </p>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {[
            {
              icon: Layers,
              title: 'Context Complete',
              description:
                'Every task carries its full history: conversations, decisions, documents. No more "check Slack for the decision."',
            },
            {
              icon: Bot,
              title: 'AI as Teammate',
              description:
                'Assign work directly to AI. It executes via Ask skills and reports back with results.',
            },
            {
              icon: Eye,
              title: 'Progress Without Meetings',
              description:
                'AI-generated status updates. Blockers surfaced automatically. Silent work made visible.',
            },
          ].map((card) => (
            <div key={card.title} className="glass-card rounded-2xl p-8 text-left">
              <card.icon className="h-8 w-8 text-[var(--color-warning)]" />
              <h3 className="mt-4 text-lg font-semibold">{card.title}</h3>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{card.description}</p>
            </div>
          ))}
        </div>

        <a
          href="#waitlist"
          className="mt-12 inline-flex items-center gap-2 rounded-full border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 px-6 py-3 text-sm font-medium text-[var(--color-warning)] transition-all hover:bg-[var(--color-warning)]/20"
        >
          Be first to try Flow → Join Waitlist
        </a>
      </div>
    </section>
  );
}
