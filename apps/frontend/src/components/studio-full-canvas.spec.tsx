import type { ComponentProps, ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StudioFullCanvas } from "@/components/studio-full-canvas";

const reactFlowCanvasSpy = vi.fn();
const autoLayoutSpy = vi.fn();
const routerPushSpy = vi.fn();
const { getNodeDefinitionsMock, runGraphMock } = vi.hoisted(() => ({
  getNodeDefinitionsMock: vi.fn(async () => []),
  runGraphMock: vi.fn(async () => ({
    run_id: "r1",
    status: "completed",
    execution_order: [],
    node_results: {},
    events: [],
    validation: { valid: true, issues: [] },
    runtime: {
      requested_engine: "native",
      selected_engine: "native",
      executed_engine: "native",
      mode: "native",
    },
  })),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPushSpy,
  }),
}));

vi.mock("@/lib/api", () => ({
  getNodeDefinitions: getNodeDefinitionsMock,
  getCollaborationSession: vi.fn(async () => ({
    id: "collab-1",
    version: 1,
    participants: [],
    graph_json: { nodes: [], links: [] },
  })),
  getGuardrailRulesets: vi.fn(async () => []),
  getObservabilityDashboard: vi.fn(async () => ({
    summary: {
      total_runs: 0,
      token_estimate: 0,
      cost_estimate_usd: 0,
      average_latency_ms: 0,
    },
    runs: [],
  })),
  getObservabilityRunTrace: vi.fn(async () => ({
    run_id: "r1",
    status: "completed",
    event_count: 0,
    node_count: 0,
    edge_count: 0,
  })),
  getRuntimeProviders: vi.fn(async () => ({
    providers: [],
    framework_adapters: {
      langgraph: { engine: "langgraph", available: true, missing_modules: [] },
      langchain: { engine: "langchain", available: false, missing_modules: ["langchain_openai"] },
    },
  })),
  getPlatformSettings: vi.fn(async () => ({
    local_only_mode: true,
    mask_secrets_in_events: true,
    require_human_approval: false,
    default_guardrail_ruleset_id: null,
    global_blocked_keywords: [],
    collaboration_max_agents: 8,
    default_runtime_engine: "native",
    default_runtime_strategy: "single",
    default_hybrid_runtime_routing: {
      default: "native",
      orchestration: "native",
      retrieval: "native",
      tooling: "native",
      collaboration: "native",
    },
    allowed_runtime_engines: ["native", "langgraph", "langchain"],
    allow_runtime_engine_override: true,
    enforce_runtime_engine_allowlist: true,
  })),
  getMemorySession: vi.fn(async () => ({ session_id: "s", count: 0, entries: [] })),
  clearMemorySession: vi.fn(async () => ({ ok: true, session_id: "s" })),
  joinCollaborationSession: vi.fn(async () => ({
    session: { id: "collab-1", version: 1, participants: [], graph_json: { nodes: [], links: [] } },
    participant: { role: "editor" },
  })),
  syncCollaborationSession: vi.fn(async () => ({ version: 2 })),
  validateGraph: vi.fn(async () => ({ valid: true, issues: [] })),
  runGraph: runGraphMock,
}));

vi.mock("@/components/reactflow-canvas", () => ({
  ReactFlowCanvas: (props: {
    onReady?: (api: {
      addNode: (node: { type: string; title?: string; x?: number; y?: number; config?: Record<string, unknown> }) => void;
      autoLayout: (options?: { fitView?: boolean }) => void;
      clear: () => void;
      serialize: () => { nodes: Array<unknown>; links: Array<unknown> };
    }) => void;
  }) => {
    reactFlowCanvasSpy(props);
    props.onReady?.({
      addNode: () => {},
      autoLayout: autoLayoutSpy,
      clear: () => {},
      serialize: () => ({ nodes: [], links: [] }),
    });
    return <div data-testid="rf-canvas" />;
  },
}));

async function renderStudioFullCanvas(props: ComponentProps<typeof StudioFullCanvas>) {
  let rendered: ReturnType<typeof render> | undefined;

  await act(async () => {
    rendered = render(<StudioFullCanvas {...props} />);
    await Promise.resolve();
  });

  await waitFor(() => expect(getNodeDefinitionsMock).toHaveBeenCalled());
  return rendered as ReturnType<typeof render>;
}

describe("StudioFullCanvas", () => {
  beforeEach(() => {
    reactFlowCanvasSpy.mockClear();
    autoLayoutSpy.mockClear();
    getNodeDefinitionsMock.mockClear();
    runGraphMock.mockClear();
    routerPushSpy.mockClear();
  });

  it("hides internal runtime controls in standard mode", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    expect(await screen.findByText(/Execution Profile/i)).toBeInTheDocument();
    expect(screen.queryByText(/Framework adapters/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/runtime engine/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/runtime session id/i)).not.toBeInTheDocument();
  });

  it("applies overflow-safe viewport classes", async () => {
    const { container } = await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    const section = container.querySelector("section");
    expect(section).not.toBeNull();
    expect(section?.className).toContain("overflow-hidden");
    expect(section?.className).toContain("h-[calc(100vh-57px-2rem)]");
    expect(section?.className).toContain("md:h-[calc(100vh-57px-3rem)]");
  });

  it("passes selected edge style controls to canvas", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    const edgeSelect = screen.getByRole("combobox", { name: /edge style/i });
    expect(edgeSelect).toHaveValue("default");

    fireEvent.change(edgeSelect, { target: { value: "step" } });

    const animateToggle = screen.getByRole("checkbox", { name: /animate/i });
    fireEvent.click(animateToggle);

    const lastCall = reactFlowCanvasSpy.mock.calls[reactFlowCanvasSpy.mock.calls.length - 1]?.[0] as {
      edgeType?: string;
      edgeAnimated?: boolean;
    };

    expect(lastCall.edgeType).toBe("step");
    expect(lastCall.edgeAnimated).toBe(false);
  });

  it("triggers auto layout from toolbar", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [{ id: "n1", title: "Trigger", type: "frontier/trigger", x: 0, y: 0, config: {} }],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    fireEvent.click(screen.getByRole("button", { name: /auto layout/i }));

    expect(autoLayoutSpy).toHaveBeenCalledWith({ fitView: true });
  });

  it("shows framework adapter readiness indicators", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      builderMode: "internal",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    expect(await screen.findByText("Framework adapters")).toBeInTheDocument();
    expect(await screen.findByLabelText(/runtime engine/i)).toBeInTheDocument();
    const adapterBadges = await screen.findAllByLabelText(/Runtime adapter .* (ready|missing dependencies)/i);
    expect(adapterBadges.length).toBeGreaterThan(0);
    expect(getNodeDefinitionsMock).toHaveBeenCalledWith({ includeInternal: true });
  });

  it("passes selected runtime engine to graph run payload", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      builderMode: "internal",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    const runtimeEngineSelect = await screen.findByLabelText(/runtime engine/i);
    fireEvent.change(runtimeEngineSelect, { target: { value: "langgraph" } });
    fireEvent.click(screen.getByRole("button", { name: /run test/i }));

    await waitFor(() => expect(runGraphMock).toHaveBeenCalledTimes(1));
    const calls = runGraphMock.mock.calls as unknown as Array<[unknown]>;
    const payload = calls[0]?.[0];
    expect(payload).toBeDefined();
    const call = payload as unknown as {
      input?: {
        runtime?: {
          engine?: string;
        };
      };
    };
    expect(call.input?.runtime?.engine).toBe("langgraph");
  });

  it("passes hybrid strategy routing to graph run payload", async () => {
    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      builderMode: "internal",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave: async () => {},
      onPublish: async () => {},
    });

    fireEvent.change(await screen.findByLabelText(/runtime strategy/i), { target: { value: "hybrid" } });
    fireEvent.change(await screen.findByLabelText(/hybrid route retrieval/i), { target: { value: "langchain" } });
    fireEvent.change(await screen.findByLabelText(/hybrid route collaboration/i), { target: { value: "autogen" } });
    fireEvent.click(screen.getByRole("button", { name: /run test/i }));

    await waitFor(() => expect(runGraphMock).toHaveBeenCalledTimes(1));
    const calls = runGraphMock.mock.calls as unknown as Array<[unknown]>;
    const payload = calls[0]?.[0];
    expect(payload).toBeDefined();
    const call = payload as unknown as {
      input?: {
        runtime?: {
          strategy?: string;
          hybrid_routing?: {
            retrieval?: string;
            collaboration?: string;
          };
        };
      };
    };
    expect(call.input?.runtime?.strategy).toBe("hybrid");
    expect(call.input?.runtime?.hybrid_routing?.retrieval).toBe("langchain");
    expect(call.input?.runtime?.hybrid_routing?.collaboration).toBe("autogen");
  });

  it("supports playbook mode without a publish action", async () => {
    await renderStudioFullCanvas({
      entityType: "playbook",
      entityId: "playbook-1",
      entityName: "Ops Playbook",
      description: "playbook summary",
      initialNodes: [],
      initialLinks: [],
      rightSidebarSlot: <div>Playbook Settings</div>,
      onSave: async () => {},
    });

    expect(await screen.findByText(/Playbook Studio/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /publish/i })).not.toBeInTheDocument();
    expect(screen.getByText("Playbook Settings")).toBeInTheDocument();
    expect(screen.getByText("Diagram Summary")).toBeInTheDocument();
    expect(screen.getByText("playbook summary")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /collapse header details panel/i })).toBeInTheDocument();
    expect(screen.getByText("playbook summary")).toHaveClass("text-[9px]");
  });

  it("collapses everything below the header divider", async () => {
    await renderStudioFullCanvas({
      entityType: "workflow",
      entityId: "workflow-1",
      entityName: "Workflow One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      rightSidebarSlot: <div>Workflow Settings</div>,
      onSave: async () => {},
      onPublish: async () => {},
    });

    expect(screen.getByText("Workflow Settings")).toBeInTheDocument();
    expect(screen.getByText("Diagram Summary")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /collapse header details panel/i }));

    expect(screen.queryByText("Workflow Settings")).not.toBeInTheDocument();
    expect(screen.queryByText("Diagram Summary")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /expand header details panel/i })).toBeInTheDocument();
  });

  it("keeps the expand control at the far right of the studio title row", async () => {
    await renderStudioFullCanvas({
      entityType: "playbook",
      entityId: "playbook-1",
      entityName: "Ops Playbook",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      rightSidebarSlot: <div>Playbook Settings</div>,
      onSave: async () => {},
    });

    const collapseButton = screen.getByRole("button", { name: /collapse header details panel/i });
    const titleText = screen.getByText(/Playbook Studio \/ Ops Playbook/i);
    const titleRow = collapseButton.parentElement;

    expect(titleRow).not.toBeNull();
    expect(titleRow).toContainElement(collapseButton);
    expect(titleRow).toContainElement(titleText);
    expect(titleRow?.lastElementChild).toBe(collapseButton);
  });

  it("saves and returns when a return action is configured", async () => {
    const onSave = vi.fn(async () => {});

    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave,
      onPublish: async () => {},
      returnAction: { label: "Save & Return", href: "/builder/workflows/wf-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save & return/i }));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(routerPushSpy).toHaveBeenCalledWith("/builder/workflows/wf-1"));
  });

  it("does not navigate when save and return fails", async () => {
    const onSave = vi.fn(async () => {
      throw new Error("save failed");
    });

    await renderStudioFullCanvas({
      entityType: "agent",
      entityId: "agent-1",
      entityName: "Agent One",
      description: "desc",
      initialNodes: [],
      initialLinks: [],
      onSave,
      onPublish: async () => {},
      returnAction: { label: "Save & Return", href: "/builder/workflows/wf-1" },
    });

    fireEvent.click(screen.getByRole("button", { name: /save & return/i }));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(routerPushSpy).not.toHaveBeenCalled();
  });
});
