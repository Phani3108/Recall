'use client';

import { useState } from 'react';
import { ArrowRight, Shield, Download, Server } from 'lucide-react';

export default function CTASection() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    // TODO: Submit to API / Supabase
    setSubmitted(true);
  };

  return (
    <section id="waitlist" className="relative px-6 py-32">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[var(--color-accent)]/5 to-transparent" />

      <div className="relative mx-auto max-w-3xl text-center">
        <h2 className="text-3xl font-bold md:text-5xl">
          AI that <span className="gradient-text">works</span> — not just talks
        </h2>
        <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
          Join the teams building the future of work.
        </p>

        {submitted ? (
          <div className="mx-auto mt-10 max-w-md rounded-2xl border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-8">
            <div className="text-4xl">✓</div>
            <h3 className="mt-4 text-xl font-semibold text-[var(--color-success)]">
              You&apos;re on the list
            </h3>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
              We&apos;ll be in touch when early access opens.
            </p>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="mx-auto mt-10 flex max-w-md flex-col gap-3 sm:flex-row"
          >
            <input
              type="email"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-card)] px-5 py-3.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
            />
            <button
              type="submit"
              className="group flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] px-6 py-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              Request Early Access
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
          </form>
        )}

        {/* Trust signals */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-[var(--color-text-muted)]">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            Self-hosted or cloud — your choice
          </div>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            SOC 2 on the roadmap
          </div>
          <div className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Your data stays yours — full export
          </div>
        </div>

        <p className="mt-8 text-sm text-[var(--color-text-muted)]">
          Want a demo?{' '}
          <a href="#" className="font-medium text-[var(--color-accent-light)] underline">
            Book a call
          </a>
        </p>
      </div>
    </section>
  );
}
