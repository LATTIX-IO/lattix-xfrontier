"use client";

import Link from "next/link";
import { getPreferenceNavItem, getPrimaryNavGroups, type NavGroup, type NavIconName, type NavItem, type NavMode } from "@/components/navigation/nav-config";
import type { PlatformVersionStatus } from "@/types/frontier";

type LeftNavProps = {
  mode: NavMode;
  pathname: string;
  inAdmin: boolean;
  expanded: boolean;
  platformVersion?: PlatformVersionStatus | null;
};

function NavIcon({ name, active }: { name: NavIconName; active: boolean }) {
  const cls = `h-[1.05rem] w-[1.05rem] ${active ? "text-[var(--fx-primary-strong)]" : "text-[var(--fx-muted)]"}`;

  if (name === "inbox") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 4h16v11H4z" />
        <path d="M4 15h5l2 3h2l2-3h5" />
      </svg>
    );
  }

  if (name === "workflow" || name === "playbooks") {
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

  if (name === "artifact" || name === "templates") {
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

  if (name === "observability") {
    return (
      <svg viewBox="0 0 24 24" className={cls} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 18h16" />
        <path d="M7 15V9" />
        <path d="M12 15V5" />
        <path d="M17 15v-3" />
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

function isActive(pathname: string, item: NavItem) {
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavSection({ group, pathname }: { group: NavGroup; pathname: string }) {
  return (
    <section className="fx-nav-section">
      <h3 className="fx-nav-section-title">{group.title}</h3>
      <nav className="space-y-1.5" aria-label={group.title}>
        {group.items.map((item) => {
          const active = isActive(pathname, item);

          return (
            <Link key={item.href} href={item.href} className={active ? "fx-nav-item fx-nav-item-active" : "fx-nav-item"}>
              <span className="fx-nav-item-icon" aria-hidden="true">
                <NavIcon name={item.icon} active={active} />
              </span>
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </section>
  );
}

export function LeftNav({ mode, pathname, inAdmin, expanded, platformVersion }: LeftNavProps) {
  const navGroups = getPrimaryNavGroups(mode, inAdmin);
  const preferenceItem = getPreferenceNavItem(mode);
  const modeLabel = mode === "builder" ? "Builder Console" : "Operational Console";
  const workspaceLabel = mode === "builder" ? "Builder workspace" : "Workspace";
  const versionLabel = platformVersion?.current_version ? `v${platformVersion.current_version}` : "Version unavailable";
  const latestVersionLabel = platformVersion?.latest_version ? `v${platformVersion.latest_version}` : "";
  const versionStatus = platformVersion?.status ?? "unknown";
  const updateVersionDetails = versionStatus === "update_available" && platformVersion ? platformVersion : null;

  if (!expanded) {
    return null;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--ui-border)] px-3 pb-3 pt-3">
        <button type="button" className="fx-workspace-switcher w-full text-left" aria-label="Workspace switcher">
          <span className="fx-workspace-switcher-kicker">{workspaceLabel}</span>
          <span className="mt-1 block truncate text-[0.92rem] font-semibold text-[hsl(var(--foreground))]">Lattix Corporation</span>
          <span className="mt-1 flex items-center justify-between gap-2 text-[0.72rem] text-[var(--fx-muted)]">
            <span className="truncate">{modeLabel}</span>
            <span aria-hidden="true">⌄</span>
          </span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3">
        {navGroups.map((group) => (
          <NavSection key={group.title} group={group} pathname={pathname} />
        ))}
      </div>

      <div className="border-t border-[var(--ui-border)] px-2 py-3">
        <section className="fx-nav-section mb-0">
          <h3 className="fx-nav-section-title">Preferences</h3>
          <nav aria-label="Preferences">
            <Link
              href={preferenceItem.href}
              className={isActive(pathname, preferenceItem) ? "fx-nav-item fx-nav-item-active" : "fx-nav-item"}
            >
              <span className="fx-nav-item-icon" aria-hidden="true">
                <NavIcon name={preferenceItem.icon} active={isActive(pathname, preferenceItem)} />
              </span>
              <span className="truncate">{preferenceItem.label}</span>
            </Link>
          </nav>
        </section>

        <div className="mt-3 border-t border-[var(--ui-border)] px-2 pt-3">
          <div className="flex items-center justify-between gap-3 text-[0.68rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">
            <span>Platform version</span>
            <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[0.72rem] font-semibold normal-case text-[hsl(var(--foreground))]">
              {versionLabel}
            </span>
          </div>

          {updateVersionDetails ? (
            <div className="mt-3 rounded-2xl border border-[color-mix(in_srgb,var(--fx-primary-strong)_28%,var(--ui-border))] bg-[color-mix(in_srgb,var(--fx-primary)_12%,var(--fx-sidebar))] p-3 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-primary-strong)]">Update available</p>
              <p className="mt-1 text-[0.9rem] font-semibold text-[hsl(var(--foreground))]">
                {versionLabel} → {latestVersionLabel}
              </p>
              <p className="mt-2 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
                Refresh the local app in place. Workflows, agents, settings, and installer state stay intact.
              </p>
              <details className="mt-3 rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card))] p-2 text-[0.74rem] text-[var(--foreground)]">
                <summary className="cursor-pointer list-none font-medium text-[var(--foreground)] marker:hidden">
                  How to update
                </summary>
                <p className="mt-2 leading-5 text-[var(--fx-muted)]">Open a terminal on this machine and run the updater command below.</p>
                <div className="mt-2 rounded-lg border border-[var(--ui-border)] bg-[var(--fx-sidebar)] px-2 py-2 font-mono text-[0.72rem] text-[hsl(var(--foreground))]">
                  {updateVersionDetails.update_command}
                </div>
                {updateVersionDetails.release_notes_url ? (
                  <a
                    href={updateVersionDetails.release_notes_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-[0.72rem] font-medium text-[var(--fx-primary-strong)] no-underline hover:underline"
                  >
                    View release source ↗
                  </a>
                ) : null}
              </details>
            </div>
          ) : versionStatus === "up_to_date" ? (
            <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">Current build is up to date.</p>
          ) : (
            <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">Update status is unavailable right now.</p>
          )}
        </div>
      </div>
    </div>
  );
}
