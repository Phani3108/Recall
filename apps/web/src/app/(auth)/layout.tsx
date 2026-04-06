"use client";

import dynamic from "next/dynamic";
import { AuthProvider } from "@/lib/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
