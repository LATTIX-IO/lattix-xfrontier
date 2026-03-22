"use client";

import { useState } from "react";

type AgentTrace = {
  agent: string;
  reasoningSummary: string;
  actions: string[];
  output: string;
};

type Props = {
  traces: AgentTrace[];
};

export function AgentTraceTabs({ traces }: Props) {
  const [active, setActive] = useState(traces[0]?.agent ?? "");

  if (traces.length === 0) {
    return (
      <div className="fx-panel p-3">
        <p className="fx-muted text-sm">No agent trace entries yet.</p>
      </div>
    );
  }

  const selected = traces.find((t) => t.agent === active) ?? traces[0];

  if (!selected) return null;

  return (
    <div className="fx-panel p-3">
      <div className="mb-3 flex flex-wrap gap-2 border-b border-[var(--fx-border)] pb-2">
        {traces.map((trace) => (
          <button
            key={trace.agent}
            onClick={() => setActive(trace.agent)}
            className={`px-3 py-1 text-xs ${
              trace.agent === selected.agent
                ? "fx-nav-active"
                : "border border-[var(--fx-border)] text-[var(--foreground)] hover:bg-[var(--fx-nav-hover)]"
            }`}
          >
            {trace.agent}
          </button>
        ))}
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="fx-muted mb-1 text-xs uppercase">Reasoning summary</p>
          <p className="text-[var(--foreground)]">{selected.reasoningSummary}</p>
        </div>

        <div>
          <p className="fx-muted mb-1 text-xs uppercase">Actions</p>
          <ul className="list-disc space-y-1 pl-5 text-[var(--foreground)]">
            {selected.actions.map((a, i) => (
              <li key={`${selected.agent}-${i}`}>{a}</li>
            ))}
          </ul>
        </div>

        <div>
          <p className="fx-muted mb-1 text-xs uppercase">Output</p>
          <p className="text-[var(--foreground)]">{selected.output}</p>
        </div>
      </div>
    </div>
  );
}
