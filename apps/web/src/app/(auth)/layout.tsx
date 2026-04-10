"use client";

import dynamic from "next/dynamic";
import { AuthProvider } from "@/lib/auth";
import { DemoProvider } from "@/lib/demo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <DemoProvider>
      <AuthProvider>{children}</AuthProvider>
    </DemoProvider>
  );
}
