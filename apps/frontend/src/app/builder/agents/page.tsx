import { randomUUID } from "node:crypto";
import Link from "next/link";
import { TypedDeleteButton } from "@/components/typed-delete-button";
import { ImportExportControls } from "@/components/import-export-controls";
import { getAgentDefinitions } from "@/lib/api";

export default async function BuilderAgentsPage() {
  const agents = await getAgentDefinitions();
  const newAgentId = randomUUID();

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Agent Studio</h1>
          <p className="fx-muted">Agents are individual units of execution used by workflows.</p>
        </div>
        <div className="flex items-center gap-3">
          <ImportExportControls kind="agent-definitions" />
          <Link className="fx-btn-primary px-3 py-2 text-sm font-medium" href={`/builder/agents/${newAgentId}`}>
            New Agent
          </Link>
        </div>
      </header>

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Agent</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Version</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2 text-[var(--foreground)]">{agent.name}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{agent.type}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{agent.status}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">v{agent.version}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <div className="flex flex-nowrap items-center justify-end gap-2">
                    <ImportExportControls kind="agent-definitions" id={agent.id} compact />
                    <Link className="fx-btn-primary px-2.5 py-1 text-xs font-medium" href={`/builder/agents/${agent.id}`}>
                      Open
                    </Link>
                    <TypedDeleteButton itemType="agent" itemId={agent.id} itemName={agent.name} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
