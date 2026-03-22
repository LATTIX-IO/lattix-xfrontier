"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getPlaybooks,
  instantiatePlaybook,
} from "@/lib/api";
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
      <header>
        <h1 className="text-2xl font-semibold">Playbooks</h1>
        <p className="fx-muted">Playbooks are collaborations of workflows designed to achieve high-level outcomes.</p>
      </header>

      {error && (
        <div className="border border-[#6b1f2a] bg-[#2f1a21] p-3 text-sm text-[#ffb8c4]">
          {error}
        </div>
      )}

      <div className="grid gap-4">
        <article className="fx-panel p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide fx-muted">Available Playbooks</h2>
          <ul className="space-y-2 text-sm">
            {playbooks.map((playbook) => (
              <li key={playbook.id} className="border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-[var(--foreground)]">{playbook.name}</div>
                    <div className="fx-muted">{playbook.description}</div>
                    <div className="mt-1 text-xs fx-muted">category={playbook.category} · status={playbook.status}</div>
                  </div>
                  <button
                    className="fx-btn-secondary px-2 py-1 text-xs"
                    disabled={busyKey === `playbook:${playbook.id}` || playbook.status !== "active"}
                    onClick={() => void handleCreateFromPlaybook(playbook)}
                  >
                    {busyKey === `playbook:${playbook.id}` ? "Creating..." : "Launch Playbook"}
                  </button>
                </div>
              </li>
            ))}
            {playbooks.length === 0 && <li className="fx-muted">No playbooks available.</li>}
          </ul>
        </article>
      </div>
    </section>
  );
}
