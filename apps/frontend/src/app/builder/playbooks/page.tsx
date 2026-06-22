"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getPlaybooks,
  instantiatePlaybook,
} from "@/lib/api";
import { ImportExportControls } from "@/components/import-export-controls";
import type { PlaybookDefinition } from "@/types/frontier";

export default function PlaybooksPage() {
  const router = useRouter();
  const [playbooks, setPlaybooks] = useState<PlaybookDefinition[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const playbookData = await getPlaybooks();
        if (cancelled) {
          return;
        }
        setPlaybooks(playbookData);
      } catch {
        if (!cancelled) {
          setError("Unable to load playbooks.");
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  async function reloadPlaybooks() {
    try {
      setPlaybooks(await getPlaybooks());
    } catch {
      setError("Unable to load playbooks.");
    }
  }

  async function handleCreateFromPlaybook(playbook: PlaybookDefinition) {
    setBusyKey(`playbook:${playbook.id}`);
    setError(null);
    try {
      const created = await instantiatePlaybook(playbook.id, {
        name: `${playbook.name} Instance`,
      });
      router.push(`/builder/workflows/${created.id}`);
    } catch {
      setError(`Failed to instantiate playbook ${playbook.name}.`);
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Playbooks</h1>
          <p className="fx-muted">Playbooks are collaborations of workflows designed to achieve high-level outcomes.</p>
        </div>
        <div className="flex items-center gap-3">
          <ImportExportControls kind="playbooks" onImported={() => void reloadPlaybooks()} />
          <button
            type="button"
            className="fx-btn-primary px-3 py-2 text-sm font-medium"
            onClick={() => router.push(`/builder/workflows/${crypto.randomUUID()}`)}
          >
            New Workflow
          </button>
        </div>
      </header>

      {error && (
        <div className="border border-[#6b1f2a] bg-[#2f1a21] p-3 text-sm text-[#ffb8c4]">
          {error}
        </div>
      )}

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Playbook</th>
              <th className="px-3 py-2 text-left">Category</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Description</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {playbooks.map((playbook) => (
              <tr key={playbook.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2 align-top font-medium text-[var(--foreground)]">{playbook.name}</td>
                <td className="px-3 py-2 align-top text-[var(--foreground)]">{playbook.category}</td>
                <td className="px-3 py-2 align-top text-[var(--foreground)]">{playbook.status}</td>
                <td className="fx-muted px-3 py-2 align-top">
                  <p className="max-w-[34rem] leading-snug line-clamp-3" title={playbook.description}>
                    {playbook.description}
                  </p>
                </td>
                <td className="px-3 py-2 align-top text-right whitespace-nowrap">
                  <div className="flex flex-nowrap items-center justify-end gap-2">
                    <ImportExportControls kind="playbooks" id={playbook.id} compact onImported={() => void reloadPlaybooks()} />
                    <button
                      className="fx-btn-secondary px-2.5 py-1 text-xs font-medium"
                      disabled={busyKey === `playbook:${playbook.id}` || playbook.status !== "active"}
                      onClick={() => void handleCreateFromPlaybook(playbook)}
                    >
                      {busyKey === `playbook:${playbook.id}` ? "Creating…" : "Launch Playbook"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {playbooks.length === 0 ? (
              <tr className="border-t border-[var(--fx-border)]">
                <td className="fx-muted px-3 py-3" colSpan={5}>No playbooks available.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
