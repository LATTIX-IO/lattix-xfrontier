import Link from "next/link";
import { notFound } from "next/navigation";
import { getPublishedWorkflows } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function WorkflowDetailPage({ params }: Props) {
  const { id } = await params;
  const workflows = await getPublishedWorkflows();
  const workflow = workflows.find((item) => item.id === id);

  if (!workflow) {
    notFound();
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Workflow Details</h1>
        <p className="fx-muted">Stable workflow reference by UUID.</p>
      </header>

      <div className="fx-panel space-y-3 p-4">
        <p className="text-lg font-semibold text-[var(--foreground)]">{workflow.name}</p>
        <p className="fx-muted">{workflow.description}</p>
        <p className="text-sm text-[var(--foreground)]">Status: {workflow.status} • v{workflow.version}</p>
        <p className="font-mono text-xs text-[var(--foreground)]">workflow_id: {workflow.id}</p>
        <div className="flex gap-2">
          <Link className="fx-btn-secondary px-3 py-2 text-sm" href="/workflows/start">
            Back to catalog
          </Link>
        </div>
      </div>
    </section>
  );
}
