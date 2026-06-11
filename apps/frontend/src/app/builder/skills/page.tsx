"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { deleteSkill, getSkills, saveSkill, type SkillDefinition } from "@/lib/api";

export default function SkillsInventoryPage() {
  const router = useRouter();
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSkills(await getSkills());
      setError(null);
    } catch {
      setError("Unable to load skills. Check that the backend is reachable.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function toggleSkill(skill: SkillDefinition) {
    setBusy(skill.id);
    setNotice(null);
    try {
      await saveSkill({ id: skill.id, status: skill.status === "enabled" ? "disabled" : "enabled" });
      await refresh();
    } catch {
      setNotice(`Unable to update ${skill.name}.`);
    } finally {
      setBusy(null);
    }
  }

  async function removeSkill(skill: SkillDefinition) {
    setBusy(skill.id);
    setNotice(null);
    try {
      await deleteSkill(skill.id);
      setNotice(`Deleted ${skill.name}.`);
      await refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : `Unable to delete ${skill.name}.`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Skills</h1>
          <p className="fx-muted">
            Operating procedures injected into agent context. Open a skill to edit, version, and test it.
          </p>
        </div>
        <button
          type="button"
          className="fx-btn-primary px-3 py-2 text-sm font-medium"
          onClick={() => router.push(`/builder/skills/${crypto.randomUUID()}`)}
        >
          New Skill
        </button>
      </header>

      {error ? <div className="fx-panel border-[hsl(var(--state-critical)/0.4)] p-3 text-sm">{error}</div> : null}

      <div className="fx-panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Skill</th>
              <th className="px-3 py-2 text-left">Source</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Version</th>
              <th className="px-3 py-2 text-left">Uses</th>
              <th className="px-3 py-2 text-left">Last used</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((skill) => (
              <tr key={skill.id} className="border-t border-[var(--fx-border)]">
                <td className="px-3 py-2">
                  <p className="font-mono font-medium text-[var(--foreground)]">{skill.name}</p>
                  <p className="fx-muted text-xs">{skill.description}</p>
                </td>
                <td className="px-3 py-2 text-[var(--foreground)]">{skill.source}</td>
                <td className="px-3 py-2">
                  <span
                    className={
                      skill.status === "enabled"
                        ? "text-[hsl(var(--state-success))]"
                        : "fx-muted"
                    }
                  >
                    {skill.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-[var(--foreground)]">v{skill.version}</td>
                <td className="px-3 py-2 text-[var(--foreground)]">{skill.usage_count}</td>
                <td className="fx-muted px-3 py-2 text-xs">{skill.last_used_at || "never"}</td>
                <td className="px-3 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <Link className="fx-btn-primary px-2.5 py-1 text-xs font-medium" href={`/builder/skills/${skill.id}`}>
                      Open
                    </Link>
                    <button
                      type="button"
                      disabled={busy === skill.id}
                      onClick={() => void toggleSkill(skill)}
                      className="fx-btn-secondary px-2.5 py-1 text-xs font-medium disabled:opacity-60"
                    >
                      {skill.status === "enabled" ? "Disable" : "Enable"}
                    </button>
                    {skill.source === "custom" ? (
                      <button
                        type="button"
                        disabled={busy === skill.id}
                        onClick={() => void removeSkill(skill)}
                        className="fx-btn-secondary px-2.5 py-1 text-xs font-medium disabled:opacity-60"
                      >
                        Delete
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
            {skills.length === 0 && !error ? (
              <tr>
                <td colSpan={7} className="fx-muted px-3 py-4 text-sm">
                  Loading skills...
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {notice ? <p className="fx-muted text-xs">{notice}</p> : null}
    </section>
  );
}
