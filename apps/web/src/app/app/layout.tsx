"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth, AuthProvider } from "@/lib/auth";
import {
  MessageSquare,
  Search,
  Plug,
  Shield,
  Settings,
  LogOut,
  Zap,
  ChevronRight,
  Inbox,
  Layers,
} from "lucide-react";

const navItems = [
  { href: "/app", icon: MessageSquare, label: "Ask" },
  { href: "/app/pilot", icon: Inbox, label: "Pilot" },
  { href: "/app/flow", icon: Layers, label: "Flow" },
  { href: "/app/search", icon: Search, label: "Search" },
  { href: "/app/integrations", icon: Plug, label: "Integrations" },
  { href: "/app/governance", icon: Shield, label: "Governance" },
  { href: "/app/settings", icon: Settings, label: "Settings" },
];

function DashboardShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!user) return null;

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
            <button
              onClick={logout}
              className="text-gray-500 hover:text-gray-300"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
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
    <AuthProvider>
      <DashboardShell>{children}</DashboardShell>
    </AuthProvider>
  );
}
