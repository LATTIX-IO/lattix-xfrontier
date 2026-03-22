import Link from "next/link";
import { TypedDeleteButton } from "@/components/typed-delete-button";
import { WorkflowStatusButton } from "@/components/workflow-status-button";
import { getWorkflowDefinitions } from "@/lib/api";

export default async function BuilderWorkflowsPage() {
  const workflows = await getWorkflowDefinitions();

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Workflow Studio</h1>
        <p className="fx-muted">Workflows are tasks for one or more agents to execute end-to-end.</p>
      </header>

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Workflow</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Version</th>
              <th className="px-3 py-2 text-left">Description</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((workflow) => (
              <tr key={workflow.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2 text-[var(--foreground)]">{workflow.name}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{workflow.status}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">v{workflow.version}</td>
                <td className="fx-muted px-3 py-2">{workflow.description}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <Link className="fx-btn-primary px-2.5 py-1 text-xs font-medium" href={`/builder/workflow/${workflow.id}`}>
                      Open
                    </Link>
                    <WorkflowStatusButton workflowId={workflow.id} status={workflow.status} />
                    <TypedDeleteButton itemType="workflow" itemId={workflow.id} itemName={workflow.name} />
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
