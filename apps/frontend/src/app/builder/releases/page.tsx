import { getAgentDefinitions, getWorkflowDefinitions } from "@/lib/api";

export default async function ReleasesPage() {
  const [workflows, agents] = await Promise.all([getWorkflowDefinitions(), getAgentDefinitions()]);

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Versions & Releases</h1>
        <p className="fx-muted">Promote workflow/agent versions to current and roll back when needed.</p>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="fx-panel p-4">
          <h2 className="fx-muted mb-3 text-sm font-semibold uppercase tracking-wide">Workflow Definitions</h2>
          <ul className="space-y-2 text-sm">
            {workflows.map((wf) => (
              <li key={wf.id} className="flex items-center justify-between border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
                <span>{wf.name} <span className="fx-muted">v{wf.version}</span></span>
                <button className="fx-btn-secondary px-2 py-1 text-xs">Promote</button>
              </li>
            ))}
          </ul>
        </div>

        <div className="fx-panel p-4">
          <h2 className="fx-muted mb-3 text-sm font-semibold uppercase tracking-wide">Agent Definitions</h2>
          <ul className="space-y-2 text-sm">
            {agents.map((agent) => (
              <li key={agent.id} className="flex items-center justify-between border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
                <span>{agent.name} <span className="fx-muted">v{agent.version}</span></span>
                <button className="fx-btn-secondary px-2 py-1 text-xs">Promote</button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
