"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getSkills,
  saveSkill,
  testSkill,
  type SkillDefinition,
  type SkillTestResult,
} from "@/lib/api";

type Draft = {
  name: string;
  description: string;
  content: string;
  tags: string;
  auto_inject: boolean;
  status: "enabled" | "disabled";
};

const EMPTY_DRAFT: Draft = {
  name: "",
  description: "",
  content: "## Goal\n\n## Steps\n1. \n\n## Output\n",
  tags: "",
  auto_inject: true,
  status: "enabled",
};

export default function SkillBuilderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [existing, setExisting] = useState<SkillDefinition | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState<"save" | "test" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [testPrompt, setTestPrompt] = useState("");
  const [testModel, setTestModel] = useState("");
  const [testResult, setTestResult] = useState<SkillTestResult | null>(null);

  const load = useCallback(async () => {
    try {
      const skills = await getSkills();
      const match = skills.find((skill) => skill.id === id) ?? null;
      setExisting(match);
      if (match) {
        setDraft({
          name: match.name,
          description: match.description,
          content: match.content,
          tags: match.tags.join(", "),
          auto_inject: match.auto_inject,
          status: match.status,
        });
        setSaved(true);
      }
    } catch {
      setNotice("Unable to load the skill registry.");
    } finally {
      setLoaded(true);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!draft.name.trim()) {
      setNotice("Skill name is required.");
      return;
    }
    setBusy("save");
    setNotice(null);
    try {
      await saveSkill({
        id,
        name: draft.name.trim(),
        description: draft.description.trim(),
        content: draft.content,
        status: draft.status,
        auto_inject: draft.auto_inject,
        tags: draft.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setSaved(true);
      setNotice("Skill saved.");
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Unable to save the skill.");
    } finally {
      setBusy(null);
    }
  }

  async function handleTest() {
    if (!testPrompt.trim()) {
      setNotice("Enter a sample task to test the skill against.");
      return;
    }
    setBusy("test");
    setNotice(null);
    setTestResult(null);
    try {
      const result = await testSkill(id, {
        prompt: testPrompt.trim(),
        model: testModel.trim() || undefined,
      });
      setTestResult(result);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Skill test failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide fx-muted">
            <Link href="/builder/skills" className="underline decoration-dotted underline-offset-2">
              Skills
            </Link>{" "}
            / {existing ? existing.name : "new"}
          </p>
          <h1 className="text-xl font-semibold">
            {existing ? `Edit skill: ${existing.name}` : loaded ? "New skill" : "Loading skill..."}
          </h1>
          <p className="fx-muted text-sm">
            SKILL.md-style operating procedure. Save it, then dry-run it against a sample task before
            enabling it platform-wide.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {existing ? (
            <>
              <span className="rounded-full border border-[var(--ui-border)] px-2 py-1">v{existing.version}</span>
              <span className="rounded-full border border-[var(--ui-border)] px-2 py-1">{existing.source}</span>
              <span className="rounded-full border border-[var(--ui-border)] px-2 py-1">
                used {existing.usage_count}×
              </span>
            </>
          ) : null}
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void handleSave()}
            className="fx-btn-primary px-3 py-2 text-sm font-medium disabled:opacity-60"
          >
            {busy === "save" ? "Saving..." : "Save skill"}
          </button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <article className="fx-panel space-y-2.5 p-3 text-xs">
          <h2 className="text-sm font-semibold">Definition</h2>
          <div className="grid gap-2.5 md:grid-cols-2">
            <label className="block">
              <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">Name</span>
              <input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="release-notes"
                className="fx-field h-8 w-full px-2"
              />
            </label>
            <label className="block">
              <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">Tags (comma separated)</span>
              <input
                value={draft.tags}
                onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
                placeholder="delivery, git"
                className="fx-field h-8 w-full px-2"
              />
            </label>
          </div>
          <label className="block">
            <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">Description</span>
            <input
              value={draft.description}
              onChange={(event) => setDraft({ ...draft, description: event.target.value })}
              placeholder="What this procedure achieves"
              className="fx-field h-8 w-full px-2"
            />
          </label>
          <label className="block">
            <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">Procedure (markdown)</span>
            <textarea
              value={draft.content}
              onChange={(event) => setDraft({ ...draft, content: event.target.value })}
              className="fx-field min-h-72 w-full p-2 font-mono"
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={draft.status === "enabled"}
                onChange={(event) =>
                  setDraft({ ...draft, status: event.target.checked ? "enabled" : "disabled" })
                }
              />
              Enabled
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={draft.auto_inject}
                onChange={(event) => setDraft({ ...draft, auto_inject: event.target.checked })}
              />
              Auto-inject into agent prompts
            </label>
          </div>
        </article>

        <article className="fx-panel space-y-2.5 p-3 text-xs">
          <h2 className="text-sm font-semibold">Test bench</h2>
          <p className="fx-muted leading-5">
            Runs a sample task with <em>only this skill</em> injected, using the configured inference
            providers. Save the skill before testing.
          </p>
          <label className="block">
            <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">Sample task</span>
            <textarea
              value={testPrompt}
              onChange={(event) => setTestPrompt(event.target.value)}
              placeholder="Commit the current changes with an appropriate message."
              className="fx-field min-h-20 w-full p-2"
            />
          </label>
          <label className="block">
            <span className="fx-muted mb-1 block text-[11px] uppercase tracking-wide">
              Model (optional — e.g. ollama/llama3.2:3b, nim/&lt;model&gt;, anthropic/&lt;model&gt;)
            </span>
            <input
              value={testModel}
              onChange={(event) => setTestModel(event.target.value)}
              placeholder="platform default"
              className="fx-field h-8 w-full px-2 font-mono"
            />
          </label>
          <button
            type="button"
            disabled={busy !== null || !saved}
            onClick={() => void handleTest()}
            className="fx-btn-secondary px-3 py-2 text-sm font-medium disabled:opacity-60"
            title={saved ? "" : "Save the skill before testing"}
          >
            {busy === "test" ? "Running..." : "Run test"}
          </button>

          {testResult ? (
            <div className="space-y-1.5 rounded border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
              <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide fx-muted">
                <span>provider: {testResult.provider}</span>
                <span>model: {testResult.model}</span>
                <span>mode: {testResult.mode}</span>
              </div>
              {testResult.mode !== "live" && testResult.reason ? (
                <p className="text-[hsl(var(--state-warning))]">{testResult.reason}</p>
              ) : null}
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-[var(--foreground)]">{testResult.output}</pre>
            </div>
          ) : null}
        </article>
      </div>

      {notice ? <p className="fx-muted text-xs">{notice}</p> : null}
    </section>
  );
}
