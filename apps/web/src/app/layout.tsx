import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Recall — The Work OS for AI-Native Organizations',
  description:
    'Enterprise AI that doesn\'t just answer questions — it does work. One platform. Complete context. Every workflow.',
  keywords: ['AI', 'enterprise', 'work OS', 'AI assistant', 'agent platform', 'workflow automation'],
  openGraph: {
    title: 'Recall — The Work OS for AI-Native Organizations',
    description: 'Enterprise AI that does work, not just talks.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
