"use client";

import Link from "next/link";
import { type ChangeEvent, useEffect, useMemo, useState } from "react";
import { StatusChip } from "@/components/status-chip";
import { getInbox, getWorkflowRuns } from "@/lib/api";
import type { InboxItem, PlatformVersionStatus, WorkflowRunSummary } from "@/types/frontier";

type UserConsoleSidebarProps = {
  pathname: string;
  selectedSessionId: string | null;
  expanded: boolean;
  platformVersion?: PlatformVersionStatus | null;
};

type SessionRow = WorkflowRunSummary & {
  inboxCount: number;
  inboxReasons: string[];
};

function sessionHref(runId: string): string {
  return `/inbox?session=${encodeURIComponent(runId)}`;
}

function formatSessionSearchText(run: SessionRow): string {
  return [run.title, run.status, run.progressLabel, ...run.inboxReasons].join(" ").toLowerCase();
}

export function UserConsoleSidebar({ pathname, selectedSessionId, expanded, platformVersion }: UserConsoleSidebarProps) {
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;

    void Promise.all([getWorkflowRuns(), getInbox()])
      .then(([nextRuns, nextInbox]) => {
        if (cancelled) {
          return;
        }
        setRuns(nextRuns);
        setInboxItems(nextInbox);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setRuns([]);
        setInboxItems([]);
      });

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const sessions = useMemo<SessionRow[]>(() => {
    const inboxByRun = new Map<string, InboxItem[]>();
    for (const item of inboxItems) {
      const current = inboxByRun.get(item.runId) ?? [];
      current.push(item);
      inboxByRun.set(item.runId, current);
    }

    return runs.map((run: WorkflowRunSummary) => {
      const relatedInbox = inboxByRun.get(run.id) ?? [];
      return {
        ...run,
        inboxCount: relatedInbox.length,
        inboxReasons: relatedInbox.map((item: InboxItem) => item.reason),
      };
    });
  }, [inboxItems, runs]);

  const filteredSessions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return sessions;
    }
    return sessions.filter((run: SessionRow) => formatSessionSearchText(run).includes(query));
  }, [search, sessions]);

  const versionLabel = platformVersion?.current_version ? `v${platformVersion.current_version}` : "No version";
  const updateLabel = platformVersion?.status === "update_available" && platformVersion.latest_version
    ? `Update ${platformVersion.latest_version}`
    : platformVersion?.status === "up_to_date"
      ? "Current"
      : "Unchecked";

  if (!expanded) {
    return null;
  }

  return (
    <div className="flex h-full flex-col bg-[radial-gradient(circle_at_top,hsl(var(--muted)/0.8),transparent_32%)]">
      <div className="border-b border-[var(--ui-border)] px-3 pb-3 pt-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Workspace</p>
        <h2 className="mt-2 text-[1rem] font-semibold text-[hsl(var(--foreground))]">Conversations</h2>
        <p className="mt-1 text-[0.78rem] leading-5 text-[var(--fx-muted)]">Workflows and artifacts stay one click away while live sessions remain searchable.</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Link href="/workflows/start" className={pathname.startsWith("/workflows") ? "fx-nav-item fx-nav-item-active justify-center" : "fx-nav-item justify-center"}>
            Workflows
          </Link>
          <Link href="/artifacts" className={pathname.startsWith("/artifacts") ? "fx-nav-item fx-nav-item-active justify-center" : "fx-nav-item justify-center"}>
            Artifacts
          </Link>
        </div>
      </div>

      <div className="border-b border-[var(--ui-border)] px-3 py-3">
        <label htmlFor="session-search" className="sr-only">
          Search sessions
        </label>
        <div className="rounded-[1.15rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
          <div className="flex items-center gap-2">
            <span className="text-[0.82rem] text-[var(--fx-muted)]">/</span>
            <input
              id="session-search"
              type="search"
              value={search}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
              placeholder="Search sessions"
              className="w-full bg-transparent text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--fx-muted)]"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        <div className="mb-3 flex items-center justify-between px-2">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-[var(--fx-muted)]">Sessions</p>
          <span className="text-[0.72rem] text-[var(--fx-muted)]">{filteredSessions.length}</span>
        </div>

        <div className="space-y-1.5">
          {filteredSessions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--ui-border)] px-3 py-4 text-[0.78rem] text-[var(--fx-muted)]">
              No sessions match this search.
            </div>
          ) : (
            filteredSessions.map((run: SessionRow) => {
              const active = pathname.startsWith("/inbox") && selectedSessionId === run.id;
              return (
                <Link
                  key={run.id}
                  href={sessionHref(run.id)}
                  className={active ? "block rounded-[1.1rem] border border-[var(--fx-nav-active-border)] bg-[var(--fx-nav-active)] px-3 py-3" : "block rounded-[1.1rem] border border-transparent px-3 py-3 transition hover:border-[var(--fx-sidebar-divider)] hover:bg-[var(--fx-nav-hover)]"}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-2 text-[0.88rem] font-medium leading-5 text-[hsl(var(--foreground))]">{run.title}</p>
                    {run.inboxCount > 0 ? (
                      <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-0.5 text-[0.65rem] font-semibold text-[var(--foreground)]">
                        {run.inboxCount}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <StatusChip status={run.status} />
                    <span className="text-[0.72rem] text-[var(--fx-muted)]">{run.updatedAt}</span>
                  </div>
                  <p className="mt-2 text-[0.74rem] text-[var(--fx-muted)]">{run.progressLabel}</p>
                  {run.inboxReasons[0] ? (
                    <p className="mt-2 line-clamp-2 text-[0.72rem] leading-5 text-[var(--fx-muted)]">{run.inboxReasons[0]}</p>
                  ) : null}
                </Link>
              );
            })
          )}
        </div>
      </div>

      <div className="border-t border-[var(--ui-border)] px-3 py-3">
        <div className="flex items-center justify-between gap-2 text-[0.72rem] text-[var(--fx-muted)]">
          <span>{versionLabel}</span>
          <span>{updateLabel}</span>
        </div>
        <Link href="/settings" className="mt-3 inline-flex text-[0.78rem] font-medium text-[var(--fx-primary-strong)] no-underline hover:underline">
          Preferences
        </Link>
      </div>
    </div>
  );
}
