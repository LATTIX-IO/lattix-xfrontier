import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RunConversationConsole } from "@/components/run-conversation-console";

const routerRefreshMock = vi.fn();

const {
  getAtfAlignmentReportMock,
  submitApprovalMock,
} = vi.hoisted(() => ({
  getAtfAlignmentReportMock: vi.fn(async () => ({
    generated_at: new Date().toISOString(),
    framework: "CSA Agentic Trust Framework",
    coverage_percent: 87,
    maturity_estimate: "senior",
    pillars: {
      identity: { status: "strong", controls: {}, gaps: [] },
      behavior_monitoring: { status: "strong", controls: {}, gaps: ["Expand anomaly scoring coverage"] },
      data_governance: { status: "partial", controls: {}, gaps: ["Tighten data retention windows"] },
      segmentation: { status: "strong", controls: {}, gaps: [] },
      incident_response: { status: "partial", controls: {}, gaps: ["Increase tabletop drill cadence"] },
    },
    evidence: {
      audit_window_hours: 24,
      audit_event_count_24h: 21,
      audit_allowed_24h: 17,
      audit_blocked_24h: 3,
      audit_error_24h: 1,
      total_audit_events: 95,
      run_count_total: 14,
    },
  })),
  submitApprovalMock: vi.fn(async () => ({})),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: routerRefreshMock,
  }),
}));

vi.mock("@/components/reactflow-canvas", () => ({
  ReactFlowCanvas: () => <div data-testid="rf-canvas" />,
}));

vi.mock("@/components/run-archive-button", () => ({
  RunArchiveButton: () => <button type="button">Archive</button>,
}));

vi.mock("@/components/run-followup-composer", () => ({
  RunFollowupComposer: () => <div data-testid="followup-composer" />,
}));

vi.mock("@/lib/api", () => ({
  getAtfAlignmentReport: getAtfAlignmentReportMock,
  submitApproval: submitApprovalMock,
}));

describe("RunConversationConsole", () => {
  const run = {
    artifacts: [{ id: "artifact-1", name: "Decision Memo", status: "Draft" as const, version: 1 }],
    status: "Running",
    graph: {
      nodes: [{ id: "node-1", title: "Agent", type: "frontier/agent", x: 100, y: 120, config: {} }],
      links: [],
    },
    agent_traces: [],
    approvals: { required: false, pending: false },
  };

  const events = [
    {
      id: "evt-1",
      type: "user_message" as const,
      title: "User prompt",
      summary: "Please generate the draft.",
      createdAt: new Date().toISOString(),
    },
  ];

  it("renders ATF posture metrics and top gaps", async () => {
    getAtfAlignmentReportMock.mockClear();

    render(<RunConversationConsole runId="run-1" run={run} events={events} />);

    expect(await screen.findByText(/ATF posture at execution time/i)).toBeInTheDocument();
    expect(await screen.findByText("87%")).toBeInTheDocument();
    expect(await screen.findByText("senior")).toBeInTheDocument();

    const blockedLabel = await screen.findByText(/Blocked \(24h\)/i);
    const blockedCard = blockedLabel.closest("div");
    expect(blockedCard).not.toBeNull();
    expect(within(blockedCard as HTMLElement).getByText("3")).toBeInTheDocument();

    const errorsLabel = await screen.findByText(/Errors \(24h\)/i);
    const errorsCard = errorsLabel.closest("div");
    expect(errorsCard).not.toBeNull();
    expect(within(errorsCard as HTMLElement).getByText("1")).toBeInTheDocument();

    expect(await screen.findByText(/Tighten data retention windows/i)).toBeInTheDocument();

    expect(getAtfAlignmentReportMock).toHaveBeenCalledTimes(1);
  });

  it("shows ATF loading error message when report fetch fails", async () => {
    getAtfAlignmentReportMock.mockReset();
    getAtfAlignmentReportMock.mockRejectedValueOnce(new Error("network"));

    render(<RunConversationConsole runId="run-2" run={run} events={events} />);

    expect(await screen.findByText(/Unable to load ATF posture/i)).toBeInTheDocument();
    expect(getAtfAlignmentReportMock).toHaveBeenCalledTimes(1);
  });
});
