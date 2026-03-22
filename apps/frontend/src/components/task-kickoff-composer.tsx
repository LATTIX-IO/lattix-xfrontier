"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createWorkflowRun, getAgentDefinitions, getPublishedWorkflows } from "@/lib/api";
import type { AgentDefinition, WorkflowDefinition } from "@/types/frontier";

type TokenKind = "data" | "tag" | "workflow" | "agent";

type ParsedToken = {
  kind: TokenKind;
  value: string;
};

type MentionSuggestion = {
  trigger: "@" | "/";
  value: string;
  label: string;
};

const delimiterLegend: Array<{ symbol: string; meaning: string; example: string }> = [
  { symbol: "$", meaning: "Bring in data/source", example: "$crm_q1_pipeline" },
  { symbol: "#", meaning: "Task tag/priority", example: "#need-review" },
  { symbol: "/", meaning: "Call workflow", example: "/investor-pack" },
  { symbol: "@", meaning: "Assign agent", example: "@orchestration-agent" },
];

function parseTokens(text: string): ParsedToken[] {
  const matches = text.match(/([$#/@])[^\s$#/@]+/g) ?? [];

  return matches.map((token) => {
    const prefix = token[0];
    const value = token.slice(1);

    if (prefix === "$") return { kind: "data", value };
    if (prefix === "#") return { kind: "tag", value };
    if (prefix === "/") return { kind: "workflow", value };
    return { kind: "agent", value };
  });
}

function tokenClass(kind: TokenKind): string {
  if (kind === "data") return "border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] text-[var(--foreground)]";
  if (kind === "tag") return "border border-[var(--fx-warning)] bg-[color-mix(in_srgb,var(--fx-warning)_20%,transparent)] text-[var(--foreground)]";
  if (kind === "workflow") return "border border-[var(--fx-primary)] bg-[color-mix(in_srgb,var(--fx-primary)_20%,transparent)] text-[var(--foreground)]";
  return "border border-[var(--fx-success)] bg-[color-mix(in_srgb,var(--fx-success)_20%,transparent)] text-[var(--foreground)]";
}

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function getActiveMentionToken(text: string, cursor: number): { trigger: "@" | "/"; query: string; start: number; end: number } | null {
  if (cursor < 0 || cursor > text.length) {
    return null;
  }

  let start = cursor - 1;
  while (start >= 0 && !/\s/.test(text[start])) {
    start -= 1;
  }
  start += 1;

  const token = text.slice(start, cursor);
  if (!token || (token[0] !== "@" && token[0] !== "/")) {
    return null;
  }

  if (token.length > 1 && /[@/]/.test(token.slice(1))) {
    return null;
  }

  return {
    trigger: token[0] as "@" | "/",
    query: token.slice(1),
    start,
    end: cursor,
  };
}

export function TaskKickoffComposer() {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [publishedAgents, setPublishedAgents] = useState<AgentDefinition[]>([]);
  const [publishedWorkflows, setPublishedWorkflows] = useState<WorkflowDefinition[]>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const tokens = useMemo(() => parseTokens(draft), [draft]);

  useEffect(() => {
    let cancelled = false;

    async function loadMentions() {
      const [agentDefs, workflowDefs] = await Promise.all([getAgentDefinitions(), getPublishedWorkflows()]);
      if (cancelled) {
        return;
      }
      setPublishedAgents(agentDefs.filter((agent) => agent.status === "published"));
      setPublishedWorkflows(workflowDefs.filter((workflow) => workflow.status === "published"));
    }

    void loadMentions();

    return () => {
      cancelled = true;
    };
  }, []);

  const activeMention = useMemo(() => getActiveMentionToken(draft, cursorPosition), [draft, cursorPosition]);

  const mentionSuggestions = useMemo<MentionSuggestion[]>(() => {
    if (!activeMention) {
      return [];
    }

    const query = activeMention.query.toLowerCase();
    if (activeMention.trigger === "@") {
      return publishedAgents
        .map((agent) => {
          const value = slugify(agent.name) || slugify(agent.id);
          return {
            trigger: "@" as const,
            value,
            label: `${agent.name} (v${agent.version})`,
          };
        })
        .filter((item) => item.value.includes(query) || item.label.toLowerCase().includes(query))
        .slice(0, 8);
    }

    return publishedWorkflows
      .map((workflow) => ({
        trigger: "/" as const,
        value: slugify(workflow.name) || slugify(workflow.id),
        label: `${workflow.name} (v${workflow.version})`,
      }))
      .filter((item) => item.value.includes(query) || item.label.toLowerCase().includes(query))
      .slice(0, 8);
  }, [activeMention, publishedAgents, publishedWorkflows]);

  useEffect(() => {
    setActiveSuggestionIndex(0);
  }, [activeMention?.trigger, activeMention?.query]);

  function applyMentionSuggestion(suggestion: MentionSuggestion) {
    if (!activeMention) {
      return;
    }

    const nextDraft = `${draft.slice(0, activeMention.start)}${suggestion.trigger}${suggestion.value} ${draft.slice(activeMention.end)}`;
    const nextCursor = activeMention.start + suggestion.value.length + 2;
    setDraft(nextDraft);
    setCursorPosition(nextCursor);

    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(nextCursor, nextCursor);
      }
    });
  }

  function handleTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!activeMention || mentionSuggestions.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestionIndex((previous) => (previous + 1) % mentionSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestionIndex((previous) => (previous - 1 + mentionSuggestions.length) % mentionSuggestions.length);
      return;
    }

    if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault();
      const selected = mentionSuggestions[activeSuggestionIndex] ?? mentionSuggestions[0];
      if (selected) {
        applyMentionSuggestion(selected);
      }
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      setCursorPosition(-1);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) return;
    setSubmitError(null);

    try {
      setIsSubmitting(true);
      const publishedAgentSlugs = new Set(publishedAgents.map((agent) => slugify(agent.name) || slugify(agent.id)));
      const publishedWorkflowSlugs = new Set(publishedWorkflows.map((workflow) => slugify(workflow.name) || slugify(workflow.id)));
      const filteredTokens = tokens.filter((token) => {
        if (token.kind === "agent") {
          return publishedAgentSlugs.has(token.value);
        }
        if (token.kind === "workflow") {
          return publishedWorkflowSlugs.has(token.value);
        }
        return true;
      });

      const payload = {
        prompt: draft,
        tokens: filteredTokens,
      };
      const result = await createWorkflowRun(payload);
      setCreatedRunId(result.id);
      setDraft("");
      router.refresh();
    } catch {
      setSubmitError("Unable to start task run. Please verify backend connectivity and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fx-panel p-4">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Kick off new task</h2>
      <p className="fx-muted mb-3 text-sm">
        Use delimiters to structure intent: data, tags, workflow routing, and agent assignment.
      </p>

      <form onSubmit={onSubmit} className="space-y-3">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            setCursorPosition(event.target.selectionStart ?? event.target.value.length);
          }}
          onClick={(event) => setCursorPosition((event.target as HTMLTextAreaElement).selectionStart ?? draft.length)}
          onKeyUp={(event) => setCursorPosition((event.target as HTMLTextAreaElement).selectionStart ?? draft.length)}
          onKeyDown={handleTextareaKeyDown}
          placeholder="Draft outreach sequence for $federal_pipeline #need-review /prospect-outreach @orchestration-agent"
          className="fx-field min-h-24 w-full p-3 text-sm"
        />

        {activeMention && mentionSuggestions.length > 0 ? (
          <div className="border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)]">
            <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-[var(--fx-muted)]">
              {activeMention.trigger === "@" ? "Published Agents" : "Published Workflows"}
            </div>
            <ul className="max-h-40 overflow-auto text-xs">
              {mentionSuggestions.map((suggestion, index) => (
                <li key={`${suggestion.trigger}-${suggestion.value}`}>
                  <button
                    type="button"
                    className={`w-full px-2 py-1.5 text-left ${
                      index === activeSuggestionIndex
                        ? "bg-[color-mix(in_srgb,var(--fx-primary)_16%,transparent)] text-[var(--foreground)]"
                        : "hover:bg-[var(--fx-nav-hover)]"
                    }`}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      applyMentionSuggestion(suggestion);
                    }}
                  >
                    <div className="font-mono text-[var(--foreground)]">{suggestion.trigger}{suggestion.value}</div>
                    <div className="fx-muted">{suggestion.label}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2 text-xs">
          {tokens.length === 0 ? (
            <span className="fx-muted">No delimiters detected yet.</span>
          ) : (
            tokens.map((token, index) => (
              <span key={`${token.kind}-${token.value}-${index}`} className={`px-2 py-1 ${tokenClass(token.kind)}`}>
                {token.kind}:{token.value}
              </span>
            ))
          )}
        </div>

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {delimiterLegend.map((item) => (
            <div key={item.symbol} className="border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2 text-xs">
              <p className="font-semibold text-[var(--foreground)]">
                {item.symbol} {item.meaning}
              </p>
              <p className="fx-muted mt-1 font-mono">{item.example}</p>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" disabled={isSubmitting} className="fx-btn-primary px-3 py-2 text-sm font-medium disabled:opacity-60">
            {isSubmitting ? "Starting..." : "Start task"}
          </button>
          {createdRunId ? (
            <Link className="fx-btn-secondary px-3 py-2 text-sm" href={`/runs/${createdRunId}`}>
              Open run
            </Link>
          ) : null}
        </div>

        {submitError ? <p className="text-xs text-[var(--fx-danger)]">{submitError}</p> : null}
      </form>
    </div>
  );
}
