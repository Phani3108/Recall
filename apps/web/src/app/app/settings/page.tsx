"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { users, orgSettings, type OrgSettings } from "@/lib/api";
import {
  Key,
  Shield,
  User,
  Trash2,
  Eye,
  EyeOff,
  Check,
  Loader2,
  AlertTriangle,
  Crown,
} from "lucide-react";

type Tab = "profile" | "keys" | "license";

export default function SettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("profile");

  const tabs = [
    { id: "profile" as Tab, label: "Profile", icon: User },
    { id: "keys" as Tab, label: "API Keys", icon: Key },
    { id: "license" as Tab, label: "License", icon: Shield },
  ];

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white/5 rounded-lg p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors flex-1 justify-center ${
              tab === t.id
                ? "bg-[var(--accent)] text-white"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "profile" && <ProfileTab />}
      {tab === "keys" && <ApiKeysTab />}
      {tab === "license" && <LicenseTab />}
    </div>
  );
}

/* ── Profile Tab ── */
function ProfileTab() {
  const { user, refreshUser, logout } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await users.deleteMe();
      logout();
    } catch (err) {
      console.error("Failed to delete:", err);
      setDeleting(false);
    }
  };

  return (
    <>
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
          <div>
            <label className="block text-sm text-gray-400 mb-1">Role</label>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[var(--accent)]/20 text-[var(--accent)]">
              {user?.role === "owner" && <Crown className="w-3 h-3" />}
              {user?.role ?? "member"}
            </span>
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
      <section className="glass-card p-6 border border-red-500/20">
        <h2 className="text-lg font-semibold text-red-400 mb-2">Danger Zone</h2>
        {!showDeleteConfirm ? (
          <>
            <p className="text-sm text-gray-400 mb-4">
              Once you delete your account, there is no going back.
            </p>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="text-red-400 border border-red-400/30 hover:bg-red-400/10 rounded-lg px-4 py-2 text-sm transition-colors"
            >
              Delete account
            </button>
          </>
        ) : (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span className="text-red-400 font-medium">Are you sure?</span>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              This will permanently deactivate your account and remove all org memberships.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="bg-red-500 hover:bg-red-600 text-white rounded-lg px-4 py-2 text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                {deleting ? "Deleting..." : "Yes, delete my account"}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="text-gray-400 hover:text-white border border-white/10 rounded-lg px-4 py-2 text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

/* ── API Keys Tab ── */
function ApiKeysTab() {
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  // Editable key values — empty string means no change
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [composioKey, setComposioKey] = useState("");

  // Visibility toggles
  const [showOpenai, setShowOpenai] = useState(false);
  const [showAnthropic, setShowAnthropic] = useState(false);
  const [showComposio, setShowComposio] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await orgSettings.get();
      setSettings(data);
    } catch (err) {
      setError("Failed to load settings. You may not have admin access.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updates: Record<string, string> = {};
      if (openaiKey.trim()) updates.openai_api_key = openaiKey.trim();
      if (anthropicKey.trim()) updates.anthropic_api_key = anthropicKey.trim();
      if (composioKey.trim()) updates.composio_api_key = composioKey.trim();

      if (Object.keys(updates).length === 0) {
        setError("Enter at least one API key to save.");
        setSaving(false);
        return;
      }

      await orgSettings.updatePlatformKeys(updates);
      // Clear inputs and reload
      setOpenaiKey("");
      setAnthropicKey("");
      setComposioKey("");
      await loadSettings();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      setError(err?.detail || "Failed to save keys.");
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveKey = async (keyName: string) => {
    try {
      await orgSettings.removePlatformKey(keyName);
      await loadSettings();
    } catch (err: any) {
      setError(err?.detail || "Failed to remove key.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const keys = [
    {
      name: "openai_api_key",
      label: "OpenAI API Key",
      desc: "Powers GPT-4o, GPT-4o-mini for Ask chat",
      placeholder: "sk-...",
      value: openaiKey,
      setValue: setOpenaiKey,
      show: showOpenai,
      setShow: setShowOpenai,
      current: settings?.platform_keys.openai_api_key,
    },
    {
      name: "anthropic_api_key",
      label: "Anthropic API Key",
      desc: "Powers Claude models for Ask chat",
      placeholder: "sk-ant-...",
      value: anthropicKey,
      setValue: setAnthropicKey,
      show: showAnthropic,
      setShow: setShowAnthropic,
      current: settings?.platform_keys.anthropic_api_key,
    },
    {
      name: "composio_api_key",
      label: "Composio API Key",
      desc: "Powers OAuth integrations (Slack, GitHub, Jira, etc.)",
      placeholder: "cmp_...",
      value: composioKey,
      setValue: setComposioKey,
      show: showComposio,
      setShow: setShowComposio,
      current: settings?.platform_keys.composio_api_key,
    },
  ];

  return (
    <section className="glass-card p-6">
      <div className="flex items-center gap-2 mb-1">
        <Key className="w-5 h-5 text-[var(--accent)]" />
        <h2 className="text-lg font-semibold text-white">Platform API Keys</h2>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        Enter your API keys to enable AI features and integrations. Keys are stored securely and never exposed in full.
      </p>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="space-y-5">
        {keys.map((k) => (
          <div key={k.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-white">{k.label}</label>
                <span className="text-xs text-gray-500">{k.desc}</span>
              </div>
              {k.current && (
                <button
                  onClick={() => handleRemoveKey(k.name)}
                  className="text-xs text-red-400 hover:text-red-300 transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
            {k.current && (
              <div className="text-xs text-green-400 flex items-center gap-1">
                <Check className="w-3 h-3" />
                Configured: {k.current}
              </div>
            )}
            <div className="relative">
              <input
                type={k.show ? "text" : "password"}
                value={k.value}
                onChange={(e) => k.setValue(e.target.value)}
                placeholder={k.current ? "Enter new key to replace..." : k.placeholder}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[var(--accent)] pr-10"
              />
              <button
                type="button"
                onClick={() => k.setShow(!k.show)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {k.show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-6 bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-6 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
      >
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
        {saving ? "Saving..." : saved ? "Saved!" : "Save API Keys"}
      </button>
    </section>
  );
}

/* ── License Tab ── */
function LicenseTab() {
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [licenseKey, setLicenseKey] = useState("");
  const [activating, setActivating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await orgSettings.get();
      setSettings(data);
    } catch {
      setError("Failed to load license info.");
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!licenseKey.trim()) return;
    setActivating(true);
    setError("");
    setSuccess("");
    try {
      const result = await orgSettings.activateLicense(licenseKey.trim());
      setSuccess(`License activated! Tier: ${result.tier.toUpperCase()}`);
      setLicenseKey("");
      await loadSettings();
    } catch (err: any) {
      setError(err?.detail || "Invalid license key.");
    } finally {
      setActivating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const tierColors: Record<string, string> = {
    free: "text-gray-400 bg-gray-400/10",
    pro: "text-blue-400 bg-blue-400/10",
    enterprise: "text-purple-400 bg-purple-400/10",
  };

  const tier = settings?.license.tier || "free";

  return (
    <section className="glass-card p-6">
      <div className="flex items-center gap-2 mb-1">
        <Shield className="w-5 h-5 text-[var(--accent)]" />
        <h2 className="text-lg font-semibold text-white">License</h2>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        Manage your organization&apos;s license to unlock features.
      </p>

      {/* Current license status */}
      <div className="bg-white/5 rounded-lg p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">Current Tier</span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${tierColors[tier] || tierColors.free}`}>
            {tier}
          </span>
        </div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">License Key</span>
          <span className="text-sm text-white">
            {settings?.license.license_key_set ? "Configured" : "Not set"}
          </span>
        </div>
        {settings?.license.valid_until && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Valid Until</span>
            <span className="text-sm text-white">
              {new Date(settings.license.valid_until).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>

      {/* Feature comparison */}
      <div className="bg-white/5 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-white mb-3">Features by Tier</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between text-gray-400">
            <span>Ask (AI Chat)</span>
            <div className="flex gap-4">
              <span className={tier === "free" ? "text-green-400" : "text-gray-600"}>Free ✓</span>
              <span className={tier === "pro" ? "text-green-400" : "text-gray-600"}>Pro ✓</span>
              <span className={tier === "enterprise" ? "text-green-400" : "text-gray-600"}>Ent ✓</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-gray-400">
            <span>Flow (Tasks)</span>
            <div className="flex gap-4">
              <span className={tier === "free" ? "text-green-400" : "text-gray-600"}>Free ✓</span>
              <span className={tier === "pro" ? "text-green-400" : "text-gray-600"}>Pro ✓</span>
              <span className={tier === "enterprise" ? "text-green-400" : "text-gray-600"}>Ent ✓</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-gray-400">
            <span>Pilot (Delegations)</span>
            <div className="flex gap-4">
              <span className="text-gray-600">Free —</span>
              <span className={tier === "pro" ? "text-green-400" : "text-gray-600"}>Pro ✓</span>
              <span className={tier === "enterprise" ? "text-green-400" : "text-gray-600"}>Ent ✓</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-gray-400">
            <span>Admin Panel</span>
            <div className="flex gap-4">
              <span className="text-gray-600">Free —</span>
              <span className="text-gray-600">Pro —</span>
              <span className={tier === "enterprise" ? "text-green-400" : "text-gray-600"}>Ent ✓</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-gray-400">
            <span>Unlimited Integrations</span>
            <div className="flex gap-4">
              <span className="text-gray-600">Free —</span>
              <span className={tier === "pro" ? "text-green-400" : "text-gray-600"}>Pro ✓</span>
              <span className={tier === "enterprise" ? "text-green-400" : "text-gray-600"}>Ent ✓</span>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-sm mb-4">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg p-3 text-sm mb-4">
          {success}
        </div>
      )}

      {/* Activate license */}
      <div>
        <label className="block text-sm font-medium text-white mb-2">Activate License Key</label>
        <div className="flex gap-3">
          <input
            type="text"
            value={licenseKey}
            onChange={(e) => setLicenseKey(e.target.value)}
            placeholder="RECALL-PRO-XXXX-XXXX or RECALL-ENT-XXXX-XXXX"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[var(--accent)]"
          />
          <button
            onClick={handleActivate}
            disabled={activating || !licenseKey.trim()}
            className="bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-6 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
          >
            {activating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            {activating ? "Activating..." : "Activate"}
          </button>
        </div>
      </div>
    </section>
  );
}
