import { ArrowRight, Play } from 'lucide-react';

export default function HeroSection() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 pt-32">
      {/* Background gradient orbs */}
      <div className="pointer-events-none absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-[var(--color-accent-gradient-start)] opacity-10 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-40 right-1/4 h-[400px] w-[400px] rounded-full bg-[var(--color-accent-gradient-end)] opacity-10 blur-[120px]" />

      <div className="relative z-10 mx-auto max-w-5xl text-center">
        {/* Badge */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-card)] px-4 py-2 text-sm text-[var(--color-text-secondary)]">
          <span className="h-2 w-2 rounded-full bg-[var(--color-success)]" />
          Now in Early Access
        </div>

        {/* Headline */}
        <h1 className="text-5xl font-bold leading-tight tracking-tight md:text-7xl">
          The Work OS for{' '}
          <span className="gradient-text">AI-Native</span>{' '}
          Organizations
        </h1>

        {/* Sub-headline */}
        <p className="mx-auto mt-6 max-w-2xl text-lg text-[var(--color-text-secondary)] md:text-xl">
          Enterprise AI that doesn&apos;t just answer questions — it does work.
          One platform. Complete context. Every workflow.
        </p>

        {/* CTAs */}
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="#waitlist"
            className="group flex items-center gap-2 rounded-lg bg-gradient-to-r from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] px-8 py-3.5 text-base font-semibold text-white transition-all hover:opacity-90 hover:shadow-lg hover:shadow-[var(--color-accent)]/20"
          >
            Request Early Access
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </a>
          <a
            href="#how-it-works"
            className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-8 py-3.5 text-base font-semibold text-[var(--color-text-primary)] transition-all hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-card-hover)]"
          >
            <Play className="h-4 w-4" />
            See How It Works
          </a>
        </div>

        {/* Hero visual — abstract node constellation */}
        <div className="relative mx-auto mt-20 h-[300px] w-full max-w-3xl md:h-[400px]">
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Central AI node */}
            <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] shadow-lg shadow-[var(--color-accent)]/30">
              <span className="text-2xl font-bold text-white">AI</span>
            </div>

            {/* Orbiting nodes representing connected tools */}
            {[
              { label: 'Slack', top: '10%', left: '20%', delay: '0s' },
              { label: 'GitHub', top: '15%', right: '15%', delay: '0.5s' },
              { label: 'Jira', bottom: '20%', left: '15%', delay: '1s' },
              { label: 'Docs', bottom: '15%', right: '20%', delay: '1.5s' },
              { label: 'Gmail', top: '45%', left: '5%', delay: '2s' },
              { label: 'Notion', top: '45%', right: '5%', delay: '2.5s' },
            ].map((node) => (
              <div
                key={node.label}
                className="glass-card absolute flex h-12 w-12 items-center justify-center rounded-xl text-xs font-medium text-[var(--color-text-secondary)] md:h-14 md:w-14"
                style={{
                  top: node.top,
                  left: node.left,
                  right: node.right,
                  bottom: node.bottom,
                  animationDelay: node.delay,
                }}
              >
                {node.label}
              </div>
            ))}

            {/* Connection lines (decorative SVG) */}
            <svg className="absolute inset-0 h-full w-full" xmlns="http://www.w3.org/2000/svg">
              <line x1="50%" y1="50%" x2="20%" y2="15%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
              <line x1="50%" y1="50%" x2="80%" y2="20%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
              <line x1="50%" y1="50%" x2="15%" y2="75%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
              <line x1="50%" y1="50%" x2="80%" y2="80%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
              <line x1="50%" y1="50%" x2="8%" y2="50%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
              <line x1="50%" y1="50%" x2="92%" y2="50%" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}
