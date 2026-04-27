"use client";

import Link from "next/link";
import { type ChangeEvent, useEffect, useMemo, useState } from "react";
import { FX_STATUS, statusFromRunStatus } from "@/components/fx-ui";
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

const NAV_GROUPS: ReadonlyArray<{
  title: string;
  items: ReadonlyArray<{ href: string; label: string; icon: NavIconName; expandable?: boolean }>;
}> = [
  {
    title: "Work",
    items: [
      { href: "/home", label: "Command Center", icon: "home" },
      { href: "/workflows/start", label: "Workflows", icon: "workflow" },
      { href: "/playbooks", label: "Playbooks", icon: "playbooks" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/memory", label: "Memory", icon: "memory" },
      { href: "/inbox", label: "Tasks", icon: "tasks", expandable: true },
    ],
  },
];

type NavIconName = "home" | "workflow" | "playbooks" | "memory" | "tasks" | "settings";

function NavIcon({ name, active }: { name: NavIconName; active: boolean }) {
  const cls = `h-4 w-4 flex-shrink-0 ${active ? "text-[var(--fx-primary-strong)]" : "text-[var(--fx-muted)]"}`;
  if (name === "home") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="11" width="18" height="10" rx="1" />
        <path d="M3 11L12 3l9 8" />
      </svg>
    );
  }
  if (name === "workflow") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="5" cy="12" r="2" />
        <circle cx="12" cy="6" r="2" />
        <circle cx="19" cy="12" r="2" />
        <circle cx="12" cy="18" r="2" />
        <path d="M7 11l3-3M14 8l3 3M14 16l3-3M10 16l-3-3" />
      </svg>
    );
  }
  if (name === "playbooks") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="4" y="3" width="16" height="5" rx="1" />
        <rect x="4" y="10" width="16" height="5" rx="1" />
        <rect x="4" y="17" width="10" height="4" rx="1" />
      </svg>
    );
  }
  if (name === "memory") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <ellipse cx="12" cy="6" rx="8" ry="3" />
        <path d="M4 6v4c0 1.66 3.58 3 8 3s8-1.34 8-3V6M4 10v4c0 1.66 3.58 3 8 3s8-1.34 8-3v-4" />
      </svg>
    );
  }
  if (name === "tasks") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 4h16v11H4z" />
        <path d="M4 15h5l2 3h2l2-3h5" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/home") return pathname === "/home";
  if (href === "/inbox") return pathname.startsWith("/inbox");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function UserConsoleSidebar({ pathname, selectedSessionId, expanded, platformVersion }: UserConsoleSidebarProps) {
  const [runs, setRuns] = useState<WorkflowRunSummary[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [search, setSearch] = useState("");
  const [tasksOpen, setTasksOpen] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([getWorkflowRuns(), getInbox()])
      .then(([nextRuns, nextInbox]) => {
        if (cancelled) return;
        setRuns(nextRuns);
        setInboxItems(nextInbox);
      })
      .catch(() => {
        if (cancelled) return;
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
    return runs.map((run) => {
      const related = inboxByRun.get(run.id) ?? [];
      return {
        ...run,
        inboxCount: related.length,
        inboxReasons: related.map((i) => i.reason),
      };
    });
  }, [inboxItems, runs]);

  const filteredSessions = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return sessions;
    return sessions.filter((s) => formatSessionSearchText(s).includes(query));
  }, [search, sessions]);

  const versionLabel = platformVersion?.current_version ? `v${platformVersion.current_version}` : "—";
  const versionStatus = platformVersion?.status ?? "unknown";

  if (!expanded) return null;

  return (
    <div className="flex h-full flex-col bg-[radial-gradient(circle_at_top,hsl(var(--muted)/0.8),transparent_32%)]">
      <div className="border-b border-[var(--ui-border)] px-2.5 pb-2 pt-2">
        <button
          type="button"
          className="fx-workspace-chip"
          aria-label="Workspace switcher"
          title="Operator workspace"
        >
          <span className="fx-workspace-chip-avatar" aria-hidden="true">LX</span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="fx-workspace-chip-name">Lattix Corporation</span>
            <span className="fx-workspace-chip-role">Operator</span>
          </span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5" className="flex-shrink-0 text-[var(--fx-muted)]" aria-hidden="true">
            <path d="M2 4l3 3 3-3" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group) => (
          <section key={group.title} className="fx-nav-section">
            <h3 className="fx-nav-section-title">{group.title}</h3>
            <nav className="space-y-1.5" aria-label={group.title}>
              {group.items.map((item) => {
                const active = isActive(pathname, item.href);
                if (item.expandable) {
                  return (
                    <div key={item.href}>
                      <div className="flex items-stretch gap-1">
                        <Link
                          href={item.href}
                          className={`flex-1 ${active ? "fx-nav-item fx-nav-item-active" : "fx-nav-item"}`}
                        >
                          <span className="fx-nav-item-icon" aria-hidden="true">
                            <NavIcon name={item.icon} active={active} />
                          </span>
                          <span className="truncate">{item.label}</span>
                          <span className="ml-auto text-[10px] text-[var(--fx-muted)]">{filteredSessions.length}</span>
                        </Link>
                        <button
                          type="button"
                          onClick={() => setTasksOpen((v) => !v)}
                          aria-label={tasksOpen ? "Collapse tasks" : "Expand tasks"}
                          className="fx-btn-secondary inline-flex h-9 w-7 items-center justify-center"
                        >
                          <svg
                            viewBox="0 0 10 10"
                            width="10"
                            height="10"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            style={{
                              transform: tasksOpen ? "rotate(0deg)" : "rotate(-90deg)",
                              transition: "transform 120ms",
                            }}
                          >
                            <path d="M2 4l3 3 3-3" />
                          </svg>
                        </button>
                      </div>
                      {tasksOpen ? (
                        <div className="mt-1 space-y-1 pl-6">
                          <div className="px-2">
                            <input
                              type="search"
                              value={search}
                              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
                              placeholder="Search tasks…"
                              className="fx-input w-full px-2 py-1 text-[11px]"
                              aria-label="Search tasks"
                            />
                          </div>
                          {filteredSessions.length === 0 ? (
                            <div className="rounded-md border border-dashed border-[var(--ui-border)] px-2 py-2 text-[11px] text-[var(--fx-muted)]">
                              No tasks
                            </div>
                          ) : (
                            filteredSessions.map((run) => {
                              const taskActive =
                                pathname.startsWith("/inbox") && selectedSessionId === run.id;
                              const fxStatus = statusFromRunStatus(run.status);
                              const dot = FX_STATUS[fxStatus]?.dot ?? "var(--ui-border)";
                              return (
                                <Link
                                  key={run.id}
                                  href={sessionHref(run.id)}
                                  className={`flex items-center gap-2 rounded-md px-2 py-1 text-[11px] no-underline ${
                                    taskActive
                                      ? "bg-[var(--fx-nav-active)] text-[hsl(var(--foreground))]"
                                      : "text-[var(--fx-muted)] hover:bg-[var(--fx-nav-hover)] hover:text-[hsl(var(--foreground))]"
                                  }`}
                                >
                                  <span
                                    className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
                                    style={{
                                      background: dot,
                                      animation: run.status === "Running" ? "pulse 1.5s ease-in-out infinite" : "none",
                                    }}
                                  />
                                  <span className="flex-1 truncate">{run.title}</span>
                                  {run.inboxCount > 0 ? (
                                    <span className="rounded-full bg-[hsl(var(--card))] px-1.5 py-0.5 text-[9px] font-semibold text-[hsl(var(--foreground))]">
                                      {run.inboxCount}
                                    </span>
                                  ) : null}
                                </Link>
                              );
                            })
                          )}
                          <Link
                            href="/workflows/start"
                            className="mt-1 flex items-center gap-2 rounded-md border border-dashed border-[var(--ui-border)] px-2 py-1 text-[11px] text-[var(--fx-muted)] no-underline hover:bg-[var(--fx-nav-hover)] hover:text-[hsl(var(--foreground))]"
                          >
                            <span>+ New Task</span>
                          </Link>
                        </div>
                      ) : null}
                    </div>
                  );
                }
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={active ? "fx-nav-item fx-nav-item-active" : "fx-nav-item"}
                  >
                    <span className="fx-nav-item-icon" aria-hidden="true">
                      <NavIcon name={item.icon} active={active} />
                    </span>
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </section>
        ))}
      </div>

      <div className="border-t border-[var(--ui-border)] px-2 py-2">
        <Link
          href="/settings"
          className={isActive(pathname, "/settings") ? "fx-nav-item fx-nav-item-active" : "fx-nav-item"}
        >
          <span className="fx-nav-item-icon" aria-hidden="true">
            <NavIcon name="settings" active={isActive(pathname, "/settings")} />
          </span>
          <span className="truncate">Settings</span>
        </Link>
        <div className="fx-platform-footer-row">
          <span className="fx-platform-footer-label">Platform</span>
          <span className="fx-platform-footer-version">{versionLabel}</span>
        </div>
        <div className="fx-platform-footer-status">
          <span className="fx-platform-footer-status-dot" aria-hidden="true" />
          <span className="fx-platform-footer-status-text">
            {versionStatus === "up_to_date" ? "Systems Nominal" : versionStatus === "update_available" ? "Update available" : "Status unavailable"}
          </span>
        </div>
      </div>
    </div>
  );
}
