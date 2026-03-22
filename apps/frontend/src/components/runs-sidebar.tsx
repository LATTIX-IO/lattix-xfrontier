import Link from "next/link";
import { getWorkflowRuns } from "@/lib/api";
import { StatusChip } from "@/components/status-chip";

export async function RunsSidebar() {
  const runs = await getWorkflowRuns();

  return (
    <aside className="hidden min-w-80 max-w-80 border-r border-[var(--fx-border)] bg-[var(--fx-sidebar)] p-4 xl:block">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-[var(--foreground)]">Runs</h2>
        <span className="fx-muted text-xs">Codex-style history</span>
      </div>
      <div className="space-y-2">
        {runs.map((run) => (
          <Link
            key={run.id}
            href={`/runs/${run.id}`}
            className="fx-panel block p-3 transition hover:bg-[var(--fx-nav-hover)]"
          >
            <p className="truncate text-sm font-medium text-[var(--foreground)]">{run.title}</p>
            <div className="mt-2 flex items-center justify-between gap-2">
              <StatusChip status={run.status} />
              <span className="fx-muted text-xs">{run.progressLabel}</span>
            </div>
            <p className="fx-muted mt-1 text-xs">Updated {run.updatedAt}</p>
          </Link>
        ))}
      </div>
    </aside>
  );
}
