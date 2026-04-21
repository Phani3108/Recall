"use client";

import { useDemo } from "@/lib/demo";
import { Eye, Wifi, WifiOff } from "lucide-react";

export function DemoBanner() {
  const { isDemo, toggleDemo, apiReachabilityError, setApiReachabilityError } = useDemo();

  return (
    <>
      {apiReachabilityError && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-4 py-2 flex items-center justify-between gap-3">
          <p className="text-sm text-amber-200">{apiReachabilityError}</p>
          <button
            type="button"
            onClick={() => setApiReachabilityError(null)}
            className="text-xs text-amber-100/80 hover:text-amber-50 shrink-0"
          >
            Dismiss
          </button>
        </div>
      )}
      {isDemo && (
        <div className="bg-[var(--accent)]/10 border-b border-[var(--accent)]/20 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-[var(--accent)]">
            <Eye className="w-4 h-4" />
            <span className="font-medium">Demo Mode</span>
            <span className="text-gray-400">
              — Showing sample data. Connect backend or sign in for live data.
            </span>
          </div>
          <button
            onClick={toggleDemo}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white px-2 py-1 rounded-md hover:bg-white/5 transition-colors"
          >
            <WifiOff className="w-3 h-3" />
            Exit Demo
          </button>
        </div>
      )}
    </>
  );
}

export function DemoToggle() {
  const { isDemo, toggleDemo } = useDemo();

  return (
    <button
      onClick={toggleDemo}
      className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-md transition-colors ${
        isDemo
          ? "text-[var(--accent)] bg-[var(--accent)]/10 hover:bg-[var(--accent)]/20"
          : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
      }`}
      title={isDemo ? "Switch to live mode" : "Switch to demo mode"}
    >
      {isDemo ? <Eye className="w-3.5 h-3.5" /> : <Wifi className="w-3.5 h-3.5" />}
      {isDemo ? "Demo" : "Live"}
    </button>
  );
}
