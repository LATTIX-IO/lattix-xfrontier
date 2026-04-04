"use client";

import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactFlowCanvas, type GraphLink, type GraphNode } from "@/components/reactflow-canvas";
import { RunArchiveButton } from "@/components/run-archive-button";
import { RunFollowupComposer } from "@/components/run-followup-composer";
import { StatusChip } from "@/components/status-chip";
import {
  getAtfAlignmentReport,
  getWorkflowRun,
  getWorkflowRunEvents,
  streamWorkflowRun,
  submitApproval,
  type WorkflowRunDetail,
} from "@/lib/api";
import type { AtfAlignmentReport, InboxItem, WorkflowRunEvent, WorkflowRunSummary } from "@/types/frontier";

type UserChatWorkspaceProps = {
  initialRuns: WorkflowRunSummary[];
  initialInbox: InboxItem[];
  initialSelectedRunId: string | null;
  initialDetailsOpen: boolean;
  initialTab: "chat" | "graph";
};

type DrawerTab = "overview" | "artifacts" | "approvals" | "guardrails";

const STOP_WORDS = new Set([
  "about",
  "after",
  "agent",
  "brief",
  "chat",
  "done",
  "draft",
  "email",
  "flow",
  "from",
  "into",
  "need",
  "needs",
  "pack",
  "plan",
  "review",
  "run",
  "step",
  "task",
  "that",
  "this",
  "with",
  "workflow",
]);

function inboxByRunId(items: InboxItem[]): Map<string, InboxItem[]> {
  const mapping = new Map<string, InboxItem[]>();
  for (const item of items) {
    const current = mapping.get(item.runId) ?? [];
    current.push(item);
    mapping.set(item.runId, current);
  }
  return mapping;
}

function orderEvents(events: WorkflowRunEvent[]): WorkflowRunEvent[] {
  return [...events].sort((left, right) => {
    const leftValue = Date.parse(left.createdAt);
    const rightValue = Date.parse(right.createdAt);
    if (Number.isNaN(leftValue) || Number.isNaN(rightValue)) {
      return 0;
    }
    return leftValue - rightValue;
  });
}

function isChatEvent(event: WorkflowRunEvent): boolean {
  return event.type === "user_message" || event.type === "agent_message";
}

function extractTopics(runTitle: string, events: WorkflowRunEvent[]): string[] {
  const counts = new Map<string, number>();
  const combined = [runTitle, ...events.map((event) => `${event.title} ${event.summary}`)].join(" ");
  for (const token of combined.toLowerCase().match(/[a-z0-9][a-z0-9-]{2,}/g) ?? []) {
    if (STOP_WORDS.has(token)) {
      continue;
    }
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([token]) => token.replace(/-/g, " "));
}

function buildExecutionGraph(
  runId: string,
  runTitle: string,
  run: WorkflowRunDetail | null,
  events: WorkflowRunEvent[],
): { nodes: GraphNode[]; links: GraphLink[] } {
  const graphNodes = (run?.graph?.nodes ?? []).filter((node) => node?.id && node?.title && node?.type);
  const graphLinks = (run?.graph?.links ?? []).filter((link) => link?.from && link?.to);

  const baseNodes: GraphNode[] = graphNodes.length > 0
    ? graphNodes.map((node, index) => ({
        ...node,
        x: Number.isFinite(node.x) ? node.x : 120 + index * 280,
        y: Number.isFinite(node.y) ? node.y : 140,
      }))
    : [
        { id: `${runId}-trigger`, title: "Session", type: "frontier/trigger", x: 120, y: 160 },
        { id: `${runId}-chat`, title: runTitle, type: "frontier/agent", x: 420, y: 160 },
        { id: `${runId}-output`, title: "Outcome", type: "frontier/output", x: 720, y: 160 },
      ];

  const baseLinks: GraphLink[] = graphLinks.length > 0
    ? graphLinks
    : [
        { from: `${runId}-trigger`, to: `${runId}-chat` },
        { from: `${runId}-chat`, to: `${runId}-output` },
      ];

  const maxX = Math.max(...baseNodes.map((node) => node.x), 120);
  const topics = extractTopics(runTitle, events);
  const memoryHighlights = events
    .filter((event) => event.type !== "user_message")
    .slice(-3)
    .map((event) => event.title);
  const toolCount = events.filter((event) => event.type === "step_started" || event.type === "step_completed").length;
  const artifactCount = run?.artifacts?.length ?? 0;

  const overlayNodes: GraphNode[] = [
    {
      id: `${runId}-memory`,
      title: `Memory · ${memoryHighlights.length}`,
      type: "frontier/retrieval",
      x: maxX + 320,
      y: 40,
      config: { summary: memoryHighlights.join(", ") || "Session memory" },
    },
    {
      id: `${runId}-tools`,
      title: `Tool Calls · ${toolCount}`,
      type: "frontier/tool-call",
      x: maxX + 320,
      y: 180,
      config: { summary: `${toolCount} execution stages observed` },
    },
    {
      id: `${runId}-topics`,
      title: topics.length > 0 ? `Topics · ${topics.slice(0, 2).join(" / ")}` : "Topics",
      type: "frontier/prompt",
      x: maxX + 320,
      y: 320,
      config: { summary: topics.join(", ") || runTitle },
    },
    {
      id: `${runId}-artifacts`,
      title: `Artifacts · ${artifactCount}`,
      type: "frontier/output",
      x: maxX + 320,
      y: 460,
      config: { summary: (run?.artifacts ?? []).map((artifact) => artifact.name).join(", ") || "No artifacts yet" },
    },
  ];

  const terminalNodeId = baseNodes[baseNodes.length - 1]?.id ?? `${runId}-chat`;
  const overlayLinks: GraphLink[] = [
    { from: terminalNodeId, to: `${runId}-memory` },
    { from: `${runId}-memory`, to: `${runId}-tools` },
    { from: `${runId}-tools`, to: `${runId}-topics` },
    { from: `${runId}-topics`, to: `${runId}-artifacts` },
  ];

  return {
    nodes: [...baseNodes, ...overlayNodes],
    links: [...baseLinks, ...overlayLinks],
  };
}

function ChatBubble({ event }: { event: WorkflowRunEvent }) {
  if (event.type === "user_message") {
    return (
      <div className="flex justify-end">
        <article className="max-w-[82%] rounded-[1.4rem] rounded-br-md bg-[var(--fx-primary)] px-4 py-3 text-[0.94rem] leading-7 text-[#211200] shadow-[0_18px_40px_rgba(215,145,20,0.18)]">
          <p className="mb-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[#5d3b03]">You</p>
          <p className="whitespace-pre-wrap">{event.summary}</p>
        </article>
      </div>
    );
  }

  if (event.type === "agent_message") {
    return (
      <div className="flex justify-start">
        <article className="max-w-[82%] rounded-[1.4rem] rounded-bl-md border border-[var(--ui-border)] bg-[hsl(var(--card)/0.96)] px-4 py-3 text-[0.94rem] leading-7 text-[hsl(var(--foreground))] shadow-[0_18px_48px_rgba(0,0,0,0.12)]">
          <p className="mb-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">Assistant</p>
          <p className="whitespace-pre-wrap">{event.summary}</p>
        </article>
      </div>
    );
  }

  return (
    <div className="flex justify-center">
      <div className="max-w-[78%] rounded-full border border-[var(--ui-border)] bg-[hsl(var(--muted)/0.75)] px-3 py-1.5 text-[0.74rem] text-[var(--fx-muted)]">
        <span className="font-medium text-[hsl(var(--foreground))]">{event.title}</span>
        <span className="mx-1.5">·</span>
        <span>{event.summary}</span>
      </div>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2 rounded-[1.2rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.94)] p-4 shadow-[0_12px_30px_rgba(0,0,0,0.12)]">
      <h3 className="text-[0.78rem] font-semibold uppercase tracking-[0.14em] text-[var(--fx-muted)]">{title}</h3>
      {children}
    </section>
  );
}

export function UserChatWorkspace({
  initialRuns,
  initialInbox,
  initialSelectedRunId,
  initialDetailsOpen,
  initialTab,
}: UserChatWorkspaceProps) {
  const router = useRouter();
  const timelineRef = useRef<HTMLDivElement | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(initialSelectedRunId ?? initialRuns[0]?.id ?? null);
  const [selectedRun, setSelectedRun] = useState<WorkflowRunDetail | null>(null);
  const [events, setEvents] = useState<WorkflowRunEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(initialDetailsOpen);
  const [activeTab, setActiveTab] = useState<"chat" | "graph">(initialTab);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>("overview");
  const [approvalFeedback, setApprovalFeedback] = useState("");
  const [approvalBusy, setApprovalBusy] = useState<"approved" | "changes_requested" | null>(null);
  const [approvalMessage, setApprovalMessage] = useState<string | null>(null);
  const [atfReport, setAtfReport] = useState<AtfAlignmentReport | null>(null);
  const [streamedResponse, setStreamedResponse] = useState("");

  useEffect(() => {
    if (initialSelectedRunId) {
      setSelectedRunId(initialSelectedRunId);
      return;
    }
    if (initialRuns[0]?.id) {
      const nextRunId = initialRuns[0].id;
      setSelectedRunId(nextRunId);
      router.replace(`/inbox?session=${encodeURIComponent(nextRunId)}`, { scroll: false });
    }
  }, [initialRuns, initialSelectedRunId, router]);

  useEffect(() => {
    if (!selectedRunId) {
      setSelectedRun(null);
      setEvents([]);
      setStreamedResponse("");
      return;
    }

    let active = true;
    setLoading(true);
    setStreamedResponse("");

    void Promise.all([getWorkflowRun(selectedRunId), getWorkflowRunEvents(selectedRunId)])
      .then(([runDetail, runEvents]) => {
        if (!active) {
          return;
        }
        setSelectedRun(runDetail);
        setEvents(runEvents);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setSelectedRun(null);
        setEvents([]);
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    const stopStreaming = streamWorkflowRun(selectedRunId, {
      onMessage: (event) => {
        if (event.type === "delta") {
          const text = typeof event.payload.text === "string" ? event.payload.text : "";
          if (text) {
            setStreamedResponse((current: string) => current + text);
          }
          return;
        }
        if (event.type === "final") {
          const text = typeof event.payload.text === "string" ? event.payload.text : "";
          setStreamedResponse(text);
          void Promise.all([getWorkflowRun(selectedRunId), getWorkflowRunEvents(selectedRunId)]).then(
            ([runDetail, runEvents]) => {
              setSelectedRun(runDetail);
              setEvents(runEvents);
            },
          );
          return;
        }
        if (event.type === "complete") {
          setStreamedResponse("");
        }
      },
      onError: () => {
        // Keep the current snapshot; polling refresh can recover on the next selection.
      },
    });

    return () => {
      stopStreaming();
    };
  }, [selectedRunId]);

  useEffect(() => {
    let active = true;

    void getAtfAlignmentReport()
      .then((report) => {
        if (active) {
          setAtfReport(report);
        }
      })
      .catch(() => {
        if (active) {
          setAtfReport(null);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedRunSummary = useMemo(
    () => initialRuns.find((run) => run.id === selectedRunId) ?? initialRuns[0] ?? null,
    [initialRuns, selectedRunId],
  );
  const relatedInboxItems = useMemo(() => {
    if (!selectedRunId) {
      return [];
    }
    return inboxByRunId(initialInbox).get(selectedRunId) ?? [];
  }, [initialInbox, selectedRunId]);
  const ordered = useMemo<WorkflowRunEvent[]>(() => {
    const base = orderEvents(events);
    if (!streamedResponse.trim()) {
      return base;
    }
    const lastEvent = base[base.length - 1];
    if (lastEvent?.type === "agent_message" && lastEvent.summary === streamedResponse) {
      return base;
    }
    const streamingEvent: WorkflowRunEvent = {
      id: "streaming-agent-message",
      type: "agent_message",
      title: "Assistant",
      summary: streamedResponse,
      createdAt: new Date().toISOString(),
    };
    return [
      ...base,
      streamingEvent,
    ];
  }, [events, streamedResponse]);
  const recentContext = useMemo(
    () => ordered.filter(isChatEvent).slice(-6).map((event: WorkflowRunEvent) => `${event.type === "user_message" ? "User" : "Agent"}: ${event.summary}`).join("\n"),
    [ordered],
  );
  const stats = useMemo(() => ({
    chatTurns: ordered.filter(isChatEvent).length,
    systemEvents: ordered.filter((event: WorkflowRunEvent) => !isChatEvent(event)).length,
    blockers: ordered.filter((event: WorkflowRunEvent) => event.type === "error" || /blocked|reject|failed/i.test(`${event.title} ${event.summary}`)).length,
    topics: extractTopics(selectedRunSummary?.title ?? "", ordered),
  }), [ordered, selectedRunSummary?.title]);
  const graph = useMemo(
    () => buildExecutionGraph(selectedRunId ?? "session", selectedRunSummary?.title ?? "Session", selectedRun, ordered),
    [ordered, selectedRun, selectedRunId, selectedRunSummary?.title],
  );
  const approvals = selectedRun?.approvals ?? { required: false, pending: false };
  const guardrailEvents = ordered.filter((event: WorkflowRunEvent) => event.type === "guardrail_result");

  useEffect(() => {
    const timeline = timelineRef.current;
    if (!timeline) {
      return;
    }
    timeline.scrollTop = timeline.scrollHeight;
  }, [ordered]);

  async function handleApproval(decision: "approved" | "changes_requested") {
    if (!selectedRunId || !approvals.required) {
      return;
    }
    if (decision === "changes_requested" && !approvalFeedback.trim()) {
      setApprovalMessage("Add feedback before requesting changes.");
      return;
    }

    setApprovalBusy(decision);
    setApprovalMessage(null);
    try {
      await submitApproval({
        run_id: selectedRunId,
        decision,
        artifact_id: approvals.artifact_id ?? selectedRun?.artifacts[0]?.id ?? "",
        version: approvals.version ?? 1,
        feedback: decision === "changes_requested" ? approvalFeedback.trim() : undefined,
      });
      setApprovalMessage(decision === "approved" ? "Approval submitted." : "Change request submitted.");
      router.refresh();
    } catch {
      setApprovalMessage("Unable to submit decision right now.");
    } finally {
      setApprovalBusy(null);
    }
  }

  if (!selectedRunSummary) {
    return (
      <section className="-m-6 flex min-h-[calc(100vh-130px)] items-center justify-center bg-[radial-gradient(circle_at_top,color-mix(in_srgb,var(--fx-primary)_12%,transparent),transparent_35%)] p-6">
        <div className="max-w-xl text-center">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-[var(--fx-muted)]">Workspace</p>
          <h1 className="mt-4 text-3xl font-semibold text-[hsl(var(--foreground))]">No sessions yet</h1>
          <p className="mt-3 text-[0.95rem] leading-7 text-[var(--fx-muted)]">Start a workflow to create the first conversation thread. Sessions will appear in the sidebar and open here as a chat-first view.</p>
          <div className="mt-6 flex justify-center gap-3">
            <Link href="/workflows/start" className="fx-btn-primary px-4 py-2 text-sm font-medium no-underline">Browse Workflows</Link>
            <Link href="/artifacts" className="fx-btn-secondary px-4 py-2 text-sm font-medium no-underline">View Artifacts</Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="-m-6 min-h-[calc(100vh-96px)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--fx-primary)_8%,transparent),transparent_28%)] p-6">
      <div className="relative flex min-h-[calc(100vh-120px)] flex-col overflow-hidden rounded-[1.8rem] border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--background))_82%,hsl(var(--card))_18%)] shadow-[0_30px_80px_rgba(0,0,0,0.12)]">
        <div className="border-b border-[var(--ui-border)] px-5 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="truncate text-[1.1rem] font-semibold text-[hsl(var(--foreground))]">{selectedRunSummary.title}</p>
                <StatusChip status={selectedRunSummary.status} />
              </div>
              <p className="mt-1 text-[0.82rem] text-[var(--fx-muted)]">Updated {selectedRunSummary.updatedAt} · {selectedRunSummary.progressLabel}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] p-1">
                <button
                  type="button"
                  onClick={() => setActiveTab("chat")}
                  className={activeTab === "chat" ? "rounded-full bg-[var(--fx-primary)] px-3 py-1.5 text-[0.76rem] font-semibold text-[#2f1700]" : "rounded-full px-3 py-1.5 text-[0.76rem] font-medium text-[var(--fx-muted)]"}
                >
                  Chat
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("graph")}
                  className={activeTab === "graph" ? "rounded-full bg-[var(--fx-primary)] px-3 py-1.5 text-[0.76rem] font-semibold text-[#2f1700]" : "rounded-full px-3 py-1.5 text-[0.76rem] font-medium text-[var(--fx-muted)]"}
                >
                  Execution Graph
                </button>
              </div>
              <button type="button" onClick={() => setDetailsOpen((value) => !value)} className="fx-btn-secondary px-3 py-2 text-xs font-medium">
                {detailsOpen ? "Hide details" : "Show details"}
              </button>
              <RunArchiveButton runId={selectedRunSummary.id} buttonClassName="fx-btn-secondary px-3 py-2 text-xs font-medium" />
            </div>
          </div>
        </div>

        <div className="relative flex-1 overflow-hidden">
          <div className="h-full transition-[padding-right] duration-200" style={{ paddingRight: detailsOpen ? "24rem" : "0rem" }}>
            {activeTab === "chat" ? (
              <div className="flex h-full flex-col">
                <div className="grid gap-3 border-b border-[var(--ui-border)] px-5 py-4 md:grid-cols-4">
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Chat Turns</p>
                    <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground))]">{stats.chatTurns}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">System Events</p>
                    <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground))]">{stats.systemEvents}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Inbox Flags</p>
                    <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground))]">{relatedInboxItems.length}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Topics</p>
                    <p className="mt-2 text-[0.92rem] font-medium text-[hsl(var(--foreground))]">{stats.topics.slice(0, 3).join(" · ") || "Waiting for signal"}</p>
                  </div>
                </div>

                <div ref={timelineRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
                  {loading ? (
                    <div className="space-y-3">
                      {[0, 1, 2].map((index) => (
                        <div key={index} className="h-20 animate-pulse rounded-[1.4rem] bg-[hsl(var(--muted)/0.65)]" />
                      ))}
                    </div>
                  ) : ordered.length === 0 ? (
                    <div className="flex h-full min-h-80 items-center justify-center">
                      <div className="max-w-md text-center">
                        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">No messages yet</p>
                        <p className="mt-3 text-[0.95rem] leading-7 text-[var(--fx-muted)]">This session exists, but the timeline is still empty. Use the chat box below to continue the run.</p>
                      </div>
                    </div>
                  ) : (
                    ordered.map((event) => <ChatBubble key={event.id} event={event} />)
                  )}
                </div>

                <div className="border-t border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-5 py-4">
                  <RunFollowupComposer runId={selectedRunSummary.id} recentContext={recentContext} />
                </div>
              </div>
            ) : (
              <div className="flex h-full flex-col px-5 py-5">
                <div className="grid gap-3 md:grid-cols-4">
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Memory</p>
                    <p className="mt-2 text-[0.88rem] font-medium text-[hsl(var(--foreground))]">{ordered.filter((event) => event.type !== "user_message").slice(-3).map((event) => event.title).join(" · ") || "Session context"}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Tool Calls</p>
                    <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground))]">{ordered.filter((event) => event.type === "step_started" || event.type === "step_completed").length}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Topics</p>
                    <p className="mt-2 text-[0.88rem] font-medium text-[hsl(var(--foreground))]">{stats.topics.slice(0, 3).join(" · ") || "No topics yet"}</p>
                  </div>
                  <div className="rounded-[1.1rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.9)] px-3 py-3">
                    <p className="text-[0.72rem] uppercase tracking-[0.12em] text-[var(--fx-muted)]">Artifacts</p>
                    <p className="mt-2 text-2xl font-semibold text-[hsl(var(--foreground))]">{selectedRun?.artifacts.length ?? 0}</p>
                  </div>
                </div>
                <div className="mt-4 min-h-[560px] flex-1 overflow-hidden rounded-[1.4rem] border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)]">
                  <ReactFlowCanvas nodes={graph.nodes} links={graph.links} readOnly className="h-full" edgeAnimated />
                </div>
              </div>
            )}
          </div>

          <aside
            className="absolute inset-y-0 right-0 w-[24rem] border-l border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--card))_96%,hsl(var(--background))_4%)] shadow-[-18px_0_40px_rgba(0,0,0,0.12)] transition-transform duration-200"
            style={{ transform: detailsOpen ? "translateX(0)" : "translateX(100%)" }}
          >
            <div className="flex h-full flex-col">
              <div className="border-b border-[var(--ui-border)] px-4 py-4">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-[0.72rem] font-semibold uppercase tracking-[0.14em] text-[var(--fx-muted)]">Session Details</p>
                    <p className="mt-1 text-sm font-semibold text-[hsl(var(--foreground))]">{selectedRunSummary.title}</p>
                  </div>
                  <button type="button" onClick={() => setDetailsOpen(false)} className="fx-btn-secondary h-8 w-8 px-0 text-xs">X</button>
                </div>
                <div className="mt-3 inline-flex rounded-full border border-[var(--ui-border)] bg-[hsl(var(--card)/0.96)] p-1">
                  {(["overview", "artifacts", "approvals", "guardrails"] as DrawerTab[]).map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setDrawerTab(tab)}
                      className={drawerTab === tab ? "rounded-full bg-[var(--fx-primary)] px-3 py-1 text-[0.7rem] font-semibold text-[#291500]" : "rounded-full px-3 py-1 text-[0.7rem] font-medium text-[var(--fx-muted)]"}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
                {drawerTab === "overview" ? (
                  <>
                    <DetailSection title="Run Overview">
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                          <p className="text-[0.72rem] text-[var(--fx-muted)]">Chat turns</p>
                          <p className="mt-1 font-semibold text-[hsl(var(--foreground))]">{stats.chatTurns}</p>
                        </div>
                        <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                          <p className="text-[0.72rem] text-[var(--fx-muted)]">Blockers</p>
                          <p className="mt-1 font-semibold text-[hsl(var(--foreground))]">{stats.blockers}</p>
                        </div>
                        <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                          <p className="text-[0.72rem] text-[var(--fx-muted)]">Inbox flags</p>
                          <p className="mt-1 font-semibold text-[hsl(var(--foreground))]">{relatedInboxItems.length}</p>
                        </div>
                        <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                          <p className="text-[0.72rem] text-[var(--fx-muted)]">Artifacts</p>
                          <p className="mt-1 font-semibold text-[hsl(var(--foreground))]">{selectedRun?.artifacts.length ?? 0}</p>
                        </div>
                      </div>
                    </DetailSection>

                    <DetailSection title="Inbox Context">
                      {relatedInboxItems.length === 0 ? (
                        <p className="text-sm text-[var(--fx-muted)]">No outstanding inbox items tied to this session.</p>
                      ) : (
                        <div className="space-y-2">
                          {relatedInboxItems.map((item) => (
                            <div key={item.id} className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-3">
                              <p className="text-sm font-medium text-[hsl(var(--foreground))]">{item.artifactType}</p>
                              <p className="mt-1 text-[0.78rem] text-[var(--fx-muted)]">{item.reason}</p>
                              <p className="mt-2 text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">{item.queue}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </DetailSection>

                    <DetailSection title="ATF Posture">
                      {atfReport ? (
                        <div className="space-y-3 text-sm">
                          <div className="grid grid-cols-2 gap-2">
                            <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                              <p className="text-[0.72rem] text-[var(--fx-muted)]">Coverage</p>
                              <p className="mt-1 font-semibold text-[hsl(var(--foreground))]">{Math.round(atfReport.coverage_percent)}%</p>
                            </div>
                            <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-2">
                              <p className="text-[0.72rem] text-[var(--fx-muted)]">Maturity</p>
                              <p className="mt-1 font-semibold capitalize text-[hsl(var(--foreground))]">{atfReport.maturity_estimate}</p>
                            </div>
                          </div>
                          <div className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-3">
                            <p className="text-[0.72rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">Gaps</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {Object.values(atfReport.pillars).flatMap((pillar) => pillar.gaps).slice(0, 4).map((gap) => (
                                <span key={gap} className="rounded-full border border-[var(--ui-border)] px-2 py-1 text-[0.72rem] text-[hsl(var(--foreground))]">{gap}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-[var(--fx-muted)]">ATF posture unavailable.</p>
                      )}
                    </DetailSection>
                  </>
                ) : null}

                {drawerTab === "artifacts" ? (
                  <DetailSection title="Artifacts">
                    {(selectedRun?.artifacts ?? []).length === 0 ? (
                      <p className="text-sm text-[var(--fx-muted)]">No artifacts recorded yet.</p>
                    ) : (
                      <div className="space-y-2">
                        {(selectedRun?.artifacts ?? []).map((artifact) => (
                          <div key={artifact.id} className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-3">
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-sm font-medium text-[hsl(var(--foreground))]">{artifact.name}</p>
                              <span className="text-[0.72rem] text-[var(--fx-muted)]">v{artifact.version}</span>
                            </div>
                            <p className="mt-1 text-[0.78rem] text-[var(--fx-muted)]">{artifact.status}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </DetailSection>
                ) : null}

                {drawerTab === "approvals" ? (
                  <DetailSection title="Approvals">
                    {approvals.required ? (
                      <div className="space-y-3">
                        <p className="text-sm text-[var(--fx-muted)]">
                          {approvals.pending ? "A human decision is required before the run can continue." : "No pending approval decision right now."}
                        </p>
                        <textarea
                          value={approvalFeedback}
                          onChange={(event) => setApprovalFeedback(event.target.value)}
                          placeholder="Leave guidance for the next pass"
                          className="fx-input min-h-28 w-full px-3 py-3 text-sm"
                        />
                        <div className="flex gap-2">
                          <button type="button" onClick={() => void handleApproval("approved")} disabled={approvalBusy !== null} className="fx-btn-success px-3 py-2 text-xs font-medium">
                            {approvalBusy === "approved" ? "Approving…" : "Approve"}
                          </button>
                          <button type="button" onClick={() => void handleApproval("changes_requested")} disabled={approvalBusy !== null} className="fx-btn-warning px-3 py-2 text-xs font-medium">
                            {approvalBusy === "changes_requested" ? "Sending…" : "Request changes"}
                          </button>
                        </div>
                        {approvalMessage ? <p className="text-xs text-[var(--fx-muted)]">{approvalMessage}</p> : null}
                      </div>
                    ) : (
                      <p className="text-sm text-[var(--fx-muted)]">This session does not currently require approval.</p>
                    )}
                  </DetailSection>
                ) : null}

                {drawerTab === "guardrails" ? (
                  <DetailSection title="Guardrails">
                    {guardrailEvents.length === 0 ? (
                      <p className="text-sm text-[var(--fx-muted)]">No guardrail findings for this session.</p>
                    ) : (
                      <div className="space-y-2">
                        {guardrailEvents.map((event) => (
                          <div key={event.id} className="rounded-xl border border-[var(--ui-border)] bg-[hsl(var(--card)/0.92)] px-3 py-3">
                            <p className="text-sm font-medium text-[hsl(var(--foreground))]">{event.title}</p>
                            <p className="mt-1 text-[0.78rem] leading-6 text-[var(--fx-muted)]">{event.summary}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </DetailSection>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
