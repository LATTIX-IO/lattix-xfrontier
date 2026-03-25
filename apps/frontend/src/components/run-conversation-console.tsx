"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";

const ReactMarkdown = dynamic(() => import("react-markdown"), { ssr: false });
import remarkGfm from "remark-gfm";
import { ReactFlowCanvas } from "@/components/reactflow-canvas";
import { RunArchiveButton } from "@/components/run-archive-button";
import { RunFollowupComposer } from "@/components/run-followup-composer";
import { getAtfAlignmentReport, submitApproval, type WorkflowRunDetail } from "@/lib/api";
import type { AtfAlignmentReport, WorkflowRunEvent } from "@/types/frontier";

type Props = {
  runId: string;
  run: WorkflowRunDetail;
  events: WorkflowRunEvent[];
};

type EventFilter = "all" | "chat" | "system" | "errors";
type RightPanelTab = "graph" | "artifacts" | "approvals" | "guardrails";

function normalizeComparableText(value: string): string {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function matchesEventFilter(event: WorkflowRunEvent, filter: EventFilter): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "chat") {
    return event.type === "user_message" || event.type === "agent_message";
  }
  if (filter === "errors") {
    return event.type === "error" || /error|failed|blocked|reject/i.test(`${event.title} ${event.summary}`);
  }
  return event.type !== "user_message" && event.type !== "agent_message";
}

function MarkdownBlock({ content, className = "" }: { content: string; className?: string }) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0 text-xs leading-relaxed text-[var(--foreground)]">{children}</p>,
          ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-4 text-xs text-[var(--foreground)]">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-4 text-xs text-[var(--foreground)]">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          code: ({ children }) => (
            <code className="rounded bg-[hsl(var(--muted)/0.65)] px-1 py-0.5 font-mono text-[11px] text-[var(--foreground)]">{children}</code>
          ),
          pre: ({ children }) => (
            <pre className="mb-2 overflow-auto rounded-md border border-[var(--ui-border)] bg-[hsl(var(--muted)/0.5)] p-2 text-[11px] text-[var(--foreground)]">{children}</pre>
          ),
          h1: ({ children }) => <h4 className="mb-1 mt-2 text-sm font-semibold text-[var(--foreground)]">{children}</h4>,
          h2: ({ children }) => <h4 className="mb-1 mt-2 text-sm font-semibold text-[var(--foreground)]">{children}</h4>,
          h3: ({ children }) => <h5 className="mb-1 mt-2 text-xs font-semibold text-[var(--foreground)]">{children}</h5>,
          blockquote: ({ children }) => (
            <blockquote className="mb-2 border-l-2 border-[var(--ui-border)] pl-2 text-xs text-[hsl(var(--muted-foreground))]">{children}</blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function statusColorForRun(status: string): string {
  if (status === "Done") {
    return "hsl(var(--state-success))";
  }
  if (status === "Failed") {
    return "hsl(var(--state-critical))";
  }
  if (status === "Needs Review") {
    return "hsl(var(--state-warning))";
  }
  return "hsl(var(--state-info))";
}

export function RunConversationConsole({ runId, run, events }: Props) {
  const router = useRouter();
  const timelineRef = useRef<HTMLDivElement | null>(null);

  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>("graph");
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandAllReasoning, setExpandAllReasoning] = useState(false);
  const [approvalFeedback, setApprovalFeedback] = useState("");
  const [approvalBusy, setApprovalBusy] = useState<"approved" | "changes_requested" | null>(null);
  const [approvalMessage, setApprovalMessage] = useState<string | null>(null);
  const [atfReport, setAtfReport] = useState<AtfAlignmentReport | null>(null);
  const [atfReportError, setAtfReportError] = useState<string | null>(null);

  const rawGraphNodes = Array.isArray(run.graph?.nodes) ? run.graph.nodes : [];
  const graphNodes = rawGraphNodes
    .filter((node): node is { id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> } => {
      return Boolean(node && String(node.id || "").trim() && String(node.title || "").trim() && String(node.type || "").trim());
    })
    .map((node, index) => {
      const hasValidX = Number.isFinite(node.x);
      const hasValidY = Number.isFinite(node.y);
      return {
        ...node,
        x: hasValidX ? node.x : 80 + index * 280,
        y: hasValidY ? node.y : 140,
      };
    });

  const graphNodeIds = new Set(graphNodes.map((node) => node.id));
  const rawGraphLinks = Array.isArray(run.graph?.links) ? run.graph.links : [];
  const graphLinks = rawGraphLinks.filter((link) => Boolean(link && graphNodeIds.has(link.from) && graphNodeIds.has(link.to)));

  const fallbackGraphNodes = [
    { id: "n-trigger", title: "Trigger", type: "trigger" as const, x: 80, y: 140 },
    { id: "n-default-chat-agent", title: "Default Chat Agent", type: "agent" as const, x: 360, y: 140 },
    { id: "n-output", title: "Output", type: "output" as const, x: 680, y: 140 },
  ];
  const fallbackGraphLinks = [
    { from: "n-trigger", to: "n-default-chat-agent", from_port: "out", to_port: "in" },
    { from: "n-default-chat-agent", to: "n-output", from_port: "out", to_port: "in" },
  ];

  const effectiveGraphNodes = graphNodes.length > 0 ? graphNodes : fallbackGraphNodes;
  const effectiveGraphLinks = graphNodes.length > 0 ? graphLinks : fallbackGraphLinks;

  const agentTraces = run.agent_traces ?? [];
  const tracesByAgent = new Map(agentTraces.map((trace) => [trace.agent, trace]));
  const approvals = run.approvals ?? { required: false, pending: false };
  const approvalArtifactId = approvals.artifact_id ?? run.artifacts[0]?.id ?? "";
  const approvalVersion = approvals.version ?? 1;

  const orderedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      const left = Date.parse(a.createdAt);
      const right = Date.parse(b.createdAt);
      if (Number.isNaN(left) || Number.isNaN(right)) {
        return 0;
      }
      return left - right;
    });
  }, [events]);

  let lastUserIndex = -1;
  let lastAgentIndex = -1;
  orderedEvents.forEach((event, index) => {
    if (event.type === "user_message") {
      lastUserIndex = index;
    }
    if (event.type === "agent_message") {
      lastAgentIndex = index;
    }
  });

  const showTypingPlaceholder = run.status === "Running" && lastUserIndex > lastAgentIndex;

  const recentContext = useMemo(() => {
    return orderedEvents
      .filter((event) => event.type === "user_message" || event.type === "agent_message")
      .slice(-6)
      .map((event) => `${event.type === "user_message" ? "User" : "Agent"}: ${event.summary}`)
      .join("\n");
  }, [orderedEvents]);

  const filteredEvents = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return orderedEvents.filter((event) => {
      if (!matchesEventFilter(event, eventFilter)) {
        return false;
      }
      if (!query) {
        return true;
      }
      return `${event.type} ${event.title} ${event.summary}`.toLowerCase().includes(query);
    });
  }, [eventFilter, orderedEvents, searchQuery]);

  const chatEventsCount = orderedEvents.filter((event) => event.type === "user_message" || event.type === "agent_message").length;
  const systemEventsCount = orderedEvents.length - chatEventsCount;
  const errorEventsCount = orderedEvents.filter((event) => matchesEventFilter(event, "errors")).length;

  const hasAgentNode = effectiveGraphNodes.some((node) => {
    const normalized = String(node.type || "").replace(/^frontier\//, "");
    return normalized === "agent" || normalized.startsWith("agent/");
  });
  const usedAgentStudioAgent = hasAgentNode || agentTraces.length > 0;

  const guardrailEvents = orderedEvents.filter((event) => event.type === "guardrail_result");

  useEffect(() => {
    if (approvals.required && approvals.pending) {
      setRightPanelTab("approvals");
    }
  }, [approvals.pending, approvals.required]);

  useEffect(() => {
    let active = true;
    setAtfReportError(null);

    void getAtfAlignmentReport()
      .then((report) => {
        if (!active) {
          return;
        }
        setAtfReport(report);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setAtfReportError("Unable to load ATF posture.");
      });

    return () => {
      active = false;
    };
  }, [runId]);

  useEffect(() => {
    if (!autoScroll) {
      return;
    }
    const timeline = timelineRef.current;
    if (!timeline) {
      return;
    }
    timeline.scrollTop = timeline.scrollHeight;
  }, [autoScroll, filteredEvents.length, showTypingPlaceholder]);

  async function copyTranscript() {
    const transcript = filteredEvents
      .map((event) => `[${event.createdAt}] ${event.type}: ${event.title}\n${event.summary}`)
      .join("\n\n");

    if (!transcript.trim()) {
      setApprovalMessage("No timeline content available to copy.");
      return;
    }

    if (typeof navigator === "undefined" || !navigator.clipboard) {
      setApprovalMessage("Clipboard access is unavailable in this environment.");
      return;
    }

    try {
      await navigator.clipboard.writeText(transcript);
      setApprovalMessage("Timeline copied to clipboard.");
    } catch {
      setApprovalMessage("Unable to copy timeline on this browser/session.");
    }
  }

  async function handleApprovalDecision(decision: "approved" | "changes_requested") {
    if (!approvals.required) {
      return;
    }

    const feedback = approvalFeedback.trim();
    if (decision === "changes_requested" && !feedback) {
      setApprovalMessage("Please provide feedback before requesting changes.");
      return;
    }

    setApprovalBusy(decision);
    setApprovalMessage(null);

    try {
      await submitApproval({
        run_id: runId,
        decision,
        artifact_id: approvalArtifactId,
        version: approvalVersion,
        feedback: decision === "changes_requested" ? feedback : undefined,
      });
      setApprovalMessage(decision === "approved" ? "Approval submitted." : "Change request submitted.");
      router.refresh();
    } catch {
      setApprovalMessage("Unable to submit approval decision. Please retry.");
    } finally {
      setApprovalBusy(null);
    }
  }

  const statusColor = statusColorForRun(run.status);
  const atfTopGaps = atfReport
    ? Object.values(atfReport.pillars)
        .flatMap((pillar) => pillar.gaps)
        .filter(Boolean)
        .slice(0, 3)
    : [];

  return (
    <div className="-m-6 min-h-[calc(100vh-57px)] p-6">
      <section className="space-y-4">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">Run Console</h1>
            <p className="fx-muted text-sm">
              Review execution, triage issues, and continue the run for <span className="font-mono">{runId}</span>.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 font-medium" style={{ color: statusColor }}>
              {run.status}
            </span>
            <span className="rounded-full border border-[var(--ui-border)] px-2 py-1 text-[var(--foreground)]">{orderedEvents.length} events</span>
            <span className="rounded-full border border-[var(--ui-border)] px-2 py-1 text-[var(--foreground)]">{agentTraces.length} trace(s)</span>
            <span className="rounded-full border border-[var(--ui-border)] px-2 py-1 text-[var(--foreground)]">{run.artifacts.length} artifact(s)</span>
            <button onClick={() => router.refresh()} className="fx-btn-secondary px-2 py-1 text-xs font-medium" type="button">
              Refresh
            </button>
            <RunArchiveButton runId={runId} buttonClassName="fx-btn-secondary px-2 py-1 text-xs font-medium" />
          </div>
        </header>

        <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
          <div className="fx-panel px-3 py-2">
            <p className="fx-muted">Chat turns</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{chatEventsCount}</p>
          </div>
          <div className="fx-panel px-3 py-2">
            <p className="fx-muted">System events</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{systemEventsCount}</p>
          </div>
          <div className="fx-panel px-3 py-2">
            <p className="fx-muted">Errors / blockers</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{errorEventsCount}</p>
          </div>
          <div className="fx-panel px-3 py-2">
            <p className="fx-muted">Graph mode</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{usedAgentStudioAgent ? "Agent-mediated" : "Fallback view"}</p>
          </div>
        </div>

        <div className="fx-panel p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-[var(--foreground)]">ATF posture at execution time</h2>
            <span className="fx-muted text-[11px]">CSA Agentic Trust Framework</span>
          </div>
          {atfReport ? (
            <>
              <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-2 py-1.5">
                  <p className="fx-muted">Coverage</p>
                  <p className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">{Math.round(atfReport.coverage_percent)}%</p>
                </div>
                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-2 py-1.5">
                  <p className="fx-muted">Maturity</p>
                  <p className="mt-0.5 text-sm font-semibold capitalize text-[var(--foreground)]">{atfReport.maturity_estimate}</p>
                </div>
                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-2 py-1.5">
                  <p className="fx-muted">Blocked (24h)</p>
                  <p className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">{atfReport.evidence.audit_blocked_24h}</p>
                </div>
                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-2 py-1.5">
                  <p className="fx-muted">Errors (24h)</p>
                  <p className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">{atfReport.evidence.audit_error_24h}</p>
                </div>
              </div>

              <div className="mt-2 rounded-md border border-[var(--ui-border)] bg-[hsl(var(--muted)/0.24)] p-2">
                <p className="fx-muted text-[11px] uppercase tracking-wide">Top current gaps</p>
                {atfTopGaps.length > 0 ? (
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs leading-relaxed text-[var(--foreground)]">
                    {atfTopGaps.map((gap, index) => (
                      <li key={`atf-gap-${index}`}>{gap}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-xs text-[var(--foreground)]">No major gaps currently flagged.</p>
                )}
              </div>
            </>
          ) : (
            <p className="mt-2 text-xs text-[hsl(var(--muted-foreground))]">{atfReportError ?? "Loading ATF posture..."}</p>
          )}
        </div>

        <div className="grid min-h-[72vh] grid-cols-1 gap-3 xl:grid-cols-[1.08fr_1.42fr]">
          <section className="fx-panel flex min-h-0 flex-col overflow-hidden p-0">
            <div className="border-b border-[var(--ui-border)] px-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold">Timeline</h2>
                <div className="flex items-center gap-1.5 text-xs">
                  <button type="button" onClick={() => setExpandAllReasoning((prev) => !prev)} className="fx-btn-secondary px-2 py-1 text-[11px]">
                    {expandAllReasoning ? "Collapse reasoning" : "Expand reasoning"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const timeline = timelineRef.current;
                      if (timeline) {
                        timeline.scrollTop = timeline.scrollHeight;
                      }
                    }}
                    className="fx-btn-secondary px-2 py-1 text-[11px]"
                  >
                    Jump latest
                  </button>
                  <button type="button" onClick={copyTranscript} className="fx-btn-secondary px-2 py-1 text-[11px]">
                    Copy timeline
                  </button>
                </div>
              </div>

              <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search timeline (events, summaries, errors)..."
                  className="fx-field h-8 px-2 text-xs"
                />
                <div className="flex items-center gap-1 rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card))] p-1">
                  {(["all", "chat", "system", "errors"] as EventFilter[]).map((filterOption) => (
                    <button
                      key={filterOption}
                      type="button"
                      onClick={() => setEventFilter(filterOption)}
                      className={`rounded px-2 py-1 text-[11px] ${eventFilter === filterOption ? "bg-[hsl(var(--primary)/0.18)] text-[var(--foreground)]" : "text-[hsl(var(--muted-foreground))]"}`}
                    >
                      {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-1 rounded-md border border-[var(--ui-border)] px-2 text-[11px] text-[hsl(var(--muted-foreground))]">
                  <input type="checkbox" checked={autoScroll} onChange={(event) => setAutoScroll(event.target.checked)} />
                  Auto-scroll
                </label>
              </div>
            </div>

            <div ref={timelineRef} className="min-h-0 flex-1 space-y-4 overflow-auto bg-[hsl(var(--muted)/0.25)] px-3 py-4">
              {filteredEvents.length === 0 ? (
                <div className="mx-auto w-full max-w-[880px] rounded-xl border border-dashed border-[var(--ui-border)] bg-[hsl(var(--card)/0.8)] px-3 py-4 text-xs">
                  <p className="font-medium text-[var(--foreground)]">No events match your current filters.</p>
                  <p className="fx-muted mt-1">Try clearing search or switching from <span className="font-semibold">{eventFilter}</span> to <span className="font-semibold">all</span>.</p>
                </div>
              ) : (
                filteredEvents.map((event) => {
                  const trace = event.type === "agent_message" ? tracesByAgent.get(event.title.replace(/\s+response$/i, "")) : undefined;
                  const eventModelMeta =
                    event.metadata && typeof event.metadata === "object" && typeof event.metadata.model === "object"
                      ? (event.metadata.model as Record<string, unknown>)
                      : null;
                  const eventReasoningMeta =
                    eventModelMeta && typeof eventModelMeta.reasoning === "object"
                      ? (eventModelMeta.reasoning as Record<string, unknown>)
                      : null;
                  const reasoningSummaries =
                    eventReasoningMeta && Array.isArray(eventReasoningMeta.summaries)
                      ? eventReasoningMeta.summaries.map((item) => String(item ?? "").trim()).filter(Boolean)
                      : [];

                  const showTraceOutput =
                    Boolean(trace?.output?.trim()) &&
                    normalizeComparableText(trace?.output ?? "") !== normalizeComparableText(event.summary);

                  const isUserMessage = event.type === "user_message";
                  const isAgentMessage = event.type === "agent_message";
                  const isChatTurn = isUserMessage || isAgentMessage;

                  if (!isChatTurn) {
                    return (
                      <article key={event.id} className="group mx-auto w-full max-w-[880px] rounded-lg border border-[var(--ui-border)] bg-[hsl(var(--card)/0.72)] px-3 py-2">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                            {event.type.replace(/_/g, " ")}
                          </p>
                          <span className="fx-muted text-[11px] opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">{event.createdAt}</span>
                        </div>
                        <p className="mb-1 text-xs font-medium text-[var(--foreground)]">{event.title}</p>
                        <MarkdownBlock content={event.summary} />
                      </article>
                    );
                  }

                  const roleLabel = isUserMessage ? "You" : (trace?.agent || "Assistant");
                  const containerClass = isUserMessage ? "justify-end" : "justify-start";
                  const bubbleClass = isUserMessage
                    ? "border-[hsl(var(--primary)/0.45)] bg-[hsl(var(--primary)/0.16)]"
                    : "border-[var(--ui-border)] bg-[hsl(var(--card)/0.98)]";

                  return (
                    <article key={event.id} className={`group mx-auto flex w-full max-w-[880px] ${containerClass}`}>
                      <div className={`w-full max-w-[760px] rounded-2xl border px-3 py-2.5 shadow-sm ${bubbleClass}`}>
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <p className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">{roleLabel}</p>
                          <span className="fx-muted text-[11px] opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">{event.createdAt}</span>
                        </div>
                        <MarkdownBlock content={event.summary} className="mt-1" />

                        {trace ? (
                          <details open={expandAllReasoning} className="mt-2 rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--muted)/0.32)] px-2 py-1.5">
                            <summary className="cursor-pointer list-none text-[11px] font-medium text-[hsl(var(--muted-foreground))]">Reasoning</summary>

                            <div className="mt-2 space-y-2">
                              <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.8)] p-2">
                                <p className="fx-muted text-[10px] uppercase tracking-wide">Summary</p>
                                <MarkdownBlock content={trace.reasoningSummary} className="mt-1" />
                              </div>

                              {reasoningSummaries.length > 0 ? (
                                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.8)] p-2">
                                  <p className="fx-muted text-[10px] uppercase tracking-wide">Model reasoning highlights (auto)</p>
                                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[var(--foreground)]">
                                    {reasoningSummaries.map((item, index) => (
                                      <li key={`${event.id}-reasoning-${index}`}>{item}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}

                              {trace.actions.length > 0 ? (
                                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.8)] p-2">
                                  <p className="fx-muted text-[10px] uppercase tracking-wide">Actions</p>
                                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[var(--foreground)]">
                                    {trace.actions.map((action, index) => (
                                      <li key={`${trace.agent}-${index}`}>{action}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}

                              {showTraceOutput ? (
                                <div className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.8)] p-2">
                                  <p className="fx-muted text-[10px] uppercase tracking-wide">Full output</p>
                                  <MarkdownBlock content={trace.output} className="mt-1" />
                                </div>
                              ) : null}
                            </div>
                          </details>
                        ) : null}
                      </div>
                    </article>
                  );
                })
              )}

              {showTypingPlaceholder ? (
                <article className="mx-auto flex w-full max-w-[880px] justify-start">
                  <div className="w-full max-w-[760px] rounded-2xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.98)] px-3 py-2.5 shadow-sm">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">Assistant</p>
                      <span className="fx-muted text-[11px]">streaming</span>
                    </div>
                    <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--ui-border)] bg-[hsl(var(--muted)/0.45)] px-2 py-1">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[hsl(var(--muted-foreground))] [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[hsl(var(--muted-foreground))] [animation-delay:120ms]" />
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[hsl(var(--muted-foreground))] [animation-delay:240ms]" />
                      <span className="ml-1 text-xs text-[hsl(var(--muted-foreground))]">Thinking…</span>
                    </div>
                  </div>
                </article>
              ) : null}
            </div>

            <div className="sticky bottom-0 border-t border-[var(--ui-border)] bg-[hsl(var(--background)/0.86)] px-3 py-3 shadow-[0_-8px_24px_rgba(0,0,0,0.08)] backdrop-blur-md">
              <RunFollowupComposer runId={runId} recentContext={recentContext} />
            </div>
          </section>

          <section className="min-h-0 space-y-3">
            <div className="fx-panel p-2">
              <div className="mb-2 flex items-center gap-1 rounded-lg border border-[var(--ui-border)] bg-[hsl(var(--card))] p-1 text-xs">
                {([
                  ["graph", "Execution Graph"],
                  ["artifacts", "Artifacts"],
                  ["approvals", "Approvals"],
                  ["guardrails", "Guardrails"],
                ] as const).map(([tabKey, label]) => (
                  <button
                    key={tabKey}
                    type="button"
                    onClick={() => setRightPanelTab(tabKey)}
                    className={`rounded px-2 py-1 ${rightPanelTab === tabKey ? "bg-[hsl(var(--primary)/0.18)] text-[var(--foreground)]" : "text-[hsl(var(--muted-foreground))]"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {rightPanelTab === "graph" ? (
                <div>
                  <div className="mb-2 flex items-center justify-between px-2 text-xs">
                    <h2 className="font-semibold">Execution Graph</h2>
                    <span className="fx-muted">
                      {usedAgentStudioAgent ? "Read-only snapshot • draggable nodes" : "Default chat agent fallback shown"}
                    </span>
                  </div>
                  <ReactFlowCanvas nodes={effectiveGraphNodes} links={effectiveGraphLinks} height={560} readOnly />
                </div>
              ) : null}

              {rightPanelTab === "artifacts" ? (
                <div className="p-2">
                  <h3 className="mb-2 text-sm font-semibold">Artifacts</h3>
                  {run.artifacts.length === 0 ? (
                    <p className="fx-muted text-xs">No artifact was captured for this run.</p>
                  ) : (
                    <ul className="space-y-1.5 text-xs text-[var(--foreground)]">
                      {run.artifacts.map((artifact) => (
                        <li key={artifact.id} className="flex items-center justify-between gap-2 border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] px-2 py-1.5">
                          <div className="min-w-0">
                            <p className="truncate font-medium text-[var(--foreground)]">{artifact.name}</p>
                            <p className="fx-muted truncate">{artifact.status} • v{artifact.version}</p>
                          </div>
                          <Link href={`/artifacts/${artifact.id}`} className="fx-btn-secondary shrink-0 px-2 py-1 text-[11px] font-medium">
                            Open
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}

              {rightPanelTab === "approvals" ? (
                <div className="p-2">
                  <h3 className="mb-2 text-sm font-semibold">Approvals</h3>
                  <div className="mb-2 border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2 text-xs">
                    <p className="font-semibold text-[var(--foreground)]">Pending approval target</p>
                    {approvals.required ? (
                      <p className="fx-muted mt-1">
                        Artifact: {approvalArtifactId || "(n/a)"} • Version: v{approvalVersion} • Scope: {approvals.scope ?? "final send/export"}
                      </p>
                    ) : (
                      <p className="fx-muted mt-1">No approval required for this run.</p>
                    )}
                  </div>

                  {approvals.required ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <button
                          type="button"
                          disabled={approvalBusy !== null}
                          onClick={() => handleApprovalDecision("approved")}
                          className="fx-btn-success px-2 py-1.5 text-xs font-medium disabled:opacity-60"
                        >
                          {approvalBusy === "approved" ? "Submitting..." : "Approve"}
                        </button>
                        <button
                          type="button"
                          disabled={approvalBusy !== null}
                          onClick={() => handleApprovalDecision("changes_requested")}
                          className="fx-btn-secondary px-2 py-1.5 text-xs font-medium disabled:opacity-60"
                        >
                          {approvalBusy === "changes_requested" ? "Submitting..." : "Request edits"}
                        </button>
                      </div>

                      <form
                        onSubmit={(event: FormEvent) => {
                          event.preventDefault();
                          void handleApprovalDecision("changes_requested");
                        }}
                        className="space-y-1.5"
                      >
                        <label htmlFor="approval-feedback" className="fx-muted block text-[11px] uppercase tracking-wide">
                          Feedback / requested edits
                        </label>
                        <textarea
                          id="approval-feedback"
                          name="feedback"
                          value={approvalFeedback}
                          onChange={(event) => setApprovalFeedback(event.target.value)}
                          placeholder="Describe what to change before approval..."
                          className="fx-field min-h-20 w-full p-2 text-xs"
                        />
                      </form>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {rightPanelTab === "guardrails" ? (
                <div className="p-2">
                  <h3 className="mb-2 text-sm font-semibold">Guardrails</h3>
                  {guardrailEvents.length === 0 ? (
                    <p className="fx-muted text-xs">No guardrail findings were emitted for this run.</p>
                  ) : (
                    <ul className="space-y-2">
                      {guardrailEvents.map((event) => (
                        <li key={event.id} className="rounded-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] p-2">
                          <p className="text-xs font-semibold text-[var(--foreground)]">{event.title}</p>
                          <p className="fx-muted mt-0.5 text-[11px]">{event.createdAt}</p>
                          <MarkdownBlock content={event.summary} className="mt-1" />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}
            </div>

            {approvalMessage ? (
              <div className="fx-panel px-3 py-2 text-xs text-[var(--foreground)]">
                {approvalMessage}
              </div>
            ) : null}
          </section>
        </div>
      </section>
    </div>
  );
}
