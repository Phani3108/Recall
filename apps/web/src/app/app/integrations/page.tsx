"use client";

import { useState, useEffect, useCallback } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Plus,
  RefreshCw,
  ExternalLink,
  X,
  AlertTriangle,
  LogIn,
  Key,
} from "lucide-react";
import { integrations as integrationsApi, type Integration } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoIntegrations } from "@/lib/demo-data";

type ProviderDef = {
  id: string;
  name: string;
  color: string;
  icon: string;
  category: "productivity" | "engineering" | "communication" | "crm" | "ai" | "design" | "storage";
};

const PROVIDERS: ProviderDef[] = [
  { id: "slack", name: "Slack", color: "#E01E5A", icon: "S", category: "communication" },
  { id: "microsoft365", name: "Microsoft 365", color: "#00A4EF", icon: "M", category: "communication" },
  { id: "zoom", name: "Zoom", color: "#2D8CFF", icon: "Z", category: "communication" },
  { id: "whatsapp", name: "WhatsApp", color: "#25D366", icon: "W", category: "communication" },
  { id: "google", name: "Google Workspace", color: "#4285F4", icon: "G", category: "productivity" },
  { id: "notion", name: "Notion", color: "#FFFFFF", icon: "N", category: "productivity" },
  { id: "confluence", name: "Confluence", color: "#1868DB", icon: "C", category: "productivity" },
  { id: "dropbox", name: "Dropbox", color: "#0061FF", icon: "D", category: "storage" },
  { id: "github", name: "GitHub", color: "#8B5CF6", icon: "GH", category: "engineering" },
  { id: "gitlab", name: "GitLab", color: "#FC6D26", icon: "GL", category: "engineering" },
  { id: "jira", name: "Jira", color: "#0052CC", icon: "J", category: "engineering" },
  { id: "linear", name: "Linear", color: "#5E6AD2", icon: "L", category: "engineering" },
  { id: "asana", name: "Asana", color: "#F06A6A", icon: "A", category: "engineering" },
  { id: "cursor", name: "Cursor", color: "#00E5A0", icon: "Cu", category: "engineering" },
  { id: "figma", name: "Figma", color: "#A259FF", icon: "F", category: "design" },
  { id: "hubspot", name: "HubSpot", color: "#FF7A59", icon: "H", category: "crm" },
  { id: "claude", name: "Claude (Anthropic)", color: "#D4A574", icon: "Cl", category: "ai" },
];

const CATEGORIES: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "communication", label: "Communication" },
  { key: "productivity", label: "Productivity & Docs" },
  { key: "engineering", label: "Engineering" },
  { key: "design", label: "Design" },
  { key: "crm", label: "CRM & Sales" },
  { key: "ai", label: "AI" },
  { key: "storage", label: "Storage" },
];

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  connected: { icon: CheckCircle, color: "text-green-400", label: "Connected" },
  active: { icon: CheckCircle, color: "text-green-400", label: "Active" },
  pending: { icon: Clock, color: "text-yellow-400", label: "Pending" },
  disconnected: { icon: XCircle, color: "text-gray-500", label: "Not connected" },
  error: { icon: AlertTriangle, color: "text-red-400", label: "Error" },
  syncing: { icon: Loader2, color: "text-blue-400 animate-spin", label: "Syncing" },
};

type ProviderField = { key: string; label: string; placeholder: string };
type ProviderMeta = {
  fields: ProviderField[];
  help_url: string;
  auth_method: "oauth" | "api_key" | "coming_soon";
  oauth_configured: boolean;
};

function ApiKeyModal({
  provider,
  fields,
  helpUrl,
  onClose,
  onConnect,
}: {
  provider: ProviderDef;
  fields: ProviderField[];
  helpUrl: string;
  onClose: () => void;
  onConnect: (config: Record<string, string>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    for (const f of fields) {
      if (!values[f.key]?.trim()) {
        setError(`${f.label} is required`);
        return;
      }
    }
    setConnecting(true);
    setError(null);
    try {
      await onConnect(values);
      setDone(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
              style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
            >
              {provider.icon}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Connect {provider.name}</h3>
              <p className="text-xs text-gray-400">Enter your API credentials</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {done ? (
          <div className="text-center py-4">
            <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
            <p className="text-white font-medium mb-1">Connected successfully!</p>
            <p className="text-sm text-gray-400">Data is being synced from {provider.name}.</p>
            <button
              onClick={onClose}
              className="mt-4 w-full bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-xl py-2.5 text-sm font-medium transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  {field.label}
                </label>
                <input
                  type={field.key.includes("token") || field.key.includes("key") ? "password" : "text"}
                  placeholder={field.placeholder}
                  value={values[field.key] || ""}
                  onChange={(e) => setValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-[var(--accent)]"
                />
              </div>
            ))}

            {helpUrl && (
              <a
                href={helpUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-[var(--accent)] hover:underline"
              >
                <ExternalLink className="w-3 h-3" />
                How to get your {provider.name} credentials
              </a>
            )}

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={connecting}
              className="w-full bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-xl py-2.5 text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {connecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connecting & syncing...
                </>
              ) : (
                <>
                  <Key className="w-4 h-4" />
                  Connect with API Key
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function IntegrationsPage() {
  const { isDemo, markBackendDown } = useDemo();
  const [integrationsList, setIntegrationsList] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [providerFieldsMap, setProviderFieldsMap] = useState<Record<string, ProviderMeta>>({});
  const [apiKeyProvider, setApiKeyProvider] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState("all");

  useEffect(() => {
    if (isDemo) {
      setIntegrationsList(demoIntegrations);
      // Build a sensible providerFieldsMap for demo
      const demoFields: Record<string, ProviderMeta> = {};
      for (const p of PROVIDERS) {
        const isOAuth = ["slack", "github", "google", "notion", "jira", "linear", "gitlab", "zoom", "dropbox", "figma", "asana", "microsoft365", "confluence"].includes(p.id);
        demoFields[p.id] = {
          fields: isOAuth ? [] : [{ key: "api_key", label: `${p.name} API Key`, placeholder: `Enter your ${p.name} API key` }],
          help_url: `https://${p.id}.com/settings/api`,
          auth_method: isOAuth ? "oauth" : "api_key",
          oauth_configured: isOAuth,
        };
      }
      setProviderFieldsMap(demoFields);
      setLoading(false);
      return;
    }
    Promise.all([
      integrationsApi.list().then(setIntegrationsList),
      integrationsApi.providerFields().then(setProviderFieldsMap),
    ])
      .catch(() => {
        markBackendDown();
        setIntegrationsList(demoIntegrations);
      })
      .finally(() => setLoading(false));
  }, [isDemo, markBackendDown]);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type !== "recall_oauth_callback") return;
      const { provider, success } = event.data as {
        provider: string;
        success: boolean;
        synced: number;
        error?: string;
      };
      setOauthLoading(null);
      if (success) {
        integrationsApi.list().then(setIntegrationsList).catch(console.error);
      } else {
        console.error(`OAuth failed for ${provider}: ${event.data.error}`);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, []);

  const handleOAuthConnect = useCallback(async (providerId: string) => {
    setOauthLoading(providerId);
    try {
      const { auth_url } = await integrationsApi.oauthUrl(providerId);
      const w = 600, h = 700;
      const left = window.screenX + (window.outerWidth - w) / 2;
      const top = window.screenY + (window.outerHeight - h) / 2;
      window.open(auth_url, `recall_oauth_${providerId}`, `width=${w},height=${h},left=${left},top=${top}`);
    } catch {
      setOauthLoading(null);
      setApiKeyProvider(providerId);
    }
  }, []);

  const handleApiKeyConnect = async (providerId: string, config: Record<string, string>) => {
    let integration = integrationsList.find((i) => i.provider === providerId);
    if (!integration) {
      integration = await integrationsApi.create(providerId);
      setIntegrationsList((prev) => [...prev, integration!]);
    }
    const result = await integrationsApi.connect(integration.id, config);
    if (result.error) throw new Error(result.error);
    setIntegrationsList((prev) =>
      prev.map((i) =>
        i.id === integration!.id ? { ...i, status: result.status, last_synced_at: new Date().toISOString() } : i,
      ),
    );
  };

  const handleSync = async (integrationId: string) => {
    setSyncing(integrationId);
    try {
      const result = await integrationsApi.sync(integrationId);
      setIntegrationsList((prev) =>
        prev.map((i) =>
          i.id === integrationId ? { ...i, status: result.status, last_synced_at: new Date().toISOString() } : i,
        ),
      );
    } catch (err) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(null);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    try {
      await integrationsApi.disconnect(integrationId);
      setIntegrationsList((prev) =>
        prev.map((i) => (i.id === integrationId ? { ...i, status: "disconnected" } : i)),
      );
    } catch (err) {
      console.error("Failed to disconnect:", err);
    }
  };

  const handleConnect = (provider: ProviderDef) => {
    const meta = providerFieldsMap[provider.id];
    if (!meta) {
      setApiKeyProvider(provider.id);
      return;
    }
    if (meta.auth_method === "coming_soon") return;
    if (meta.auth_method === "oauth" && meta.oauth_configured) {
      handleOAuthConnect(provider.id);
    } else {
      setApiKeyProvider(provider.id);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  const connectedCount = integrationsList.filter(
    (i) => i.status === "active" || i.status === "connected",
  ).length;

  const filtered = activeCategory === "all"
    ? PROVIDERS
    : PROVIDERS.filter((p) => p.category === activeCategory);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">Integrations</h1>
        <p className="text-gray-400">
          Connect your tools to give Recall access to your organization&apos;s context.
          {connectedCount > 0 && (
            <span className="text-[var(--accent)] ml-2">{connectedCount} connected</span>
          )}
        </p>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setActiveCategory(cat.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
              activeCategory === cat.key
                ? "bg-[var(--accent)] text-white"
                : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((provider) => {
          const integration = integrationsList.find((i) => i.provider === provider.id);
          const meta = providerFieldsMap[provider.id];
          const isComingSoon = meta?.auth_method === "coming_soon";
          const isOAuth = meta?.auth_method === "oauth";
          const status = integration
            ? statusConfig[integration.status] || statusConfig.disconnected
            : statusConfig.disconnected;
          const StatusIcon = status.icon;
          const isConnected = integration?.status === "connected" || integration?.status === "active";
          const isSyncing = syncing === integration?.id;
          const isOAuthLoading = oauthLoading === provider.id;

          return (
            <div
              key={provider.id}
              className={`glass-card p-4 flex items-center gap-4 ${isComingSoon ? "opacity-50" : ""}`}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
                style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
              >
                {provider.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-white truncate">{provider.name}</h3>
                  {isComingSoon && (
                    <span className="text-[10px] bg-white/10 text-gray-400 px-1.5 py-0.5 rounded-full">
                      Soon
                    </span>
                  )}
                </div>
                <div className={`flex items-center gap-1 text-xs ${status.color}`}>
                  <StatusIcon className="w-3 h-3" />
                  {status.label}
                  {integration?.last_synced_at && isConnected && (
                    <span className="text-gray-500 ml-1">
                      &middot; {new Date(integration.last_synced_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>

              {isConnected ? (
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => handleSync(integration!.id)}
                    disabled={isSyncing}
                    className="p-2 rounded-lg border border-white/10 text-gray-400 hover:text-[var(--accent)] hover:border-[var(--accent)]/30 transition-colors disabled:opacity-50"
                    title="Re-sync data"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                  </button>
                  <button
                    onClick={() => handleDisconnect(integration!.id)}
                    className="text-xs text-gray-400 hover:text-red-400 transition-colors px-2.5 py-1.5 rounded-lg border border-white/10 hover:border-red-400/30"
                  >
                    Disconnect
                  </button>
                </div>
              ) : isComingSoon ? (
                <span className="text-xs text-gray-500 shrink-0">Coming soon</span>
              ) : (
                <button
                  onClick={() => handleConnect(provider)}
                  disabled={isOAuthLoading}
                  className="flex items-center gap-1.5 text-xs text-[var(--accent)] px-3 py-1.5 rounded-lg border border-[var(--accent)]/30 hover:bg-[var(--accent)]/10 transition-colors disabled:opacity-50 shrink-0"
                >
                  {isOAuthLoading ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : isOAuth && meta?.oauth_configured ? (
                    <LogIn className="w-3 h-3" />
                  ) : (
                    <Plus className="w-3 h-3" />
                  )}
                  {isOAuth && meta?.oauth_configured ? "Sign in" : "Connect"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {apiKeyProvider && (
        <ApiKeyModal
          provider={PROVIDERS.find((p) => p.id === apiKeyProvider)!}
          fields={
            providerFieldsMap[apiKeyProvider]?.fields || [
              { key: "token", label: "API Token", placeholder: "Enter token..." },
            ]
          }
          helpUrl={providerFieldsMap[apiKeyProvider]?.help_url || ""}
          onClose={() => setApiKeyProvider(null)}
          onConnect={async (config) => {
            await handleApiKeyConnect(apiKeyProvider, config);
          }}
        />
      )}
    </div>
  );
}
