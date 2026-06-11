"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { TaskKickoffComposer } from "@/components/task-kickoff-composer";
import {
  archiveWorkflowRun,
  createInboxGroup,
  deleteInboxGroup,
  getInboxGroups,
  getWorkflowRuns,
  renameWorkflowRun,
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

function statusDotColor(status: string): string {
  if (status === "Done") return "hsl(var(--state-success))";
  if (status === "Failed" || status === "Blocked") return "hsl(var(--state-critical))";
  if (status === "Needs Review") return "hsl(var(--state-warning))";
  if (status === "Running") return "hsl(var(--accent))";
  return "var(--fx-muted)";
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
  return "All";
}

type ContextMenuState = {
  x: number;
  y: number;
  kind: "chat" | "folder";
  id: string;
  folderId?: string; // when a chat is shown inside a folder
};

export function InboxWorkspace() {
  const router = useRouter();
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [groups, setGroups] = useState<InboxGroup[]>([]);
  const [groupBy, setGroupBy] = useState<GroupBy>("type");
  const [typeFilter, setTypeFilter] = useState<RunKind | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["__all__"]));
  const [newGroupName, setNewGroupName] = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [runList, groupList] = await Promise.all([
      getWorkflowRuns(),
      getInboxGroups().catch(() => [] as InboxGroup[]),
    ]);
    setRuns(runList);
    setGroups(groupList);
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [runList, groupList] = await Promise.all([
          getWorkflowRuns(),
          getInboxGroups().catch(() => [] as InboxGroup[]),
        ]);
        if (active) {
          setRuns(runList);
          setGroups(groupList);
        }
      } catch {
        /* surfaced via empty state */
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [menu]);

  const runsById = useMemo(() => {
    const map = new Map<string, WorkflowRunSummary>();
    runs.forEach((run) => map.set(run.id, run));
    return map;
  }, [runs]);

  const filtered = useMemo(
    () => (typeFilter ? runs.filter((run) => runKind(run) === typeFilter) : runs),
    [runs, typeFilter],
  );

  const grouped = useMemo(() => {
    const buckets = new Map<string, WorkflowRunSummary[]>();
    for (const run of filtered) {
      const key = groupKey(run, groupBy);
      const bucket = buckets.get(key);
      if (bucket) bucket.push(run);
      else buckets.set(key, [run]);
    }
    return Array.from(buckets.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered, groupBy]);

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function openMenu(event: React.MouseEvent, state: Omit<ContextMenuState, "x" | "y">) {
    event.preventDefault();
    event.stopPropagation();
    setMenu({ ...state, x: event.clientX, y: event.clientY });
  }

  async function addFolder() {
    if (!newGroupName.trim()) return;
    try {
      await createInboxGroup(newGroupName.trim());
      setNewGroupName("");
      setShowNewFolder(false);
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to create folder.");
    }
  }

  async function renameFolder(group: InboxGroup) {
    const name = window.prompt("Rename folder", group.name);
    if (!name || !name.trim()) return;
    await updateInboxGroup(group.id, { name: name.trim() }).catch(() => null);
    await refresh();
  }

  async function removeFolder(group: InboxGroup) {
    await deleteInboxGroup(group.id).catch(() => null);
    await refresh();
  }

  async function renameChat(run: WorkflowRunSummary) {
    const title = window.prompt("Rename chat", run.title);
    if (!title || !title.trim()) return;
    await renameWorkflowRun(run.id, title.trim()).catch(() => null);
    await refresh();
  }

  async function archiveChat(runId: string) {
    await archiveWorkflowRun(runId).catch(() => null);
    await refresh();
  }

  async function assignToFolder(runId: string, groupId: string) {
    await updateInboxGroup(groupId, { add_run_id: runId }).catch(() => null);
    await refresh();
  }

  async function removeFromFolder(runId: string, groupId: string) {
    await updateInboxGroup(groupId, { remove_run_id: runId }).catch(() => null);
    await refresh();
  }

  function ChatRow({ run, folderId }: { run: WorkflowRunSummary; folderId?: string }) {
    return (
      <button
        type="button"
        onClick={() => router.push(`/runs/${run.id}`)}
        onContextMenu={(e) => openMenu(e, { kind: "chat", id: run.id, folderId })}
        className="group flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-[11px] hover:bg-[var(--fx-nav-hover)]"
        title={run.title}
      >
        <span
          aria-hidden
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${run.status === "Running" ? "animate-pulse" : ""}`}
          style={{ background: statusDotColor(run.status) }}
        />
        <span className="min-w-0 flex-1 truncate text-[var(--foreground)]">{run.title}</span>
        <span className="fx-muted shrink-0 text-[10px] opacity-70">{run.updatedAt}</span>
      </button>
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Inbox</h1>
        <p className="fx-muted text-sm">
          Historical chats across agents, workflows, and playbooks — right-click a chat or folder to edit.
        </p>
      </header>

      <div className="grid gap-4 xl:grid-cols-[248px_1fr]">
        {/* T3-style chat rail */}
        <aside className="fx-panel flex flex-col gap-1 p-2 text-[12px]">
          <div className="flex items-center justify-between px-1.5 py-1">
            <span className="fx-muted text-[10px] font-semibold uppercase tracking-[0.12em]">Chats</span>
            <div className="flex items-center gap-1">
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value as GroupBy)}
                title="Group by"
                className="fx-field h-6 rounded px-1 text-[10px]"
              >
                <option value="type">Type</option>
                <option value="status">Status</option>
                <option value="recency">Recency</option>
                <option value="none">None</option>
              </select>
              <button
                type="button"
                aria-label="New folder"
                title="New folder"
                onClick={() => setShowNewFolder((v) => !v)}
                className="fx-btn-secondary rounded px-1.5 py-0.5 text-[11px] leading-none"
              >
                +
              </button>
            </div>
          </div>

          {/* type quick-filters */}
          <div className="flex flex-wrap gap-1 px-1 pb-1">
            <button
              type="button"
              onClick={() => setTypeFilter(null)}
              className={`rounded-full border px-1.5 py-0.5 text-[9px] uppercase ${typeFilter === null ? "border-[hsl(var(--accent)/0.6)] text-[var(--foreground)]" : "border-[var(--ui-border)] fx-muted"}`}
            >
              All
            </button>
            {KIND_ORDER.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => setTypeFilter((c) => (c === kind ? null : kind))}
                className={`rounded-full border px-1.5 py-0.5 text-[9px] uppercase ${typeFilter === kind ? "border-[hsl(var(--accent)/0.6)] text-[var(--foreground)]" : "border-[var(--ui-border)] fx-muted"}`}
              >
                {KIND_LABEL[kind]}
              </button>
            ))}
          </div>

          {showNewFolder ? (
            <div className="flex gap-1 px-1 pb-1">
              <input
                autoFocus
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void addFolder();
                  if (e.key === "Escape") setShowNewFolder(false);
                }}
                placeholder="Folder name"
                className="fx-field h-6 flex-1 px-1.5 text-[11px]"
              />
              <button type="button" onClick={() => void addFolder()} className="fx-btn-secondary rounded px-1.5 text-[10px]">
                Add
              </button>
            </div>
          ) : null}

          {/* Folders */}
          {groups.map((group) => {
            const key = `folder:${group.id}`;
            const open = expanded.has(key);
            const folderRuns = group.run_ids
              .map((id) => runsById.get(id))
              .filter((r): r is WorkflowRunSummary => Boolean(r))
              .filter((r) => !typeFilter || runKind(r) === typeFilter);
            return (
              <div key={group.id}>
                <button
                  type="button"
                  onClick={() => toggle(key)}
                  onContextMenu={(e) => openMenu(e, { kind: "folder", id: group.id })}
                  className="flex w-full items-center gap-1 rounded px-1.5 py-1 text-left hover:bg-[var(--fx-nav-hover)]"
                >
                  <span className={`fx-muted transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
                  <span className="min-w-0 flex-1 truncate text-[var(--foreground)]">📁 {group.name}</span>
                  <span className="fx-muted text-[10px]">{folderRuns.length}</span>
                </button>
                {open ? (
                  <div className="ml-3 border-l border-[var(--fx-border)] pl-1.5">
                    {folderRuns.length === 0 ? (
                      <p className="fx-muted px-1.5 py-1 text-[10px]">Empty — right-click a chat to add.</p>
                    ) : (
                      folderRuns.map((run) => <ChatRow key={run.id} run={run} folderId={group.id} />)
                    )}
                  </div>
                ) : null}
              </div>
            );
          })}

          {/* All chats (grouped) */}
          <div className="mt-1 border-t border-[var(--fx-border)] pt-1">
            {grouped.map(([key, bucket]) => {
              const expandKey = `all:${key}`;
              const open = groupBy === "none" ? true : expanded.has(expandKey) || expanded.has("__all__");
              return (
                <div key={key}>
                  {groupBy !== "none" ? (
                    <button
                      type="button"
                      onClick={() => toggle(expandKey)}
                      className="flex w-full items-center gap-1 rounded px-1.5 py-1 text-left hover:bg-[var(--fx-nav-hover)]"
                    >
                      <span className={`fx-muted transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
                      <span className="min-w-0 flex-1 truncate fx-muted text-[10px] font-semibold uppercase tracking-wide">
                        {key}
                      </span>
                      <span className="fx-muted text-[10px]">{bucket.length}</span>
                    </button>
                  ) : null}
                  {open ? (
                    <div className={groupBy !== "none" ? "ml-3 border-l border-[var(--fx-border)] pl-1.5" : ""}>
                      {bucket.map((run) => (
                        <ChatRow key={run.id} run={run} />
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
            {runs.length === 0 ? <p className="fx-muted px-1.5 py-2 text-[11px]">No chats yet.</p> : null}
          </div>
        </aside>

        {/* Main: composer */}
        <div className="space-y-4">
          <TaskKickoffComposer />
          {notice ? <p className="fx-muted text-xs">{notice}</p> : null}
          <p className="fx-muted text-xs">
            Select a chat from the rail to open it, or kick off a new task above. Right-click any chat
            or folder for edit actions.
          </p>
        </div>
      </div>

      {/* Right-click context menu */}
      {menu ? (
        <div
          className="fx-panel fixed z-50 min-w-[160px] overflow-hidden p-1 text-[12px] shadow-[0_10px_30px_rgba(0,0,0,0.5)]"
          style={{ left: Math.min(menu.x, (typeof window !== "undefined" ? window.innerWidth : 9999) - 180), top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {menu.kind === "chat" ? (
            (() => {
              const run = runsById.get(menu.id);
              if (!run) return null;
              return (
                <>
                  <MenuItem label="Open" onClick={() => router.push(`/runs/${run.id}`)} />
                  <MenuItem label="Rename chat" onClick={() => void renameChat(run)} />
                  <MenuItem
                    label="Copy chat ID"
                    onClick={() => void navigator.clipboard?.writeText(run.id).catch(() => null)}
                  />
                  {menu.folderId ? (
                    <MenuItem label="Remove from folder" onClick={() => void removeFromFolder(run.id, menu.folderId as string)} />
                  ) : null}
                  {groups.length > 0 ? (
                    <div className="border-t border-[var(--fx-border)] px-2 py-1 text-[10px] uppercase tracking-wide fx-muted">
                      Add to folder
                    </div>
                  ) : null}
                  {groups.map((group) => (
                    <MenuItem
                      key={group.id}
                      label={group.name}
                      indent
                      onClick={() => void assignToFolder(run.id, group.id)}
                    />
                  ))}
                  <div className="my-1 border-t border-[var(--fx-border)]" />
                  <MenuItem label="Archive" danger onClick={() => void archiveChat(run.id)} />
                </>
              );
            })()
          ) : (
            (() => {
              const group = groups.find((g) => g.id === menu.id);
              if (!group) return null;
              return (
                <>
                  <MenuItem label="Rename folder" onClick={() => void renameFolder(group)} />
                  <MenuItem label="Delete folder" danger onClick={() => void removeFolder(group)} />
                </>
              );
            })()
          )}
        </div>
      ) : null}
    </section>
  );
}

function MenuItem({
  label,
  onClick,
  danger,
  indent,
}: {
  label: string;
  onClick: () => void;
  danger?: boolean;
  indent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`block w-full truncate rounded px-2 py-1 text-left hover:bg-[var(--fx-nav-hover)] ${
        danger ? "text-[hsl(var(--state-critical))]" : "text-[var(--foreground)]"
      } ${indent ? "pl-4" : ""}`}
    >
      {label}
    </button>
  );
}
