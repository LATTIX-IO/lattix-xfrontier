"use client";

import { useMemo, useState } from "react";
import type { WorkflowRunEvent } from "@/types/frontier";

type AgentTrace = {
  agent: string;
  reasoningSummary: string;
  actions: string[];
  output: string;
};

type Props = {
  events: WorkflowRunEvent[];
  traces: AgentTrace[];
};

type Tab = { id: string; label: string; kind: "overview" | "agent" };

export function RunAuditTabs({ events, traces }: Props) {
  const tabs = useMemo<Tab[]>(() => {
    const agentTabs = traces.map((trace) => ({ id: trace.agent, label: trace.agent, kind: "agent" as const }));
    return [{ id: "overview", label: "Overview", kind: "overview" as const }, ...agentTabs];
  }, [traces]);

  const [activeTabId, setActiveTabId] = useState(tabs[0]?.id ?? "overview");

  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0];
  const selectedTrace = traces.find((trace) => trace.agent === activeTab?.id);

  return (
    <div className="fx-panel p-4">
      <div className="mb-3 flex flex-wrap gap-2 border-b border-[var(--fx-border)] pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTabId(tab.id)}
            className={`px-2.5 py-1 text-xs ${
              tab.id === activeTab?.id
                ? "fx-nav-active"
                : "border border-[var(--fx-border)] text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab?.kind === "overview" ? (
        <div className="space-y-3 text-sm">
          <p className="fx-muted text-xs uppercase tracking-wide">Conversation & Audit Log</p>
          <div className="max-h-[280px] space-y-2 overflow-auto pr-1">
            {events.map((event) => (
              <article key={event.id} className="border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
                <div className="mb-1 flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-[var(--foreground)]">{event.title}</h4>
                  <span className="fx-muted text-[11px]">{event.createdAt}</span>
                </div>
                <p className="text-xs text-[var(--foreground)]">{event.summary}</p>
                <p className="fx-muted mt-1 text-[10px] uppercase tracking-wide">{event.type}</p>
              </article>
            ))}
          </div>
        </div>
      ) : selectedTrace ? (
        <div className="space-y-3 text-sm">
          <div>
            <p className="fx-muted mb-1 text-xs uppercase">Reasoning summary</p>
            <p className="text-[var(--foreground)]">{selectedTrace.reasoningSummary}</p>
          </div>

          <div>
            <p className="fx-muted mb-1 text-xs uppercase">Actions</p>
            <ul className="list-disc space-y-1 pl-5 text-[var(--foreground)]">
              {selectedTrace.actions.map((action, index) => (
                <li key={`${selectedTrace.agent}-${index}`}>{action}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="fx-muted mb-1 text-xs uppercase">Output</p>
            <p className="text-[var(--foreground)]">{selectedTrace.output}</p>
          </div>
        </div>
      ) : (
        <p className="fx-muted text-sm">No trace details found for this tab.</p>
      )}
    </div>
  );
}
