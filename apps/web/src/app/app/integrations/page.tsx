"use client";

import { useState, useEffect } from "react";
import { Plug, CheckCircle, XCircle, Clock, Loader2, Plus } from "lucide-react";
import { integrations as integrationsApi, type Integration } from "@/lib/api";

const PROVIDERS = [
  { id: "slack", name: "Slack", color: "#E01E5A" },
  { id: "google", name: "Google Workspace", color: "#4285F4" },
  { id: "github", name: "GitHub", color: "#8B5CF6" },
  { id: "notion", name: "Notion", color: "#FFFFFF" },
  { id: "jira", name: "Jira", color: "#0052CC" },
  { id: "linear", name: "Linear", color: "#5E6AD2" },
  { id: "confluence", name: "Confluence", color: "#1868DB" },
  { id: "gitlab", name: "GitLab", color: "#FC6D26" },
  { id: "microsoft365", name: "Microsoft 365", color: "#00A4EF" },
  { id: "dropbox", name: "Dropbox", color: "#0061FF" },
];

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  connected: { icon: CheckCircle, color: "text-green-400", label: "Connected" },
  active: { icon: CheckCircle, color: "text-green-400", label: "Active" },
  pending: { icon: Clock, color: "text-yellow-400", label: "Pending" },
  disconnected: { icon: XCircle, color: "text-gray-500", label: "Not connected" },
  error: { icon: XCircle, color: "text-red-400", label: "Error" },
  syncing: { icon: Loader2, color: "text-blue-400", label: "Syncing" },
};

export default function IntegrationsPage() {
  const [integrationsList, setIntegrationsList] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    integrationsApi.list().then(setIntegrationsList).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleConnect = async (providerId: string) => {
    setConnecting(providerId);
    try {
      // Check if integration already exists
      let integration = integrationsList.find((i) => i.provider === providerId);

      if (!integration) {
        integration = await integrationsApi.create(providerId);
        setIntegrationsList((prev) => [...prev, integration!]);
      }

      const result = await integrationsApi.connect(integration.id);
      if (result.redirect_url) {
        window.open(result.redirect_url, "_blank", "width=600,height=700");
      }
    } catch (err) {
      console.error("Failed to connect:", err);
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    try {
      await integrationsApi.disconnect(integrationId);
      setIntegrationsList((prev) =>
        prev.map((i) =>
          i.id === integrationId ? { ...i, status: "disconnected" } : i,
        ),
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

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Integrations</h1>
      <p className="text-gray-400 mb-8">
        Connect your tools to give Ask access to your organization&apos;s context.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PROVIDERS.map((provider) => {
          const integration = integrationsList.find(
            (i) => i.provider === provider.id,
          );
          const status = integration
            ? statusConfig[integration.status] || statusConfig.disconnected
            : statusConfig.disconnected;
          const StatusIcon = status.icon;
          const isConnected = integration?.status === "connected" || integration?.status === "active";

          return (
            <div
              key={provider.id}
              className="glass-card p-4 flex items-center gap-4"
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold"
                style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
              >
                {provider.name.charAt(0)}
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-white">
                  {provider.name}
                </h3>
                <div className={`flex items-center gap-1 text-xs ${status.color}`}>
                  <StatusIcon className="w-3 h-3" />
                  {status.label}
                </div>
              </div>
              {isConnected ? (
                <button
                  onClick={() => handleDisconnect(integration!.id)}
                  className="text-xs text-gray-400 hover:text-red-400 transition-colors px-3 py-1.5 rounded-lg border border-white/10 hover:border-red-400/30"
                >
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={() => handleConnect(provider.id)}
                  disabled={connecting === provider.id}
                  className="flex items-center gap-1 text-xs text-[var(--accent)] px-3 py-1.5 rounded-lg border border-[var(--accent)]/30 hover:bg-[var(--accent)]/10 transition-colors disabled:opacity-50"
                >
                  {connecting === provider.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Plus className="w-3 h-3" />
                  )}
                  Connect
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
