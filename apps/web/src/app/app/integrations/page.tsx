"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plug,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Plus,
  RefreshCw,
  ExternalLink,
  X,
  AlertTriangle,
} from "lucide-react";
import { integrations as integrationsApi, type Integration } from "@/lib/api";

const PROVIDERS = [
  { id: "slack", name: "Slack", color: "#E01E5A", icon: "S" },
  { id: "google", name: "Google Workspace", color: "#4285F4", icon: "G" },
  { id: "github", name: "GitHub", color: "#8B5CF6", icon: "GH" },
  { id: "notion", name: "Notion", color: "#FFFFFF", icon: "N" },
  { id: "jira", name: "Jira", color: "#0052CC", icon: "J" },
  { id: "linear", name: "Linear", color: "#5E6AD2", icon: "L" },
  { id: "confluence", name: "Confluence", color: "#1868DB", icon: "C" },
  { id: "gitlab", name: "GitLab", color: "#FC6D26", icon: "GL" },
  { id: "microsoft365", name: "Microsoft 365", color: "#00A4EF", icon: "M" },
  { id: "dropbox", name: "Dropbox", color: "#0061FF", icon: "D" },
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
type ProviderMeta = { fields: ProviderField[]; help_url: string };

function ConnectModal({
  provider,
  fields,
  helpUrl,
  onClose,
  onConnect,
}: {
  provider: typeof PROVIDERS[0];
  fields: ProviderField[];
  helpUrl: string;
  onClose: () => void;
  onConnect: (config: Record<string, string>) => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ synced: number } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Validate required fields
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
      setResult({ synced: 1 }); // will be overwritten by actual result
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

        {result ? (
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
                  type={field.key === "token" ? "password" : "text"}
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
                  <Plug className="w-4 h-4" />
                  Connect & Sync
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
  const [integrationsList, setIntegrationsList] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [providerFieldsMap, setProviderFieldsMap] = useState<Record<string, ProviderMeta>>({});
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      integrationsApi.list().then(setIntegrationsList),
      integrationsApi.providerFields().then(setProviderFieldsMap),
    ])
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleConnect = async (providerId: string, config: Record<string, string>) => {
    let integration = integrationsList.find((i) => i.provider === providerId);

    if (!integration) {
      integration = await integrationsApi.create(providerId);
      setIntegrationsList((prev) => [...prev, integration!]);
    }

    const result = await integrationsApi.connect(integration.id, config);
    if (result.error) {
      throw new Error(result.error);
    }

    // Update status in list
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

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Integrations</h1>
      <p className="text-gray-400 mb-8">
        Connect your tools to give Ask access to your organization&apos;s context.
        {connectedCount > 0 && (
          <span className="text-[var(--accent)] ml-2">{connectedCount} connected</span>
        )}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PROVIDERS.map((provider) => {
          const integration = integrationsList.find((i) => i.provider === provider.id);
          const status = integration
            ? statusConfig[integration.status] || statusConfig.disconnected
            : statusConfig.disconnected;
          const StatusIcon = status.icon;
          const isConnected = integration?.status === "connected" || integration?.status === "active";
          const isSyncing = syncing === integration?.id;

          return (
            <div key={provider.id} className="glass-card p-4 flex items-center gap-4">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
                style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
              >
                {provider.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-white">{provider.name}</h3>
                <div className={`flex items-center gap-1 text-xs ${status.color}`}>
                  <StatusIcon className="w-3 h-3" />
                  {status.label}
                  {integration?.last_synced_at && isConnected && (
                    <span className="text-gray-500 ml-1">
                      · synced {new Date(integration.last_synced_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              {isConnected ? (
                <div className="flex gap-1.5">
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
                    className="text-xs text-gray-400 hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg border border-white/10 hover:border-red-400/30"
                  >
                    Disconnect
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConnectingProvider(provider.id)}
                  className="flex items-center gap-1 text-xs text-[var(--accent)] px-3 py-1.5 rounded-lg border border-[var(--accent)]/30 hover:bg-[var(--accent)]/10 transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  Connect
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Connect Modal */}
      {connectingProvider && (
        <ConnectModal
          provider={PROVIDERS.find((p) => p.id === connectingProvider)!}
          fields={providerFieldsMap[connectingProvider]?.fields || [{ key: "token", label: "API Token", placeholder: "Enter token..." }]}
          helpUrl={providerFieldsMap[connectingProvider]?.help_url || ""}
          onClose={() => setConnectingProvider(null)}
          onConnect={async (config) => {
            await handleConnect(connectingProvider, config);
          }}
        />
      )}
    </div>
  );
}
