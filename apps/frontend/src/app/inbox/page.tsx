import Link from "next/link";
import { RunArchiveButton } from "@/components/run-archive-button";
import { TaskKickoffComposer } from "@/components/task-kickoff-composer";
import { getInbox, getWorkflowRuns } from "@/lib/api";

function getQueueTags(queue: "Needs Review" | "Needs Approval" | "Clarifications Requested" | "Blocked by Guardrails"): string[] {
  if (queue === "Needs Review") return ["#flag", "#need-review"];
  if (queue === "Needs Approval") return ["#flag", "#need-review", "#approval"];
  if (queue === "Clarifications Requested") return ["#flag", "#need-review", "#clarifications"];
  return ["#flag", "#blocked"];
}

function tagStyle(tag: string): string {
  if (tag.includes("blocked")) {
    return "border border-[var(--fx-danger)] bg-[color-mix(in_srgb,var(--fx-danger)_20%,transparent)]";
  }
  if (tag.includes("approval") || tag.includes("clarification") || tag.includes("need-review")) {
    return "border border-[var(--fx-warning)] bg-[color-mix(in_srgb,var(--fx-warning)_20%,transparent)]";
  }
  if (tag.includes("complete")) {
    return "border border-[var(--fx-success)] bg-[color-mix(in_srgb,var(--fx-success)_20%,transparent)]";
  }
  return "border border-[var(--fx-primary)] bg-[color-mix(in_srgb,var(--fx-primary)_20%,transparent)]";
}

export default async function InboxPage() {
  const [items, runs] = await Promise.all([getInbox(), getWorkflowRuns()]);
  const queuedRunIds = new Set(items.map((item) => item.runId));
  const activeRunRows = runs
    .filter((run) => run.status !== "Done" && run.status !== "Failed" && !queuedRunIds.has(run.id))
    .map((run) => ({
      id: `run-${run.id}`,
      runId: run.id,
      runName: run.title,
      artifactType: "Task",
      reason: run.progressLabel || "Task in progress",
      queue: "Needs Review" as const,
    }));

  const inProcessItems = [...items, ...activeRunRows];
  const completeRuns = runs.filter((run) => run.status === "Done");

  return (
    <section className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Inbox</h1>
        <p className="fx-muted">Human-on-the-loop queue for review, approvals, and clarifications.</p>
      </header>

      <TaskKickoffComposer />

      <div className="space-y-2">
        <h2 className="fx-muted text-sm font-semibold uppercase tracking-wide">In Process</h2>
        <div className="fx-panel overflow-hidden">
          <table className="w-full text-sm">
            <thead className="fx-table-head">
              <tr>
                <th className="px-3 py-2 text-left">Run</th>
                <th className="px-3 py-2 text-left">Artifact</th>
                <th className="px-3 py-2 text-left">Reason</th>
                <th className="px-3 py-2 text-left">Ticktack tags</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {inProcessItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="fx-muted px-3 py-3">
                    No items.
                  </td>
                </tr>
              ) : (
                inProcessItems.map((item) => (
                  <tr key={item.id} className="border-t border-[var(--fx-border)]">
                    <td className="px-3 py-2 text-[var(--foreground)]">{item.runName}</td>
                    <td className="px-3 py-2 text-[var(--foreground)]">{item.artifactType}</td>
                    <td className="fx-muted px-3 py-2">{item.reason}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1.5">
                        {getQueueTags(item.queue).map((tag) => (
                          <span key={`${item.id}-${tag}`} className={`px-2 py-0.5 text-xs font-mono text-[var(--foreground)] ${tagStyle(tag)}`}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Link className="fx-btn-primary px-2.5 py-1 text-xs font-medium" href={`/runs/${item.runId}`}>
                          Open
                        </Link>
                        <RunArchiveButton runId={item.runId} />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="fx-muted text-sm font-semibold uppercase tracking-wide">Complete</h2>
        <div className="fx-panel overflow-hidden">
          <table className="w-full text-sm">
            <thead className="fx-table-head">
              <tr>
                <th className="px-3 py-2 text-left">Run</th>
                <th className="px-3 py-2 text-left">Progress</th>
                <th className="px-3 py-2 text-left">Ticktack tags</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {completeRuns.length === 0 ? (
                <tr>
                  <td colSpan={4} className="fx-muted px-3 py-3">
                    No completed runs yet.
                  </td>
                </tr>
              ) : (
                completeRuns.map((run) => (
                  <tr key={run.id} className="border-t border-[var(--fx-border)]">
                    <td className="px-3 py-2 text-[var(--foreground)]">{run.title}</td>
                    <td className="fx-muted px-3 py-2">{run.progressLabel}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 text-xs font-mono text-[var(--foreground)] ${tagStyle("#complete")}`}>
                        #complete
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <Link className="fx-btn-secondary px-2.5 py-1 text-xs font-medium" href={`/runs/${run.id}`}>
                          View
                        </Link>
                        <RunArchiveButton runId={run.id} />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
