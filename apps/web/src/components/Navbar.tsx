'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';

const navLinks = [
  { label: 'Products', href: '#products' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Integrations', href: '#integrations' },
  { label: 'Governance', href: '#governance' },
];

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 z-50 w-full border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]/80 backdrop-blur-xl">
      {/* Early access banner */}
      <div className="bg-gradient-to-r from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] px-4 py-1.5 text-center text-sm font-medium text-white">
        Early Access — Join the waitlist for Recall
      </div>

      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)]">
            <span className="text-sm font-bold text-white">R</span>
          </div>
          <span className="text-xl font-bold text-[var(--color-text-primary)]">Recall</span>
        </Link>

        {/* Desktop links */}
        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden items-center gap-4 md:flex">
          <Link
            href="/app"
            className="text-sm text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
          >
            Dashboard
          </Link>
          <a
            href="#waitlist"
            className="rounded-lg bg-gradient-to-r from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Request Early Access
          </a>
        </div>

        {/* Mobile menu button */}
        <button className="md:hidden" onClick={() => setIsOpen(!isOpen)} aria-label="Toggle menu">
          {isOpen ? (
            <X className="h-6 w-6 text-[var(--color-text-primary)]" />
          ) : (
            <Menu className="h-6 w-6 text-[var(--color-text-primary)]" />
          )}
        </button>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-primary)] px-6 py-4 md:hidden">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="block py-3 text-[var(--color-text-secondary)]"
              onClick={() => setIsOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/app"
            className="block py-3 text-[var(--color-text-secondary)]"
            onClick={() => setIsOpen(false)}
          >
            Dashboard
          </Link>
          <a
            href="#waitlist"
            className="mt-4 block rounded-lg bg-gradient-to-r from-[var(--color-accent-gradient-start)] to-[var(--color-accent-gradient-end)] px-5 py-2.5 text-center text-sm font-medium text-white"
            onClick={() => setIsOpen(false)}
          >
            Request Early Access
          </a>
        </div>
      )}
    </nav>
  );
}
