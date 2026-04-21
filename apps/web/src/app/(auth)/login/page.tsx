"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useDemo } from "@/lib/demo";
import { setToken } from "@/lib/api";
import { isStrictApiMode } from "@/lib/strict-api";
import { Eye } from "lucide-react";

function oidcLoginHref(): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  const origin = base.replace(/\/api\/?$/, "");
  return `${origin}/api/auth/oidc/login`;
}

export default function LoginPage() {
  const { login } = useAuth();
  const { enableDemo } = useDemo();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const token = params.get("access_token");
    const err = params.get("error");
    if (err) {
      setError(`SSO error: ${err}`);
    }
    if (token) {
      setToken(token);
      const u = new URL(window.location.href);
      u.searchParams.delete("access_token");
      window.history.replaceState({}, "", `${u.pathname}${u.search}`);
      router.replace("/app");
    }
  }, [router]);

  const handleTryDemo = () => {
    enableDemo();
    router.push("/app");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/app");
    } catch (err: unknown) {
      const isNetworkError = err instanceof TypeError || (err instanceof Error && err.message.includes("fetch"));
      if (isNetworkError) {
        setError(
          isStrictApiMode()
            ? "Cannot reach the Recall API — verify NEXT_PUBLIC_API_URL and that the backend is running."
            : "Backend unavailable — try Demo Mode to explore the app.",
        );
      } else {
        setError(err instanceof Error ? err.message : "Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center px-4">
      <div className="glass-card p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-2">Welcome back</h1>
        <p className="text-gray-400 mb-6">Sign in to Recall</p>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg py-2.5 font-medium transition-colors disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="px-2 bg-[var(--bg-secondary)] text-gray-500">or</span>
          </div>
        </div>

        <a
          href={oidcLoginHref()}
          className="w-full flex items-center justify-center gap-2 border border-white/15 text-white hover:bg-white/5 rounded-lg py-2.5 font-medium transition-colors mb-3"
        >
          Continue with SSO
        </a>

        <button
          type="button"
          onClick={handleTryDemo}
          className="w-full flex items-center justify-center gap-2 border border-[var(--accent)]/30 text-[var(--accent)] hover:bg-[var(--accent)]/10 rounded-lg py-2.5 font-medium transition-colors"
        >
          <Eye className="w-4 h-4" />
          Try Demo — no account needed
        </button>

        <p className="text-gray-400 text-sm mt-6 text-center">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-[var(--accent)] hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
