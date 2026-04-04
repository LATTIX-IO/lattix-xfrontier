"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
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

type Props = {
  runId: string;
  recentContext: string;
};

export function RunFollowupComposer({ runId, recentContext }: Props) {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [draft, setDraft] = useState("");
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [publishedAgents, setPublishedAgents] = useState<AgentDefinition[]>([]);
  const [publishedWorkflows, setPublishedWorkflows] = useState<WorkflowDefinition[]>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitInfo, setSubmitInfo] = useState<string | null>(null);
  const [createdRunId, setCreatedRunId] = useState<string | null>(null);

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message) {
      return;
    }
    setSubmitError(null);
    setSubmitInfo(null);
    setCreatedRunId(null);

    const parsedTokens = parseTokens(message);
    const publishedAgentSlugs = new Set(publishedAgents.map((agent) => slugify(agent.name) || slugify(agent.id)));
    const publishedWorkflowSlugs = new Set(publishedWorkflows.map((workflow) => slugify(workflow.name) || slugify(workflow.id)));

    const filteredTokens = parsedTokens.filter((token) => {
      if (token.kind === "agent") {
        return publishedAgentSlugs.has(token.value);
      }
      if (token.kind === "workflow") {
        return publishedWorkflowSlugs.has(token.value);
      }
      return true;
    });

    const contextualPrompt = recentContext
      ? `Previous run context (${runId}):\n${recentContext}\n\nFollow-up request:\n${message}`
      : message;

    const titleSnippet = message.length > 64 ? `${message.slice(0, 61)}...` : message;

    try {
      setIsSubmitting(true);
      const nextRun = await createWorkflowRun({
        title: `Follow-up: ${titleSnippet}`,
        prompt: contextualPrompt,
        tokens: filteredTokens,
        context: {
          source_run_id: runId,
          mode: "follow_up",
        },
        source_run_id: runId,
        follow_up_to_run_id: runId,
      }, {
        timeoutMs: 120000,
      });

      setCreatedRunId(nextRun.id);
      if (nextRun.id === runId) {
        setSubmitInfo("Follow-up sent. Refreshing this run timeline...");
        router.refresh();
      } else {
        setSubmitInfo(`Follow-up sent. Opening run ${nextRun.id}...`);
        router.push(`/inbox?session=${encodeURIComponent(nextRun.id)}`);
        router.refresh();
      }
      setDraft("");
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "Unable to start follow-up run.";
      setSubmitError(`${messageText} If the run is still processing, wait a few seconds and try again.`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor="continue-message" className="sr-only">
        Message this run
      </label>
      <textarea
        ref={textareaRef}
        id="continue-message"
        name="message"
        required
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
          setCursorPosition(event.target.selectionStart ?? event.target.value.length);
        }}
        onClick={(event) => setCursorPosition((event.target as HTMLTextAreaElement).selectionStart ?? draft.length)}
        onKeyUp={(event) => setCursorPosition((event.target as HTMLTextAreaElement).selectionStart ?? draft.length)}
        onKeyDown={handleTextareaKeyDown}
        placeholder="Message this run… (use @agent or /workflow)"
        className="fx-field min-h-24 w-full rounded-2xl border-[var(--ui-border)] bg-[hsl(var(--card))] p-3 text-sm leading-relaxed"
      />

      {activeMention && mentionSuggestions.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-[var(--ui-border)] bg-[hsl(var(--card))] shadow-lg">
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
                      ? "bg-[hsl(var(--primary)/0.15)] text-[var(--foreground)]"
                      : "hover:bg-[var(--fx-nav-hover)]"
                  }`}
                  onMouseDown={(mouseEvent) => {
                    mouseEvent.preventDefault();
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

      <div className="flex items-center justify-between gap-2">
        <p className="fx-muted text-[11px]">
          Published @agents and /workflows are supported. Without either, this routes through the default chat agent.
        </p>
        <button type="submit" disabled={isSubmitting} className="fx-btn-primary rounded-xl px-3 py-2 text-xs font-medium disabled:opacity-60">
          {isSubmitting ? "Sending…" : "Send"}
        </button>
      </div>

      {submitInfo ? <p className="text-xs text-[hsl(var(--state-success))]">{submitInfo}</p> : null}
      {createdRunId ? (
        <p className="text-xs text-[var(--foreground)]">
          Run created: <Link href={`/inbox?session=${encodeURIComponent(createdRunId)}`} className="underline decoration-dotted underline-offset-2">{createdRunId}</Link>
        </p>
      ) : null}
      {submitError ? <p className="text-xs text-[var(--fx-danger)]">{submitError}</p> : null}
    </form>
  );
}
