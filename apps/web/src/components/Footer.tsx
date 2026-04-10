import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-bg-primary)]">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-4">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)]">
                <span className="text-sm font-bold text-white">R</span>
              </div>
              <span className="text-xl font-bold">Recall</span>
            </div>
            <p className="mt-4 text-sm text-[var(--color-text-secondary)]">
              The Work OS for AI-Native Organizations.
            </p>
          </div>

          {/* Products */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Products
            </h4>
            <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
              <li><a href="#ask" className="hover:text-[var(--color-text-primary)]">Ask</a></li>
              <li><a href="#pilot" className="hover:text-[var(--color-text-primary)]">Pilot</a></li>
              <li><a href="#flow" className="hover:text-[var(--color-text-primary)]">Flow</a></li>
              <li><Link href="/app" className="hover:text-[var(--color-text-primary)]">Dashboard</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Company
            </h4>
            <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">About</a></li>
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">Blog</a></li>
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">Careers</a></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Legal
            </h4>
            <ul className="space-y-3 text-sm text-[var(--color-text-secondary)]">
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">Privacy</a></li>
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">Terms</a></li>
              <li><a href="#" className="hover:text-[var(--color-text-primary)]">Security</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-[var(--color-border)] pt-8 text-center text-sm text-[var(--color-text-muted)]">
          &copy; {new Date().getFullYear()} Recall. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
