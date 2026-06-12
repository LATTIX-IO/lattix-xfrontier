"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
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
  folderId?: string;
};

export function InboxChatTree() {
  const router = useRouter();
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [groups, setGroups] = useState<InboxGroup[]>([]);
  const [groupBy, setGroupBy] = useState<GroupBy>("type");
  const [typeFilter, setTypeFilter] = useState<RunKind | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  // Group sections (Type/Status/Recency buckets) default open; track collapse.
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [newGroupName, setNewGroupName] = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [menu, setMenu] = useState<ContextMenuState | null>(null);
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);

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
        /* tree degrades to empty */
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

  function toggleGroup(key: string) {
    setCollapsedGroups((prev) => {
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
    await createInboxGroup(newGroupName.trim()).catch(() => null);
    setNewGroupName("");
    setShowNewFolder(false);
    await refresh();
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
    // Expand the target folder so the moved chat is visible immediately.
    setExpanded((prev) => new Set(prev).add(`folder:${groupId}`));
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
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData("application/x-run-id", run.id);
          e.dataTransfer.effectAllowed = "move";
        }}
        onClick={() => router.push(`/runs/${run.id}`)}
        onContextMenu={(e) => openMenu(e, { kind: "chat", id: run.id, folderId })}
        className="group flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left text-[11px] hover:bg-[var(--fx-nav-hover)]"
        title={`${run.title}\n(drag onto a folder, or right-click)`}
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
    <section className="fx-nav-section mb-0">
      <div className="flex items-center justify-between px-1.5 pb-1">
        <h3 className="fx-nav-section-title mb-0 pb-0">Chats</h3>
        <div className="flex items-center gap-1">
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as GroupBy)}
            title="Group by"
            className="fx-field h-5 rounded px-1 text-[10px]"
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

      <div className="flex flex-wrap gap-1 px-1.5 pb-1">
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
        <div className="flex gap-1 px-1.5 pb-1">
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

      <div className="space-y-0.5">
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
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = "move";
                  if (dragOverFolder !== group.id) setDragOverFolder(group.id);
                }}
                onDragLeave={() => setDragOverFolder((c) => (c === group.id ? null : c))}
                onDrop={(e) => {
                  e.preventDefault();
                  const runId = e.dataTransfer.getData("application/x-run-id");
                  setDragOverFolder(null);
                  if (runId) void assignToFolder(runId, group.id);
                }}
                className={`flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-[12px] hover:bg-[var(--fx-nav-hover)] ${
                  dragOverFolder === group.id ? "bg-[hsl(var(--accent)/0.16)] ring-1 ring-[hsl(var(--accent)/0.5)]" : ""
                }`}
              >
                <span className={`fx-muted text-[9px] transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
                <FolderIcon />
                <span className="min-w-0 flex-1 truncate text-[var(--foreground)]">{group.name}</span>
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

        <div className={groups.length > 0 ? "mt-1 border-t border-[var(--fx-border)] pt-1" : ""}>
          {grouped.map(([key, bucket]) => {
            const open = groupBy === "none" ? true : !collapsedGroups.has(key);
            return (
              <div key={key}>
                {groupBy !== "none" ? (
                  <button
                    type="button"
                    onClick={() => toggleGroup(key)}
                    className="flex w-full items-center gap-1 rounded px-1.5 py-1 text-left hover:bg-[var(--fx-nav-hover)]"
                  >
                    <span className={`fx-muted text-[9px] transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
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
      </div>

      {menu ? (
        <div
          className="fx-panel fixed z-50 min-w-[160px] overflow-hidden p-1 text-[12px] shadow-[0_10px_30px_rgba(0,0,0,0.5)]"
          style={{ left: Math.min(menu.x, (typeof window !== "undefined" ? window.innerWidth : 9999) - 180), top: menu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          {menu.kind === "chat"
            ? (() => {
                const run = runsById.get(menu.id);
                if (!run) return null;
                return (
                  <>
                    <MenuItem label="Open" onClick={() => { setMenu(null); router.push(`/runs/${run.id}`); }} />
                    <MenuItem label="Rename chat" onClick={() => { setMenu(null); void renameChat(run); }} />
                    <MenuItem
                      label="Copy chat ID"
                      onClick={() => { setMenu(null); void navigator.clipboard?.writeText(run.id).catch(() => null); }}
                    />
                    {menu.folderId ? (
                      <MenuItem
                        label="Remove from folder"
                        onClick={() => { setMenu(null); void removeFromFolder(run.id, menu.folderId as string); }}
                      />
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
                        onClick={() => { setMenu(null); void assignToFolder(run.id, group.id); }}
                      />
                    ))}
                    <div className="my-1 border-t border-[var(--fx-border)]" />
                    <MenuItem label="Archive" danger onClick={() => { setMenu(null); void archiveChat(run.id); }} />
                  </>
                );
              })()
            : (() => {
                const group = groups.find((g) => g.id === menu.id);
                if (!group) return null;
                return (
                  <>
                    <MenuItem label="Rename folder" onClick={() => { setMenu(null); void renameFolder(group); }} />
                    <MenuItem label="Delete folder" danger onClick={() => { setMenu(null); void removeFolder(group); }} />
                  </>
                );
              })()}
        </div>
      ) : null}
    </section>
  );
}

function FolderIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-3 w-3 shrink-0 text-[var(--fx-muted)]"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden="true"
    >
      <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2h7A1.5 1.5 0 0 1 19 8.5v8A1.5 1.5 0 0 1 17.5 18h-13A1.5 1.5 0 0 1 3 16.5z" />
    </svg>
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
