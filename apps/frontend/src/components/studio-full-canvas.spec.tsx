import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StudioFullCanvas } from "@/components/studio-full-canvas";

const reactFlowCanvasSpy = vi.fn();
const autoLayoutSpy = vi.fn();
const { runGraphMock } = vi.hoisted(() => ({
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
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  getNodeDefinitions: vi.fn(async () => []),
  getGuardrailRulesets: vi.fn(async () => []),
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
    allow_direct_openai_without_agent: true,
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

describe("StudioFullCanvas", () => {
  it("applies overflow-safe viewport classes", () => {
    const { container } = render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

    const section = container.querySelector("section");
    expect(section).not.toBeNull();
    expect(section?.className).toContain("overflow-hidden");
    expect(section?.className).toContain("h-[calc(100vh-57px-2rem)]");
    expect(section?.className).toContain("md:h-[calc(100vh-57px-3rem)]");
  });

  it("passes selected edge style controls to canvas", () => {
    autoLayoutSpy.mockReset();
    render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

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

  it("triggers auto layout from toolbar", () => {
    autoLayoutSpy.mockReset();

    render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[{ id: "n1", title: "Trigger", type: "frontier/trigger", x: 0, y: 0, config: {} }]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /auto layout/i }));

    expect(autoLayoutSpy).toHaveBeenCalledWith({ fitView: true });
  });

  it("shows framework adapter readiness indicators", async () => {
    render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

    expect(await screen.findByText("Framework adapters")).toBeInTheDocument();
    expect(await screen.findByLabelText(/runtime engine/i)).toBeInTheDocument();
    const adapterBadges = await screen.findAllByLabelText(/Runtime adapter .* (ready|missing dependencies)/i);
    expect(adapterBadges.length).toBeGreaterThan(0);
  });

  it("passes selected runtime engine to graph run payload", async () => {
    runGraphMock.mockClear();

    render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

    const runtimeEngineSelect = await screen.findByLabelText(/runtime engine/i);
    fireEvent.change(runtimeEngineSelect, { target: { value: "langgraph" } });
    fireEvent.click(screen.getByRole("button", { name: /run test/i }));

    await waitFor(() => expect(runGraphMock).toHaveBeenCalledTimes(1));
    const call = runGraphMock.mock.calls[0]?.[0] as {
      input?: {
        runtime?: {
          engine?: string;
        };
      };
    };
    expect(call.input?.runtime?.engine).toBe("langgraph");
  });

  it("passes hybrid strategy routing to graph run payload", async () => {
    runGraphMock.mockClear();

    render(
      <StudioFullCanvas
        entityType="agent"
        entityId="agent-1"
        entityName="Agent One"
        description="desc"
        initialNodes={[]}
        initialLinks={[]}
        onSave={async () => {}}
        onPublish={async () => {}}
      />,
    );

    fireEvent.change(await screen.findByLabelText(/runtime strategy/i), { target: { value: "hybrid" } });
    fireEvent.change(await screen.findByLabelText(/hybrid route retrieval/i), { target: { value: "langchain" } });
    fireEvent.change(await screen.findByLabelText(/hybrid route collaboration/i), { target: { value: "autogen" } });
    fireEvent.click(screen.getByRole("button", { name: /run test/i }));

    await waitFor(() => expect(runGraphMock).toHaveBeenCalledTimes(1));
    const call = runGraphMock.mock.calls[0]?.[0] as {
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
});
