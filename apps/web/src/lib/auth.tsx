"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { auth as authApi, getToken, setToken, clearToken, type User, ApiError } from "@/lib/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string, orgName: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const u = await authApi.me();
      setUser(u);
    } catch {
      clearToken();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setToken(res.access_token);
    const u = await authApi.me();
    setUser(u);
  };

  const register = async (email: string, name: string, password: string, orgName: string) => {
    const res = await authApi.register(email, name, password, orgName);
    setToken(res.access_token);
    const u = await authApi.me();
    setUser(u);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const u = await authApi.me();
      setUser(u);
    } catch {
      // ignore
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
