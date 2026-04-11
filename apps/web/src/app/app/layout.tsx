"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DemoProvider } from "@/lib/demo";
import { demoUser } from "@/lib/demo-data";
import {
  MessageSquare,
  Search,
  Plug,
  Shield,
  Settings,
  Zap,
  Inbox,
  Layers,
  Lock,
  Home,
  Network,
  Bot,
  Sparkles,
  BarChart3,
  Users,
  Bell,
} from "lucide-react";

const navItems = [
  { href: "/app", icon: MessageSquare, label: "Ask" },
  { href: "/app/pilot", icon: Inbox, label: "Pilot" },
  { href: "/app/flow", icon: Layers, label: "Flow" },
  { href: "/app/skills", icon: Sparkles, label: "Skills" },
  { href: "/app/search", icon: Search, label: "Search" },
  { href: "/app/knowledge", icon: Network, label: "Knowledge" },
  { href: "/app/agent", icon: Bot, label: "Agent" },
  { href: "/app/integrations", icon: Plug, label: "Integrations" },
  { href: "/app/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/app/teams", icon: Users, label: "Teams" },
  { href: "/app/notifications", icon: Bell, label: "Notifications" },
  { href: "/app/governance", icon: Shield, label: "Governance" },
  { href: "/app/admin", icon: Lock, label: "Admin" },
  { href: "/app/settings", icon: Settings, label: "Settings" },
];

function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const user = demoUser;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/10 flex flex-col">
        <div className="p-4 border-b border-white/10">
          <Link href="/app" className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-[var(--accent)]" />
            <span className="text-lg font-bold text-white">Recall</span>
          </Link>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const isActive =
              item.href === "/app"
                ? pathname === "/app"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-white/10">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-xs text-[var(--accent)] font-bold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white truncate">{user.name}</div>
              <div className="text-xs text-gray-500 truncate">{user.email}</div>
            </div>
          </div>
          <div className="mt-2 px-3">
            <Link
              href="/"
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 px-2 py-1 rounded-md transition-colors"
            >
              <Home className="w-3.5 h-3.5" />
              Landing Page
            </Link>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <DemoProvider>
      <DashboardShell>{children}</DashboardShell>
    </DemoProvider>
  );
}
