import { AlertTriangle, Brain, Puzzle, Lock } from 'lucide-react';

const painPoints = [
  {
    icon: AlertTriangle,
    title: 'Context is Fragmented',
    description:
      'Knowledge lives across Slack, Jira, Notion, Gmail, Drive, and people\'s heads. Your AI only sees a sliver.',
  },
  {
    icon: Brain,
    title: 'Process Knowledge is Lost',
    description:
      'How work actually gets done — the judgment calls, the "ask Sarah" moments — none of it is captured for AI.',
  },
  {
    icon: Puzzle,
    title: 'Dozens of Disconnected Copilots',
    description:
      'Every SaaS tool has its own AI. None of them talk to each other. No cross-functional reasoning.',
  },
  {
    icon: Lock,
    title: 'AI is Only for Builders',
    description:
      'Engineers can wire up agents. Everyone else — ops, finance, HR, legal — can\'t use AI to get work done.',
  },
];

export default function ProblemSection() {
  return (
    <section className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            Your AI is <span className="text-[var(--color-danger)]">blind</span>. Here&apos;s why.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--color-text-secondary)]">
            Enterprise AI fails not because models are weak — but because they can&apos;t see your organization.
          </p>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-2">
          {painPoints.map((point) => (
            <div
              key={point.title}
              className="glass-card group rounded-2xl p-8 transition-all hover:border-[var(--color-danger)]/30 hover:shadow-lg hover:shadow-[var(--color-danger)]/5"
            >
              <point.icon className="h-8 w-8 text-[var(--color-danger)]" />
              <h3 className="mt-4 text-xl font-semibold">{point.title}</h3>
              <p className="mt-2 text-[var(--color-text-secondary)]">{point.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
