"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RunArchiveButton } from "@/components/run-archive-button";
import { TaskKickoffComposer } from "@/components/task-kickoff-composer";
import {
  createInboxGroup,
  deleteInboxGroup,
  getInboxGroups,
  getWorkflowRuns,
  updateInboxGroup,
  type InboxGroup,
} from "@/lib/api";
import type { RunKind, WorkflowRunSummary } from "@/types/frontier";

type GroupBy = "none" | "type" | "status" | "recency";

const KIND_LABEL: Record<RunKind, string> = {
  individual: "Chat",
  agent: "Agent",
  workflow: "Workflow",
  playbook: "Playbook",
};

const KIND_ORDER: RunKind[] = ["individual", "agent", "workflow", "playbook"];

function runKind(run: WorkflowRunSummary): RunKind {
  return run.kind ?? "individual";
}

function kindChipClass(kind: RunKind): string {
  switch (kind) {
    case "agent":
      return "border-[hsl(var(--accent)/0.5)] text-[hsl(var(--accent))]";
    case "workflow":
      return "border-[hsl(var(--state-info,var(--accent))/0.5)] text-[var(--foreground)]";
    case "playbook":
      return "border-[hsl(var(--state-warning)/0.5)] text-[hsl(var(--state-warning))]";
    default:
      return "border-[var(--ui-border)] fx-muted";
  }
}

function statusChipClass(status: string): string {
  if (status === "Done") return "border-[hsl(var(--state-success)/0.5)] text-[hsl(var(--state-success))]";
  if (status === "Failed" || status === "Blocked")
    return "border-[hsl(var(--state-critical)/0.5)] text-[hsl(var(--state-critical))]";
  if (status === "Needs Review") return "border-[hsl(var(--state-warning)/0.5)] text-[hsl(var(--state-warning))]";
  return "border-[var(--ui-border)] fx-muted";
}

function recencyBucket(updatedAt: string): string {
  const value = updatedAt.toLowerCase();
  if (value.includes("now") || /\bm ago\b/.test(value) || value.includes("min")) return "Recent";
  if (value.includes("h ago") || value.includes("hour")) return "Today";
  if (value.includes("d ago") || value.includes("day")) return "This week";
  return "Older";
}

function groupKey(run: WorkflowRunSummary, groupBy: GroupBy): string {
  if (groupBy === "type") return KIND_LABEL[runKind(run)];
  if (groupBy === "status") return run.status;
  if (groupBy === "recency") return recencyBucket(run.updatedAt);
  return "All chats";
}

export function InboxWorkspace() {
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [groups, setGroups] = useState<InboxGroup[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [groupBy, setGroupBy] = useState<GroupBy>("type");
  const [typeFilter, setTypeFilter] = useState<RunKind | null>(null);
  const [newGroupName, setNewGroupName] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [runList, groupList] = await Promise.all([
      getWorkflowRuns(),
      getInboxGroups().catch(() => [] as InboxGroup[]),
    ]);
    setRuns(runList);
    setGroups(groupList);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const activeFolder = groups.find((g) => g.id === selectedFolder) ?? null;

  const visibleRuns = useMemo(() => {
    let list = runs;
    if (activeFolder) {
      const ids = new Set(activeFolder.run_ids);
      list = runs.filter((run) => ids.has(run.id));
    }
    if (typeFilter) {
      list = list.filter((run) => runKind(run) === typeFilter);
    }
    return list;
  }, [runs, activeFolder, typeFilter]);

  const grouped = useMemo(() => {
    const buckets = new Map<string, WorkflowRunSummary[]>();
    for (const run of visibleRuns) {
      const key = groupKey(run, groupBy);
      const bucket = buckets.get(key);
      if (bucket) bucket.push(run);
      else buckets.set(key, [run]);
    }
    return Array.from(buckets.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [visibleRuns, groupBy]);

  async function addFolder() {
    if (!newGroupName.trim()) return;
    setBusy(true);
    try {
      await createInboxGroup(newGroupName.trim());
      setNewGroupName("");
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to create folder.");
    } finally {
      setBusy(false);
    }
  }

  async function removeFolder(group: InboxGroup) {
    setBusy(true);
    try {
      await deleteInboxGroup(group.id);
      if (selectedFolder === group.id) setSelectedFolder(null);
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to delete folder.");
    } finally {
      setBusy(false);
    }
  }

  async function assignToFolder(runId: string, groupId: string) {
    if (!groupId) return;
    try {
      await updateInboxGroup(groupId, { add_run_id: runId });
      await refresh();
      setNotice("Added to folder.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to update folder.");
    }
  }

  async function removeFromFolder(runId: string, groupId: string) {
    try {
      await updateInboxGroup(groupId, { remove_run_id: runId });
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to update folder.");
    }
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Inbox</h1>
        <p className="fx-muted">
          Historical chats across agents, workflows, and playbooks — organize them into folders or
          group them on the fly.
        </p>
      </header>

      <TaskKickoffComposer />

      <div className="grid gap-4 xl:grid-cols-[260px_1fr]">
        <aside className="space-y-3">
          <article className="fx-panel p-3">
            <h2 className="mb-2 text-sm font-semibold">Folders</h2>
            <ul className="space-y-1 text-sm">
              <li>
                <button
                  type="button"
                  onClick={() => setSelectedFolder(null)}
                  className={`w-full rounded border px-2 py-1.5 text-left ${
                    selectedFolder === null
                      ? "border-[hsl(var(--accent)/0.5)] bg-[hsl(var(--accent)/0.1)]"
                      : "border-[var(--fx-border)] bg-[var(--fx-surface-elevated)]"
                  }`}
                >
                  <span className="font-medium text-[var(--foreground)]">All chats</span>
                  <span className="fx-muted block text-xs">{runs.length} chat(s)</span>
                </button>
              </li>
              {groups.map((group) => (
                <li key={group.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setSelectedFolder(group.id)}
                    className={`min-w-0 flex-1 rounded border px-2 py-1.5 text-left ${
                      selectedFolder === group.id
                        ? "border-[hsl(var(--accent)/0.5)] bg-[hsl(var(--accent)/0.1)]"
                        : "border-[var(--fx-border)] bg-[var(--fx-surface-elevated)]"
                    }`}
                  >
                    <span className="block truncate font-medium text-[var(--foreground)]">{group.name}</span>
                    <span className="fx-muted block text-xs">{group.run_ids.length} chat(s)</span>
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${group.name}`}
                    disabled={busy}
                    onClick={() => void removeFolder(group)}
                    className="fx-btn-secondary px-1.5 py-1 text-xs disabled:opacity-60"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-2 flex gap-1">
              <input
                className="fx-field h-8 flex-1 px-2 text-xs"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void addFolder();
                }}
                placeholder="New folder"
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => void addFolder()}
                className="fx-btn-secondary px-2 py-1 text-xs disabled:opacity-60"
              >
                Add
              </button>
            </div>
          </article>

          <article className="fx-panel space-y-2 p-3 text-xs">
            <h2 className="text-sm font-semibold">Group by</h2>
            <select
              className="fx-field h-8 w-full px-2"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
            >
              <option value="type">Type</option>
              <option value="status">Status</option>
              <option value="recency">Recency</option>
              <option value="none">None</option>
            </select>
          </article>
        </aside>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setTypeFilter(null)}
              className={`rounded-full border px-2.5 py-0.5 text-xs ${
                typeFilter === null
                  ? "border-[hsl(var(--accent)/0.6)] bg-[hsl(var(--accent)/0.1)] text-[var(--foreground)]"
                  : "border-[var(--ui-border)] fx-muted"
              }`}
            >
              All types
            </button>
            {KIND_ORDER.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => setTypeFilter((current) => (current === kind ? null : kind))}
                className={`rounded-full border px-2.5 py-0.5 text-xs ${
                  typeFilter === kind
                    ? "border-[hsl(var(--accent)/0.6)] bg-[hsl(var(--accent)/0.1)] text-[var(--foreground)]"
                    : "border-[var(--ui-border)] fx-muted"
                }`}
              >
                {KIND_LABEL[kind]}
              </button>
            ))}
          </div>

          {visibleRuns.length === 0 ? (
            <div className="fx-panel p-6 text-center text-sm fx-muted">
              {activeFolder
                ? "This folder has no chats yet — add some from All chats."
                : "No chats yet."}
            </div>
          ) : (
            grouped.map(([key, bucket]) => (
              <div key={key} className="space-y-1.5">
                {groupBy !== "none" ? (
                  <h3 className="fx-muted px-1 text-xs font-semibold uppercase tracking-wide">
                    {key} · {bucket.length}
                  </h3>
                ) : null}
                <div className="fx-panel divide-y divide-[var(--fx-border)]">
                  {bucket.map((run) => {
                    const kind = runKind(run);
                    return (
                      <div key={run.id} className="flex flex-wrap items-center gap-2 p-2.5">
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-[var(--foreground)]">{run.title}</p>
                          <p className="fx-muted truncate text-xs">{run.progressLabel}</p>
                        </div>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${kindChipClass(kind)}`}>
                          {KIND_LABEL[kind]}
                        </span>
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] ${statusChipClass(run.status)}`}>
                          {run.status}
                        </span>
                        <span className="fx-muted text-[11px]">{run.updatedAt}</span>
                        {activeFolder ? (
                          <button
                            type="button"
                            onClick={() => void removeFromFolder(run.id, activeFolder.id)}
                            className="fx-btn-secondary px-2 py-1 text-[11px]"
                          >
                            Remove
                          </button>
                        ) : groups.length > 0 ? (
                          <select
                            className="fx-field h-7 px-1 text-[11px]"
                            value=""
                            onChange={(e) => void assignToFolder(run.id, e.target.value)}
                          >
                            <option value="">Add to…</option>
                            {groups.map((group) => (
                              <option key={group.id} value={group.id}>
                                {group.name}
                              </option>
                            ))}
                          </select>
                        ) : null}
                        <Link className="fx-btn-primary px-2.5 py-1 text-xs font-medium" href={`/runs/${run.id}`}>
                          Open
                        </Link>
                        <RunArchiveButton runId={run.id} />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {notice ? <p className="fx-muted text-xs">{notice}</p> : null}
    </section>
  );
}
