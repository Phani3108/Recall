"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { users } from "@/lib/api";

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    setSaved(false);
    try {
      await users.updateMe({ name: name.trim() });
      await refreshUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>

      {/* Profile */}
      <section className="glass-card p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Profile</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email</label>
            <input
              type="email"
              defaultValue={user?.email}
              disabled
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-gray-500 cursor-not-allowed"
            />
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-4 py-2 text-sm transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : saved ? "Saved!" : "Save changes"}
          </button>
        </div>
      </section>

      {/* Danger zone */}
      <section className="glass-card p-6 border-red-500/20">
        <h2 className="text-lg font-semibold text-red-400 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-400 mb-4">
          Once you delete your account, there is no going back.
        </p>
        <button className="text-red-400 border border-red-400/30 hover:bg-red-400/10 rounded-lg px-4 py-2 text-sm transition-colors">
          Delete account
        </button>
      </section>
    </div>
  );
}
