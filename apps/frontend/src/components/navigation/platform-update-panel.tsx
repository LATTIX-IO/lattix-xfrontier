"use client";

import { useEffect, useState } from "react";
import type { PlatformVersionStatus } from "@/types/frontier";

/**
 * Bottom-of-sidebar platform version + update control.
 *
 * In the **desktop (Tauri) shell** the Tauri updater is the source of truth:
 * we ask the shell whether an update is available (`check_for_update`) and, if
 * so, render a single "Update & Restart" button. Clicking it confirms, then the
 * shell silently downloads + installs the signed update and relaunches
 * (`install_update_and_restart`) — no terminal, no manual steps.
 *
 * In the **hosted / browser** context there is no Tauri shell, so we fall back
 * to the backend version manifest (which carries the `lattix update` CLI guidance
 * for the Docker-stack install). The backend manifest is intentionally ignored in
 * desktop mode because the frozen sidecar can't report its own packaged version.
 */
type TauriApi = {
  core?: { invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown> };
  app?: { getVersion?: () => Promise<string> };
};

function getTauri(): TauriApi | null {
  if (typeof window === "undefined") return null;
  return (window as unknown as { __TAURI__?: TauriApi }).__TAURI__ ?? null;
}

export function PlatformUpdatePanel({
  platformVersion,
}: {
  platformVersion?: PlatformVersionStatus | null;
}) {
  const [isDesktop, setIsDesktop] = useState(false);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  // undefined = not yet checked, null = up to date, string = update available.
  const [tauriUpdate, setTauriUpdate] = useState<string | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const tauri = getTauri();
    if (!tauri?.core?.invoke) return;
    setIsDesktop(true);
    let cancelled = false;
    tauri.app
      ?.getVersion?.()
      .then((v) => {
        if (!cancelled) setAppVersion(v);
      })
      .catch(() => {
        /* ignore — fall back to backend-reported version */
      });
    tauri.core
      .invoke("check_for_update")
      .then((v) => {
        if (!cancelled) setTauriUpdate((v as string | null) ?? null);
      })
      .catch(() => {
        // No updater reachable / offline — treat as up to date, stay quiet.
        if (!cancelled) setTauriUpdate(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function updateNow(version: string) {
    const tauri = getTauri();
    if (!tauri?.core?.invoke) return;
    if (
      !window.confirm(
        `Update Lattix xFrontier to v${version}?\n\n` +
          `The app will close, install the update, and restart automatically.\n` +
          `Your workflows, agents, and settings stay intact.`,
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      await tauri.core.invoke("install_update_and_restart");
      // On success the app relaunches; this line is typically never reached.
    } catch (err) {
      setBusy(false);
      window.alert(`Update failed: ${String(err)}`);
    }
  }

  const currentLabel = appVersion
    ? `v${appVersion}`
    : platformVersion?.current_version
      ? `v${platformVersion.current_version}`
      : "Version unavailable";

  const backendUpdate =
    !isDesktop && platformVersion?.status === "update_available" ? platformVersion : null;
  const backendStatus = platformVersion?.status ?? "unknown";

  return (
    <div className="mt-3 border-t border-[var(--ui-border)] px-2 pt-3">
      <div className="flex items-center justify-between gap-3 text-[0.68rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">
        <span>Platform version</span>
        <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-[0.72rem] font-semibold normal-case text-[hsl(var(--foreground))]">
          {currentLabel}
        </span>
      </div>

      {isDesktop ? (
        typeof tauriUpdate === "string" ? (
          <div className="mt-3 rounded-2xl border border-[color-mix(in_srgb,var(--fx-primary-strong)_28%,var(--ui-border))] bg-[color-mix(in_srgb,var(--fx-primary)_12%,var(--fx-sidebar))] p-3 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-primary-strong)]">
              Update available
            </p>
            <p className="mt-1 text-[0.9rem] font-semibold text-[hsl(var(--foreground))]">
              {currentLabel} → v{tauriUpdate}
            </p>
            <p className="mt-2 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
              One click — the app verifies, restarts, and applies the update silently. Workflows,
              agents, settings, and installer state stay intact.
            </p>
            <button
              type="button"
              onClick={() => updateNow(tauriUpdate)}
              disabled={busy}
              className="mt-3 inline-flex w-full items-center justify-center rounded-xl bg-[var(--fx-primary-strong)] px-3 py-2 text-[0.78rem] font-semibold text-[hsl(var(--card))] transition-opacity hover:opacity-90 disabled:cursor-default disabled:opacity-60"
            >
              {busy ? "Updating…" : "Update & Restart"}
            </button>
          </div>
        ) : tauriUpdate === null ? (
          <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
            Current build is up to date.
          </p>
        ) : (
          <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
            Checking for updates…
          </p>
        )
      ) : backendUpdate ? (
        <div className="mt-3 rounded-2xl border border-[color-mix(in_srgb,var(--fx-primary-strong)_28%,var(--ui-border))] bg-[color-mix(in_srgb,var(--fx-primary)_12%,var(--fx-sidebar))] p-3 shadow-[0_10px_24px_rgba(0,0,0,0.16)]">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-primary-strong)]">
            Update available
          </p>
          <p className="mt-1 text-[0.9rem] font-semibold text-[hsl(var(--foreground))]">
            {currentLabel} → v{backendUpdate.latest_version}
          </p>
          <p className="mt-2 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
            Refresh the local app in place. Workflows, agents, settings, and installer state stay
            intact.
          </p>
          <details className="mt-3 rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card))] p-2 text-[0.74rem] text-[var(--foreground)]">
            <summary className="cursor-pointer list-none font-medium text-[var(--foreground)] marker:hidden">
              How to update
            </summary>
            <p className="mt-2 leading-5 text-[var(--fx-muted)]">
              Open a terminal on this machine and run the updater command below.
            </p>
            <div className="mt-2 rounded-lg border border-[var(--ui-border)] bg-[var(--fx-sidebar)] px-2 py-2 font-mono text-[0.72rem] text-[hsl(var(--foreground))]">
              {backendUpdate.update_command}
            </div>
            {backendUpdate.release_notes_url ? (
              <a
                href={backendUpdate.release_notes_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex text-[0.72rem] font-medium text-[var(--fx-primary-strong)] no-underline hover:underline"
              >
                View release source ↗
              </a>
            ) : null}
          </details>
        </div>
      ) : backendStatus === "up_to_date" ? (
        <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
          Current build is up to date.
        </p>
      ) : (
        <p className="mt-3 text-[0.74rem] leading-5 text-[var(--fx-muted)]">
          Update status is unavailable right now.
        </p>
      )}
    </div>
  );
}
