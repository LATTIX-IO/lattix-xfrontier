"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiStatusBanner } from "@/components/api-status-banner";
import { ModeSwitch } from "@/components/mode-switch";
import { LeftNav } from "@/components/navigation/left-nav";
import { getOperatorSession, getPlatformVersionStatus, logoutOperator } from "@/lib/api";
import type { AppMode, OperatorSession, PlatformVersionStatus } from "@/types/frontier";

function resolveOperatorLabel(session: OperatorSession | null): string {
  if (!session) {
    return "Operator";
  }
  return session.display_name || session.preferred_username || session.email || session.actor || "Operator";
}

function resolveOperatorSecondaryLabel(session: OperatorSession | null): string {
  if (!session) {
    return "";
  }
  return session.email || session.subject || session.principal_id || "";
}

function resolveOperatorInitials(session: OperatorSession | null): string {
  const label = resolveOperatorLabel(session)
    .trim()
    .replace(/[^\p{L}\p{N}\s]+/gu, " ");
  if (!label) {
    return "OP";
  }
  const parts = label.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  return label.slice(0, 2).toUpperCase();
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublicAuthRoute = pathname.startsWith("/auth");
  const isProtectedRoute = !isPublicAuthRoute;
  const requestedMode: AppMode = pathname.startsWith("/builder") ? "builder" : "user";
  const inAdmin = pathname.startsWith("/admin");
  const [operatorSession, setOperatorSession] = useState<OperatorSession | null>(null);
  const [platformVersion, setPlatformVersion] = useState<PlatformVersionStatus | null>(null);
  const sessionRequestIdRef = useRef(0);
  const [activeSessionRequestId, setActiveSessionRequestId] = useState(0);
  const [resolvedSessionRequestId, setResolvedSessionRequestId] = useState(0);

  const SHOW_SOFT_LAUNCH = true;
  const SHOW_CLASSIFICATION = true;
  const SHOW_READ_ONLY = false;

  const SOFT_LAUNCH_HEIGHT = 36;
  const CLASSIFICATION_HEIGHT = 32;
  const TOP_NAV_HEIGHT = 48;
  const READ_ONLY_HEIGHT = 24;

  const topLayerOffset = (SHOW_SOFT_LAUNCH ? SOFT_LAUNCH_HEIGHT : 0) + (SHOW_CLASSIFICATION ? CLASSIFICATION_HEIGHT : 0);
  const contentTopOffset = topLayerOffset + TOP_NAV_HEIGHT + (SHOW_READ_ONLY ? READ_ONLY_HEIGHT : 0);

  const sidebarWidthExpanded = 248;
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
    if (typeof window === "undefined") {
      return true;
    }
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

  useEffect(() => {
    let cancelled = false;
    const requestId = sessionRequestIdRef.current + 1;
    sessionRequestIdRef.current = requestId;
    setActiveSessionRequestId(requestId);

    getOperatorSession()
      .then((session) => {
        if (!cancelled) {
          setOperatorSession(session);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOperatorSession(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setResolvedSessionRequestId(requestId);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  useEffect(() => {
    let cancelled = false;

    getPlatformVersionStatus()
      .then((status) => {
        if (!cancelled) {
          setPlatformVersion(status);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPlatformVersion(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const sessionResolved = activeSessionRequestId !== 0 && resolvedSessionRequestId === activeSessionRequestId;
  const operatorLabel = resolveOperatorLabel(operatorSession);
  const operatorSecondaryLabel = resolveOperatorSecondaryLabel(operatorSession);
  const operatorInitials = resolveOperatorInitials(operatorSession);

  useEffect(() => {
    if (!sessionResolved || requestedMode !== "builder") {
      return;
    }
    if (operatorSession?.capabilities.can_builder) {
      return;
    }
    router.replace(operatorSession?.authenticated ? "/inbox" : "/auth");
  }, [operatorSession?.authenticated, operatorSession?.capabilities.can_builder, requestedMode, router, sessionResolved]);

  useEffect(() => {
    if (!isProtectedRoute || !sessionResolved || operatorSession?.authenticated) {
      return;
    }
    router.replace("/auth");
  }, [isProtectedRoute, operatorSession?.authenticated, router, sessionResolved]);

  useEffect(() => {
    if (!isPublicAuthRoute || !sessionResolved || !operatorSession?.authenticated) {
      return;
    }
    const defaultHref = operatorSession.capabilities.can_builder && operatorSession.default_mode === "builder"
      ? "/builder/workflows"
      : "/inbox";
    router.replace(defaultHref);
  }, [isPublicAuthRoute, operatorSession?.authenticated, operatorSession?.capabilities.can_builder, operatorSession?.default_mode, router, sessionResolved]);

  const canBuilder = operatorSession?.capabilities.can_builder ?? false;
  const canAdmin = operatorSession?.capabilities.can_admin ?? false;
  const activeMode: AppMode = requestedMode === "builder" && canBuilder ? "builder" : "user";

  if (isPublicAuthRoute) {
    return (
      <div className="fx-app min-h-screen text-[var(--foreground)]">
        <div className="fixed inset-x-0 top-0 z-30 border-b border-[var(--ui-border)] bg-[color-mix(in_srgb,var(--fx-header)_94%,transparent)] backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Lattix xFrontier</span>
              <span className="fx-badge-local px-2 py-0.5 text-[10px]">Identity</span>
            </div>
            <span className="text-[11px] font-medium text-[var(--fx-muted)]">Authentication required</span>
          </div>
        </div>
        <ApiStatusBanner />
        <main className="min-h-screen pt-14">{children}</main>
      </div>
    );
  }

  if (!sessionResolved || !operatorSession?.authenticated) {
    return (
      <div className="fx-app min-h-screen text-[var(--foreground)]">
        <div className="fixed inset-x-0 top-0 z-30 border-b border-[var(--ui-border)] bg-[color-mix(in_srgb,var(--fx-header)_94%,transparent)] backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Lattix xFrontier</span>
              <span className="fx-badge-local px-2 py-0.5 text-[10px]">Locked</span>
            </div>
            <span className="text-[11px] font-medium text-[var(--fx-muted)]">
              {sessionResolved ? "Redirecting to login…" : "Checking operator session…"}
            </span>
          </div>
        </div>
        <ApiStatusBanner />
        <main className="flex min-h-screen items-center justify-center px-4 pt-14">
          <div className="fx-panel max-w-md p-6 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Secure local access</p>
            <h1 className="mt-3 text-xl font-semibold text-[hsl(var(--foreground))]">
              {sessionResolved ? "Login required" : "Verifying your session"}
            </h1>
            <p className="mt-2 text-sm leading-6 text-[var(--fx-muted)]">
              {sessionResolved
                ? "Protected routes stay fail-closed until an authenticated operator session is present."
                : "Hold tight while the console validates your operator session before rendering protected data."}
            </p>
          </div>
        </main>
      </div>
    );
  }

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
            >
              Feedback
            </a>
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
            <ModeSwitch activeMode={activeMode} canAccessBuilder={canBuilder} />
            {activeMode === "user" ? (
              <Link href="/workflows/start" className="fx-btn-primary px-2.5 py-1 text-[11px] font-medium">
                Start Workflow
              </Link>
            ) : null}
            <button
              onClick={() => setMenuOpen((value) => !value)}
              className="fx-btn-secondary h-7 w-7 px-0 text-[11px] font-semibold"
              aria-label="User menu"
              title={operatorLabel}
            >
              {operatorInitials}
            </button>
            {menuOpen ? (
              <div className="fx-panel absolute right-0 top-9 z-50 min-w-72 p-1 shadow-xl">
                <div className="border-b border-[var(--ui-border)] px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--fx-muted)]">Signed in as</p>
                  <p className="mt-1 text-sm font-semibold text-[hsl(var(--foreground))]">{operatorLabel}</p>
                  {operatorSecondaryLabel ? (
                    <p className="mt-1 break-all text-[11px] text-[var(--fx-muted)]">{operatorSecondaryLabel}</p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[10px] font-medium text-[hsl(var(--foreground))]">
                      {operatorSession?.authenticated ? "Authenticated" : "Anonymous"}
                    </span>
                    <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[10px] font-medium text-[hsl(var(--foreground))]">
                      {canBuilder ? "Builder access enabled" : "Builder access locked"}
                    </span>
                    {canAdmin ? (
                      <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[10px] font-medium text-[hsl(var(--foreground))]">
                        Admin access enabled
                      </span>
                    ) : null}
                    {(operatorSession?.roles ?? []).map((role) => (
                      <span key={role} className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[10px] font-medium text-[hsl(var(--foreground))]">
                        {role}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => {
                    setTheme("light");
                    setMenuOpen(false);
                  }}
                  className="block w-full rounded-md px-3 py-2 text-left text-xs text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
                >
                  Light mode
                </button>
                <button
                  onClick={() => {
                    setTheme("dark");
                    setMenuOpen(false);
                  }}
                  className="block w-full rounded-md px-3 py-2 text-left text-xs text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
                >
                  Dark mode
                </button>
                <button
                  onClick={async () => {
                    try {
                      await logoutOperator();
                    } finally {
                      setOperatorSession(null);
                      setMenuOpen(false);
                      router.replace("/auth");
                      router.refresh();
                    }
                  }}
                  className="block w-full rounded-md px-3 py-2 text-left text-xs text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {SHOW_READ_ONLY ? (
        <div
          className="fixed inset-x-0 z-30 flex items-center justify-center border-b border-[var(--ui-border)] bg-[hsl(var(--muted))] text-[10px]"
          style={{ top: `${topLayerOffset + TOP_NAV_HEIGHT}px`, height: `${READ_ONLY_HEIGHT}px` }}
        >
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
          <LeftNav
            mode={activeMode}
            pathname={pathname}
            inAdmin={inAdmin && canAdmin}
            expanded={sidebarExpanded}
            platformVersion={platformVersion}
          />
        </aside>

        <main
          id="main-content"
          className="min-h-[calc(100vh-57px)] transition-[margin-left] duration-200"
          style={{ marginLeft: `${sidebarExpanded ? sidebarWidthExpanded : sidebarWidthCollapsed}px` }}
        >
          <ApiStatusBanner />
          <div className="p-5 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
