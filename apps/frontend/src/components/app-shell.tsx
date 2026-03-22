"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ModeSwitch } from "@/components/mode-switch";
import { ApiStatusBanner } from "@/components/api-status-banner";

type IconName = "inbox" | "workflow" | "artifact" | "studio" | "agent" | "nodes" | "guardrails" | "integrations" | "releases" | "settings";
type NavItem = { href: string; label: string; icon: IconName };
type NavGroup = { title: string; items: NavItem[] };

function NavIcon({ name }: { name: IconName }) {
  const cls = "h-4 w-4 text-[var(--foreground)]";

  if (name === "inbox") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 4h16v11H4z" />
        <path d="M4 15h5l2 3h2l2-3h5" />
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

  if (name === "artifact") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M6 3h9l3 3v15H6z" />
        <path d="M15 3v3h3" />
      </svg>
    );
  }

  if (name === "studio") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </svg>
    );
  }

  if (name === "agent") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="5" y="7" width="14" height="10" rx="2" />
        <path d="M9 12h.01M15 12h.01M12 7V4" />
      </svg>
    );
  }

  if (name === "nodes") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="5" cy="5" r="2" />
        <circle cx="19" cy="5" r="2" />
        <circle cx="12" cy="19" r="2" />
        <path d="M7 6.5l4 10M17 6.5l-4 10M7 5h10" />
      </svg>
    );
  }

  if (name === "guardrails") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3l8 3v6c0 4.5-3 7.5-8 9-5-1.5-8-4.5-8-9V6z" />
      </svg>
    );
  }

  if (name === "releases") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M5 19l14-14" />
        <path d="M14 5h5v5" />
        <path d="M5 10V5h5" />
      </svg>
    );
  }

  if (name === "integrations") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="4" width="7" height="6" />
        <rect x="14" y="4" width="7" height="6" />
        <rect x="8.5" y="14" width="7" height="6" />
        <path d="M10 7h4M7 10v4M17 10v4" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 8.92 4.6H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c0 .67.26 1.31.73 1.78.47.47 1.11.73 1.78.73H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

const userNavGroups: NavGroup[] = [
  {
    title: "Platform",
    items: [
      { href: "/inbox", label: "Inbox", icon: "inbox" },
      { href: "/workflows/start", label: "Workflows", icon: "workflow" },
      { href: "/artifacts", label: "Artifacts", icon: "artifact" },
    ],
  },
  {
    title: "Preferences",
    items: [{ href: "/settings", label: "Settings", icon: "settings" }],
  },
];

const builderNavGroups: NavGroup[] = [
  {
    title: "Platform",
    items: [
      { href: "/builder/agents", label: "Agent Studio", icon: "agent" },
      { href: "/builder/workflows", label: "Workflow Studio", icon: "studio" },
      { href: "/builder/templates", label: "Templates", icon: "artifact" },
      { href: "/builder/playbooks", label: "Playbooks", icon: "workflow" },
    ],
  },
  {
    title: "Services",
    items: [
      { href: "/builder/observability", label: "Observability", icon: "workflow" },
      { href: "/builder/integrations", label: "Integrations", icon: "integrations" },
      { href: "/builder/nodes", label: "Node Library", icon: "nodes" },
      { href: "/builder/guardrails", label: "Guardrails", icon: "guardrails" },
      { href: "/builder/releases", label: "Releases", icon: "releases" },
    ],
  },
  {
    title: "Preferences",
    items: [{ href: "/settings", label: "Settings", icon: "settings" }],
  },
];

const adminNavGroup: NavGroup = {
  title: "Admin",
  items: [{ href: "/settings", label: "Administration", icon: "settings" }],
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const mode = pathname.startsWith("/builder") ? "builder" : "user";
  const inAdmin = pathname.startsWith("/admin");
  const navGroups = useMemo(() => {
    const base = mode === "builder" ? [...builderNavGroups] : [...userNavGroups];
    if (inAdmin) {
      base.push(adminNavGroup);
    }
    return base;
  }, [inAdmin, mode]);

  const SHOW_SOFT_LAUNCH = true;
  const SHOW_CLASSIFICATION = true;
  const SHOW_READ_ONLY = false;

  const SOFT_LAUNCH_HEIGHT = 36;
  const CLASSIFICATION_HEIGHT = 32;
  const TOP_NAV_HEIGHT = 48;
  const READ_ONLY_HEIGHT = 24;

  const topLayerOffset = (SHOW_SOFT_LAUNCH ? SOFT_LAUNCH_HEIGHT : 0) + (SHOW_CLASSIFICATION ? CLASSIFICATION_HEIGHT : 0);
  const contentTopOffset = topLayerOffset + TOP_NAV_HEIGHT + (SHOW_READ_ONLY ? READ_ONLY_HEIGHT : 0);

  const sidebarWidthExpanded = 176;
  const sidebarWidthCollapsed = 0;
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") {
      return "dark";
    }

    const stored = window.localStorage.getItem("frontier-theme");
    return stored === "light" ? "light" : "dark";
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.innerWidth >= 768;
  });

  const breadcrumbParts = useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    const label = segments
      .slice(0, 3)
      .map((segment) => segment.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()));
    return ["Console", ...label];
  }, [pathname]);

  useEffect(() => {
    const html = document.documentElement;
    html.classList.remove("theme-light", "theme-dark");
    html.classList.add(`theme-${theme}`);
    window.localStorage.setItem("frontier-theme", theme);
  }, [theme]);

  return (
    <div className="fx-app min-h-screen text-[var(--foreground)]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[9999] focus:rounded-md focus:px-3 focus:py-2 focus:text-sm focus:font-medium fx-btn-primary"
      >
        Skip to content
      </a>
      {SHOW_SOFT_LAUNCH ? (
        <div className="fx-top-strip fixed inset-x-0 top-0 z-40 flex h-9 items-center justify-center px-4 text-[11px] font-semibold uppercase tracking-[0.12em]">
          Soft launch in progress • staging only • data operations disabled
        </div>
      ) : null}

      {SHOW_CLASSIFICATION ? (
        <div
          className="fixed inset-x-0 z-40 flex items-center justify-center border-b border-[var(--ui-border)] bg-[hsl(var(--muted))] px-4 text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{ top: SHOW_SOFT_LAUNCH ? `${SOFT_LAUNCH_HEIGHT}px` : "0px", height: `${CLASSIFICATION_HEIGHT}px` }}
        >
          Internal • Operational Console
        </div>
      ) : null}

      <header className="fx-header fixed inset-x-0 z-40" style={{ top: `${topLayerOffset}px`, height: `${TOP_NAV_HEIGHT}px` }}>
        <div className="flex h-full items-center justify-between gap-3 px-3">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setSidebarExpanded((value) => !value)}
              className="fx-btn-secondary inline-flex h-7 w-7 items-center justify-center text-xs"
              aria-label="Toggle sidebar"
            >
              ☰
            </button>
            <span className="text-xs font-semibold tracking-wide text-[var(--foreground)]">Lattix</span>
            <span className="fx-badge-local px-2 py-0.5 text-[10px]">Local</span>
            <nav className="min-w-0 truncate text-[11px] text-[var(--fx-muted)]">
              {breadcrumbParts.map((part, index) => (
                <span key={`${part}-${index}`}>
                  {index > 0 ? <span className="mx-1 text-[var(--fx-muted)]">/</span> : null}
                  <span className={index === breadcrumbParts.length - 1 ? "text-[var(--foreground)]" : ""}>{part}</span>
                </span>
              ))}
            </nav>
          </div>

          <div className="relative flex items-center gap-1.5">
            <a
              href="mailto:9ff6ac2b6c9d@intake.linear.app?subject=%5BFeedback%5D%20Lattix%20Frontier&body=%0A---%20Feedback%20---%0A%0AType%3A%20%5B%20Bug%20%7C%20Feature%20Request%20%7C%20Improvement%20%7C%20Other%20%5D%0A%0ADescription%3A%0A%0A%0ASteps%20to%20reproduce%20(if%20bug)%3A%0A1.%20%0A2.%20%0A3.%20%0A%0AExpected%20behavior%3A%0A%0A%0AActual%20behavior%3A%0A%0A%0AAdditional%20context%3A%0A"
              className="fx-btn-secondary px-2 py-1 text-[11px] no-underline"
            >Feedback</a>
            <button className="fx-btn-secondary h-7 w-7 px-0 text-[11px]" aria-label="Docs">
              ?
            </button>
            <button className="fx-btn-secondary h-7 w-7 px-0 text-[11px]" aria-label="Notifications">
              🔔
            </button>
            <span className="inline-flex items-center gap-1 rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--state-success))]" />
              DB OK
            </span>
            <ModeSwitch />
            {mode === "user" && (
              <Link
                href="/workflows/start"
                className="fx-btn-primary px-2.5 py-1 text-[11px] font-medium"
              >
                Start Workflow
              </Link>
            )}
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="fx-btn-secondary h-7 w-7 px-0 text-[11px] font-semibold"
              aria-label="User menu"
            >
              LD
            </button>
            {menuOpen && (
              <div className="fx-panel absolute right-0 top-9 z-50 min-w-44 p-1 shadow-xl">
                <button
                  onClick={() => {
                    setTheme("light");
                    setMenuOpen(false);
                  }}
                  className="block w-full rounded-md px-2 py-1.5 text-left text-xs text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
                >
                  Light mode
                </button>
                <button
                  onClick={() => {
                    setTheme("dark");
                    setMenuOpen(false);
                  }}
                  className="block w-full rounded-md px-2 py-1.5 text-left text-xs text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
                >
                  Dark mode
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {SHOW_READ_ONLY ? (
        <div className="fixed inset-x-0 z-30 flex items-center justify-center border-b border-[var(--ui-border)] bg-[hsl(var(--muted))] text-[10px]" style={{ top: `${topLayerOffset + TOP_NAV_HEIGHT}px`, height: `${READ_ONLY_HEIGHT}px` }}>
          Read-only mode enabled
        </div>
      ) : null}

      <div className="min-h-screen" style={{ paddingTop: `${contentTopOffset}px` }}>
        <aside
          className="fixed left-0 overflow-hidden border-r border-[var(--ui-border)] bg-[var(--fx-sidebar)] transition-[width] duration-200 ease-out"
          style={{
            top: `${contentTopOffset}px`,
            width: `${sidebarExpanded ? sidebarWidthExpanded : sidebarWidthCollapsed}px`,
            height: `calc(100vh - ${contentTopOffset}px)`,
            borderRightWidth: sidebarExpanded ? "1px" : "0px",
          }}
        >
          <div className="h-full overflow-y-auto p-2">
            <div className="fx-panel mb-2 p-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--fx-muted)]">Workspace</p>
              <p className="mt-1 truncate text-xs font-medium">Default Tenant</p>
              <p className="mt-0.5 text-[10px] text-[var(--fx-muted)]">local / single-tenant</p>
            </div>

            {navGroups.map((group) => (
              <section key={group.title} className="mb-3">
                <h3 className="px-1 pb-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--fx-muted)]">{group.title}</h3>
                <nav className="space-y-1">
                  {group.items.map((item) => {
                    const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-xs transition ${
                          active
                            ? "fx-nav-active font-semibold text-[hsl(var(--foreground))]"
                            : "text-[hsl(var(--foreground))] hover:bg-[var(--fx-nav-hover)]"
                        }`}
                      >
                        <span className={active ? "text-[var(--fx-primary)]" : ""}>
                          <NavIcon name={item.icon} />
                        </span>
                        <span className="truncate">{item.label}</span>
                      </Link>
                    );
                  })}
                </nav>
              </section>
            ))}
          </div>
        </aside>

        <main
          id="main-content"
          className="min-h-[calc(100vh-57px)] transition-[margin-left] duration-200"
          style={{ marginLeft: `${sidebarExpanded ? sidebarWidthExpanded : sidebarWidthCollapsed}px` }}
        >
          <ApiStatusBanner />
          <div className="p-5 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
