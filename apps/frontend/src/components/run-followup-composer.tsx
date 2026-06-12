"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getAgentDefinitions, getPublishedWorkflows, sendRunMessage } from "@/lib/api";
import type { AgentDefinition, WorkflowDefinition } from "@/types/frontier";

type MentionSuggestion = {
  trigger: "@" | "/";
  value: string;
  label: string;
};

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
};

export function RunFollowupComposer({ runId }: Props) {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [draft, setDraft] = useState("");
  const [cursorPosition, setCursorPosition] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [publishedAgents, setPublishedAgents] = useState<AgentDefinition[]>([]);
  const [publishedWorkflows, setPublishedWorkflows] = useState<WorkflowDefinition[]>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [submitError, setSubmitError] = useState<string | null>(null);

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
    // Ctrl+Enter (or Cmd+Enter) sends; a plain Enter inserts a newline.
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submitMessage();
      return;
    }

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

  async function submitMessage() {
    const message = draft.trim();
    if (!message || isSubmitting) {
      return;
    }
    setSubmitError(null);

    try {
      setIsSubmitting(true);
      // Sends into THIS run's conversation; the live event stream renders the
      // user message and the agent's reply in place.
      await sendRunMessage(runId, message);
      setDraft("");
      window.dispatchEvent(new CustomEvent("frontier:runs-changed"));
      router.refresh();
      requestAnimationFrame(() => textareaRef.current?.focus());
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "Unable to send the message.";
      setSubmitError(messageText);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitMessage();
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
          Ctrl+Enter to send · Enter for a new line · @agent to address an agent
        </p>
        <button type="submit" disabled={isSubmitting} className="fx-btn-primary rounded-xl px-3 py-2 text-xs font-medium disabled:opacity-60">
          {isSubmitting ? "Sending…" : "Send"}
        </button>
      </div>

      {submitError ? <p className="text-xs text-[var(--fx-danger)]">{submitError}</p> : null}
    </form>
  );
}
