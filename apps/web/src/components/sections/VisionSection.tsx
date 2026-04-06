'use client';

import { useState } from 'react';
import { Link2, Brain, Zap, User, Code, BarChart3 } from 'lucide-react';

const flow = [
  {
    icon: Link2,
    label: 'Connect',
    title: 'Your tools feed the unified context graph',
    description:
      'Slack, GitHub, Google, Jira, Notion — two clicks each. Context starts flowing immediately.',
  },
  {
    icon: Brain,
    label: 'Understand',
    title: 'AI builds a living knowledge graph',
    description:
      'People, documents, tasks, decisions, relationships — all interconnected. Permission-aware from day one.',
  },
  {
    icon: Zap,
    label: 'Act',
    title: 'AI executes work across every connected tool',
    description:
      'Create tickets, send messages, draft documents, update statuses — with full accountability.',
  },
];

const personas = [
  {
    id: 'ops',
    icon: BarChart3,
    label: 'Operations Leader',
    description:
      'Automate cross-team workflows. Get real-time visibility without status meetings. Let AI handle the coordination.',
  },
  {
    id: 'eng',
    icon: Code,
    label: 'Engineering Lead',
    description:
      'AI that understands your codebase, tickets, Slack threads, and architecture decisions — all in context.',
  },
  {
    id: 'exec',
    icon: User,
    label: 'Executive',
    description:
      'Delegate meeting prep, follow-ups, and reporting to AI. Stay in the loop, not in the weeds.',
  },
];

export default function VisionSection() {
  const [activePersona, setActivePersona] = useState('ops');

  return (
    <section className="relative px-6 py-32">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-[var(--color-accent)] opacity-5 blur-[150px]" />

      <div className="relative mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            One platform. Complete context.{' '}
            <span className="gradient-text">AI that works.</span>
          </h2>
        </div>

        {/* Connect → Understand → Act flow */}
        <div className="mt-20 grid gap-8 md:grid-cols-3">
          {flow.map((step, i) => (
            <div key={step.label} className="relative text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)]">
                <step.icon className="h-8 w-8 text-white" />
              </div>
              <div className="mt-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-accent-light)]">
                {step.label}
              </div>
              <h3 className="mt-2 text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{step.description}</p>

              {/* Connector arrow */}
              {i < flow.length - 1 && (
                <div className="absolute right-0 top-8 hidden translate-x-1/2 text-[var(--color-border)] md:block">
                  →
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Persona tabs */}
        <div className="mt-20">
          <div className="flex flex-wrap justify-center gap-3">
            {personas.map((p) => (
              <button
                key={p.id}
                onClick={() => setActivePersona(p.id)}
                className={`flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all ${
                  activePersona === p.id
                    ? 'bg-[var(--color-accent)] text-white'
                    : 'bg-[var(--color-bg-card)] text-[var(--color-text-secondary)] hover:text-white'
                }`}
              >
                <p.icon className="h-4 w-4" />
                {p.label}
              </button>
            ))}
          </div>

          <div className="mt-8 text-center">
            <p className="mx-auto max-w-xl text-lg text-[var(--color-text-secondary)]">
              {personas.find((p) => p.id === activePersona)?.description}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
