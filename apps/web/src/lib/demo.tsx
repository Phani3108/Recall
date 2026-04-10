"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface DemoState {
  /** true when the frontend is running in demo / offline mode */
  isDemo: boolean;
  /** User explicitly toggled demo mode on */
  enableDemo: () => void;
  /** User explicitly toggled demo mode off */
  disableDemo: () => void;
  /** Toggle current state */
  toggleDemo: () => void;
  /** Called by API layer when backend is unreachable — auto-enables demo */
  markBackendDown: () => void;
}

const DEMO_KEY = "recall_demo_mode";

function getInitial(): boolean {
  if (typeof window === "undefined") return true;
  const stored = localStorage.getItem(DEMO_KEY);
  // Default to demo mode (true) unless explicitly set to "false"
  return stored !== "false";
}

const DemoContext = createContext<DemoState | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [isDemo, setIsDemo] = useState(getInitial);

  const persist = useCallback((v: boolean) => {
    setIsDemo(v);
    if (typeof window !== "undefined") {
      localStorage.setItem(DEMO_KEY, String(v));
    }
  }, []);

  const enableDemo = useCallback(() => persist(true), [persist]);
  const disableDemo = useCallback(() => persist(false), [persist]);
  const toggleDemo = useCallback(() => persist(!isDemo), [persist, isDemo]);
  const markBackendDown = useCallback(() => {
    // Only auto-enable if not already in live mode explicitly
    if (!isDemo) persist(true);
  }, [persist, isDemo]);

  return (
    <DemoContext.Provider value={{ isDemo, enableDemo, disableDemo, toggleDemo, markBackendDown }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo(): DemoState {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error("useDemo must be used within DemoProvider");
  return ctx;
}
