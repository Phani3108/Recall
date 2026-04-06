const integrations = {
  'Day 1 — Deep Integrations': [
    { name: 'Slack', color: '#E01E5A' },
    { name: 'Google Workspace', color: '#4285F4' },
    { name: 'GitHub', color: '#ffffff' },
    { name: 'Notion', color: '#ffffff' },
    { name: 'Jira', color: '#0052CC' },
  ],
  'Day 30': [
    { name: 'Microsoft 365', color: '#D83B01' },
    { name: 'Linear', color: '#5E6AD2' },
    { name: 'Confluence', color: '#1868DB' },
    { name: 'GitLab', color: '#FC6D26' },
    { name: 'Dropbox', color: '#0061FF' },
  ],
  'Day 60': [
    { name: 'Salesforce', color: '#00A1E0' },
    { name: 'HubSpot', color: '#FF7A59' },
    { name: 'Zendesk', color: '#03363D' },
    { name: 'Datadog', color: '#632CA6' },
    { name: 'PagerDuty', color: '#06AC38' },
  ],
};

export default function IntegrationsSection() {
  return (
    <section id="integrations" className="relative px-6 py-32">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold md:text-5xl">
            Connects to <span className="gradient-text">everything</span> your team uses
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--color-text-secondary)]">
            Two clicks to connect. AI starts learning in minutes. No engineering required.
          </p>
        </div>

        <div className="mt-16 space-y-12">
          {Object.entries(integrations).map(([tier, apps]) => (
            <div key={tier}>
              <h3 className="mb-6 text-center text-sm font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                {tier}
              </h3>
              <div className="flex flex-wrap items-center justify-center gap-4">
                {apps.map((app) => (
                  <div
                    key={app.name}
                    className="glass-card flex items-center gap-3 rounded-xl px-5 py-3 transition-all hover:border-[var(--color-accent)]/30"
                  >
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: app.color }}
                    />
                    <span className="text-sm font-medium">{app.name}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <p className="text-[var(--color-text-secondary)]">
            <span className="font-semibold text-[var(--color-text-primary)]">+1000 more</span> via
            our open connector framework
          </p>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">
            All integrations work with self-hosted deployments. Your data never leaves your
            infrastructure.
          </p>
        </div>
      </div>
    </section>
  );
}
