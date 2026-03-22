"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ReactFlowCanvas, type GraphLink, type GraphNode } from "@/components/reactflow-canvas";
import { normalizeNodeTypeForSchema, resolveNodePortAlias } from "@/lib/frontier-node-schema";
import {
  clearMemorySession,
  getCollaborationSession,
  getGuardrailRulesets,
  getMemorySession,
  getNodeDefinitions,
  getObservabilityDashboard,
  getObservabilityRunTrace,
  getPlatformSettings,
  getRuntimeProviders,
  joinCollaborationSession,
  runGraph,
  syncCollaborationSession,
  type GraphRunResponse,
  type ObservabilityDashboardResponse,
  type ObservabilityRunTrace,
  type PlatformRuntimePolicySettings,
  type RuntimeHybridRouting,
  type RuntimeEngineName,
  type RuntimeStrategyName,
  type RuntimeFrameworkAdapterProbe,
  type RuntimeProvider,
  validateGraph,
} from "@/lib/api";

type StudioEntityType = "agent" | "workflow";

type Props = {
  entityType: StudioEntityType;
  entityId: string;
  entityName: string;
  description: string;
  initialNodes: GraphNode[];
  initialLinks: GraphLink[];
  initialGeneratedArtifacts?: unknown[];
  rightSidebarSlot?: React.ReactNode;
  onSave: (payload: { nodes: GraphNode[]; links: GraphLink[] }) => Promise<void>;
  onPublish: () => Promise<void>;
};

export function StudioFullCanvas({
  entityType,
  entityId,
  entityName,
  description,
  initialNodes,
  initialLinks,
  onSave,
  onPublish,
}: Props) {
  const canvasApiRef = useRef<{
    addNode: (node: { type: string; title?: string; x?: number; y?: number; config?: Record<string, unknown> }) => void;
    autoLayout: (options?: { fitView?: boolean }) => void;
    replaceGraph: (graph: { nodes: GraphNode[]; links: GraphLink[] }, options?: { fitView?: boolean }) => void;
    clear: () => void;
    serialize: () => { nodes: GraphNode[]; links: GraphLink[] };
  } | null>(null);
  const suppressCollabSyncRef = useRef(false);
  const collabVersionRef = useRef(0);
  const localGraphDirtyRef = useRef(false);
  const [extraNodeDefinitions, setExtraNodeDefinitions] = useState<
    Array<{ key: `frontier/${string}`; title: string; color?: string; description?: string }>
  >([]);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({
    nodes: initialNodes,
    links: initialLinks,
  });
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [publishState, setPublishState] = useState<"idle" | "publishing" | "published" | "error">("idle");
  const [validateState, setValidateState] = useState<"idle" | "validating" | "valid" | "invalid" | "error">("idle");
  const [runState, setRunState] = useState<"idle" | "running" | "completed" | "failed" | "error">("idle");
  const [validationIssues, setValidationIssues] = useState<Array<{ code: string; message: string; path: string }>>([]);
  const [runResult, setRunResult] = useState<GraphRunResponse | null>(null);
  const [providerStatus, setProviderStatus] = useState<RuntimeProvider | null>(null);
  const [frameworkAdapters, setFrameworkAdapters] = useState<Record<string, RuntimeFrameworkAdapterProbe>>({});
  const [runtimePolicy, setRuntimePolicy] = useState<PlatformRuntimePolicySettings>({
    default_runtime_engine: "native",
    default_runtime_strategy: "single",
    default_hybrid_runtime_routing: {
      default: "native",
      orchestration: "native",
      retrieval: "native",
      tooling: "native",
      collaboration: "native",
    },
    allowed_runtime_engines: ["native"],
    allow_runtime_engine_override: false,
    enforce_runtime_engine_allowlist: true,
  });
  const [runtimeEngine, setRuntimeEngine] = useState<RuntimeEngineName>("native");
  const [runtimeStrategy, setRuntimeStrategy] = useState<RuntimeStrategyName>("single");
  const [hybridRouting, setHybridRouting] = useState<RuntimeHybridRouting>({
    default: "native",
    orchestration: "langgraph",
    retrieval: "langchain",
    tooling: "semantic-kernel",
    collaboration: "autogen",
  });
  const [runtimeModel, setRuntimeModel] = useState("gpt-5.2");
  const [runtimeTemperature, setRuntimeTemperature] = useState("0.2");
  const [sessionId, setSessionId] = useState(`${entityType}:${entityId}`);
  const [useMemory, setUseMemory] = useState(true);
  const [memoryCount, setMemoryCount] = useState(0);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [widgetOptionOverrides, setWidgetOptionOverrides] = useState<Record<string, Record<string, string[]>>>({});
  const [edgeType, setEdgeType] = useState<"smoothstep" | "step" | "straight" | "default" | "simplebezier">("default");
  const [edgeAnimated, setEdgeAnimated] = useState(true);
  const [collabSessionId, setCollabSessionId] = useState("");
  const [collabRole, setCollabRole] = useState<"owner" | "editor" | "viewer">("editor");
  const [collabParticipants, setCollabParticipants] = useState<Array<{ user_id: string; display_name: string; role: "owner" | "editor" | "viewer"; last_seen_at: string }>>([]);
  const [collabVersion, setCollabVersion] = useState(0);
  const [collabSyncState, setCollabSyncState] = useState<"idle" | "syncing" | "ok" | "conflict" | "error">("idle");
  const [observabilityDashboard, setObservabilityDashboard] = useState<ObservabilityDashboardResponse | null>(null);
  const [selectedTrace, setSelectedTrace] = useState<ObservabilityRunTrace | null>(null);
  const [collabUserId, setCollabUserId] = useState("local-user");
  const [runtimePanelCollapsed, setRuntimePanelCollapsed] = useState(false);

  const isReadOnly = collabRole === "viewer";

  const handleGraphChange = useCallback((nextGraph: { nodes: GraphNode[]; links: GraphLink[] }) => {
    if (suppressCollabSyncRef.current) {
      setGraph(nextGraph);
      suppressCollabSyncRef.current = false;
      return;
    }

    localGraphDirtyRef.current = true;
    setGraph((previous) => {
      const previousConfigByNodeId = new Map(previous.nodes.map((node) => [node.id, node.config ?? {}]));
      return {
        ...nextGraph,
        nodes: nextGraph.nodes.map((node) => ({
          ...node,
          config: node.config && Object.keys(node.config).length > 0 ? node.config : previousConfigByNodeId.get(node.id) ?? {},
        })),
      };
    });
  }, []);

  const summary = useMemo(() => {
    const typeCount = graph.nodes.reduce<Record<string, number>>((acc, node) => {
      acc[node.type] = (acc[node.type] ?? 0) + 1;
      return acc;
    }, {});
    return {
      nodes: graph.nodes.length,
      edges: graph.links.length,
      topTypes: Object.entries(typeCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3),
    };
  }, [graph.links.length, graph.nodes]);

  const runOutputPreview = useMemo(() => {
    if (!runResult) {
      return null;
    }

    const orderedNodeIds = [...runResult.execution_order].reverse();
    for (const nodeId of orderedNodeIds) {
      const result = runResult.node_results[nodeId];
      if (!result || typeof result !== "object") {
        continue;
      }

      const directResponse = result.response;
      if (typeof directResponse === "string" && directResponse.trim()) {
        return directResponse.trim();
      }

      const published = result.published as { payload?: unknown } | undefined;
      const payload = published?.payload;
      if (payload && typeof payload === "object") {
        const maybeResponse = (payload as { response?: unknown }).response;
        if (typeof maybeResponse === "string" && maybeResponse.trim()) {
          return maybeResponse.trim();
        }
      }
    }

    return null;
  }, [runResult]);

  const wiringIssues = useMemo(() => {
    const issues: Array<{ code: string; message: string }> = [];
    const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));

    const incomingTo = (nodeId: string, expectedPorts: string[]) => {
      const targetNode = nodeById.get(nodeId);
      if (!targetNode) {
        return 0;
      }

      return graph.links.filter((link) => {
        if (link.to !== nodeId) {
          return false;
        }
        const rawPort = link.to_port ?? "in";
        const normalized = resolveNodePortAlias(targetNode.type, "input", rawPort) ?? rawPort;
        return expectedPorts.includes(normalized);
      }).length;
    };

    for (const node of graph.nodes) {
      const normalizedType = normalizeNodeTypeForSchema(node.type);
      const cfg = (node.config ?? {}) as Record<string, unknown>;

      if (normalizedType === "agent") {
        if (incomingTo(node.id, ["in"]) === 0) {
          issues.push({ code: "AGENT_FLOW_INPUT_REQUIRED", message: `${node.title}: connect flow input to 'in'.` });
        }
        const hasPromptEdge = incomingTo(node.id, ["prompt"]) > 0;
        const hasInlinePrompt = String(cfg.system_prompt ?? "").trim().length > 0;
        if (!hasPromptEdge && !hasInlinePrompt) {
          issues.push({ code: "AGENT_PROMPT_REQUIRED", message: `${node.title}: connect 'prompt' or set inline system_prompt.` });
        }
      }

      if (normalizedType === "retrieval") {
        if (incomingTo(node.id, ["query"]) === 0) {
          issues.push({ code: "RETRIEVAL_QUERY_INPUT_REQUIRED", message: `${node.title}: connect query input to 'query'.` });
        }
      }

      if (normalizedType === "tool-call") {
        if (incomingTo(node.id, ["in"]) === 0) {
          issues.push({ code: "TOOL_FLOW_INPUT_REQUIRED", message: `${node.title}: connect flow input to 'in'.` });
        }
        if (incomingTo(node.id, ["request"]) === 0) {
          issues.push({ code: "TOOL_REQUEST_INPUT_REQUIRED", message: `${node.title}: connect request input to 'request'.` });
        }
      }

      if (normalizedType === "output") {
        if (incomingTo(node.id, ["in"]) === 0) {
          issues.push({ code: "OUTPUT_FLOW_INPUT_REQUIRED", message: `${node.title}: connect flow input to 'in'.` });
        }
        if (incomingTo(node.id, ["result"]) === 0) {
          issues.push({ code: "OUTPUT_RESULT_INPUT_REQUIRED", message: `${node.title}: connect payload input to 'result'.` });
        }
      }
    }

    return issues;
  }, [graph.links, graph.nodes]);

  useEffect(() => {
    let cancelled = false;

    async function loadNodeDefinitions() {
      const nodeDefinitions = await getNodeDefinitions();
      if (cancelled) {
        return;
      }

      const allNodeDefinitions = nodeDefinitions
        .filter((node) => node.type_key.startsWith("frontier/"))
        .map((node) => ({
          key: node.type_key as `frontier/${string}`,
          title: node.title ?? node.type_key.replace("frontier/", ""),
          color: node.color,
          description: node.description,
        }));

      setExtraNodeDefinitions(allNodeDefinitions);
    }

    void loadNodeDefinitions();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const storageKey = `frontier:collab:${entityType}:${entityId}:user`;
    const existing = typeof window !== "undefined" ? window.localStorage.getItem(storageKey) : null;
    if (existing) {
      setCollabUserId(existing);
      return;
    }

    const generated = `${entityType}-${entityId}-${Math.random().toString(36).slice(2, 9)}`;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, generated);
    }
    setCollabUserId(generated);
  }, [entityId, entityType]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrapCollaboration() {
      try {
        const joined = await joinCollaborationSession({
          entity_type: entityType,
          entity_id: entityId,
          user_id: collabUserId,
          display_name: `Local ${collabUserId.slice(-6)}`,
        });

        if (cancelled) {
          return;
        }

        setCollabSessionId(joined.session.id);
        setCollabRole(joined.participant.role);
        setCollabParticipants(joined.session.participants);
        setCollabVersion(joined.session.version);
        collabVersionRef.current = joined.session.version;
        setCollabSyncState("ok");
      } catch {
        if (!cancelled) {
          setCollabSyncState("error");
        }
      }
    }

    if (collabUserId) {
      void bootstrapCollaboration();
    }

    return () => {
      cancelled = true;
    };
  }, [collabUserId, entityId, entityType]);

  useEffect(() => {
    if (!collabSessionId) {
      return;
    }

    const interval = setInterval(() => {
      void (async () => {
        try {
          if (!collabSessionId) {
            return;
          }

          const session = await getCollaborationSession(collabSessionId);
          if (!session) {
            return;
          }
          setCollabParticipants(session.participants);
          const self = session.participants.find((participant) => participant.user_id === collabUserId);
          setCollabRole(self?.role ?? collabRole);
          setCollabVersion(session.version);

          const shouldPullRemote = session.version > collabVersionRef.current && !localGraphDirtyRef.current;
          if (shouldPullRemote) {
            collabVersionRef.current = session.version;
            suppressCollabSyncRef.current = true;
            canvasApiRef.current?.replaceGraph(
              {
                nodes: session.graph_json.nodes ?? [],
                links: session.graph_json.links ?? [],
              },
              { fitView: false },
            );
            setGraph({ nodes: session.graph_json.nodes ?? [], links: session.graph_json.links ?? [] });
            setCollabSyncState("ok");
          }
        } catch {
          setCollabSyncState("error");
        }
      })();
    }, 2500);

    return () => {
      clearInterval(interval);
    };
  }, [collabRole, collabSessionId, collabUserId, entityId, entityType]);

  useEffect(() => {
    if (!collabSessionId || isReadOnly || !localGraphDirtyRef.current) {
      return;
    }

    const timeout = setTimeout(() => {
      void (async () => {
        setCollabSyncState("syncing");
        try {
          const synced = await syncCollaborationSession(collabSessionId, {
            user_id: collabUserId,
            base_version: collabVersionRef.current,
            graph_json: {
              nodes: graph.nodes,
              links: graph.links,
            },
          });

          collabVersionRef.current = synced.version;
          setCollabVersion(synced.version);
          setCollabSyncState("ok");
          localGraphDirtyRef.current = false;
        } catch (error) {
          if (error instanceof Error && error.message.includes("409")) {
            setCollabSyncState("conflict");
            return;
          }
          setCollabSyncState("error");
        }
      })();
    }, 700);

    return () => {
      clearTimeout(timeout);
    };
  }, [collabSessionId, collabUserId, entityId, entityType, graph.links, graph.nodes, isReadOnly]);

  useEffect(() => {
    let cancelled = false;

    async function refreshObservability() {
      try {
        const dashboard = await getObservabilityDashboard();
        if (!cancelled) {
          setObservabilityDashboard(dashboard);
        }
      } catch {
        if (!cancelled) {
          setObservabilityDashboard(null);
        }
      }
    }

    void refreshObservability();

    return () => {
      cancelled = true;
    };
  }, [runResult?.run_id]);

  useEffect(() => {
    let cancelled = false;

    async function loadGuardrailOptions() {
      const rulesets = await getGuardrailRulesets();
      if (cancelled) {
        return;
      }

      const publishedRuleSetIds = rulesets
        .filter((item) => item.status === "published")
        .map((item) => item.id);

      setWidgetOptionOverrides({
        guardrail: {
          ruleset_id: publishedRuleSetIds,
        },
      });
    }

    void loadGuardrailOptions();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadRuntimeProvider() {
      const [response, platformSettings] = await Promise.all([getRuntimeProviders(), getPlatformSettings()]);
      if (cancelled) {
        return;
      }
      const openai = response.providers.find((provider) => provider.provider === "openai") ?? null;
      setProviderStatus(openai);
      setFrameworkAdapters(response.framework_adapters ?? {});
      if (openai?.model) {
        setRuntimeModel(openai.model);
      }

      const nextPolicy: PlatformRuntimePolicySettings = {
        default_runtime_engine: (platformSettings.default_runtime_engine ?? "native") as RuntimeEngineName,
        default_runtime_strategy: (platformSettings.default_runtime_strategy ?? "single") as RuntimeStrategyName,
        default_hybrid_runtime_routing: {
          default: (platformSettings.default_hybrid_runtime_routing?.default ?? "native") as RuntimeEngineName,
          orchestration: (platformSettings.default_hybrid_runtime_routing?.orchestration ?? platformSettings.default_hybrid_runtime_routing?.default ?? "native") as RuntimeEngineName,
          retrieval: (platformSettings.default_hybrid_runtime_routing?.retrieval ?? platformSettings.default_hybrid_runtime_routing?.default ?? "native") as RuntimeEngineName,
          tooling: (platformSettings.default_hybrid_runtime_routing?.tooling ?? platformSettings.default_hybrid_runtime_routing?.default ?? "native") as RuntimeEngineName,
          collaboration: (platformSettings.default_hybrid_runtime_routing?.collaboration ?? platformSettings.default_hybrid_runtime_routing?.default ?? "native") as RuntimeEngineName,
        },
        allowed_runtime_engines: ((platformSettings.allowed_runtime_engines ?? ["native"]) as string[]).filter(Boolean),
        allow_runtime_engine_override: Boolean(platformSettings.allow_runtime_engine_override),
        enforce_runtime_engine_allowlist: Boolean(platformSettings.enforce_runtime_engine_allowlist),
      };
      if ((nextPolicy.allowed_runtime_engines ?? []).length === 0) {
        nextPolicy.allowed_runtime_engines = ["native"];
      }
      setRuntimePolicy(nextPolicy);
      setRuntimeEngine(nextPolicy.default_runtime_engine as RuntimeEngineName);
      setRuntimeStrategy(nextPolicy.default_runtime_strategy ?? "single");
      setHybridRouting({
        default: nextPolicy.default_hybrid_runtime_routing?.default ?? nextPolicy.default_runtime_engine ?? "native",
        orchestration: nextPolicy.default_hybrid_runtime_routing?.orchestration ?? nextPolicy.default_hybrid_runtime_routing?.default ?? nextPolicy.default_runtime_engine ?? "native",
        retrieval: nextPolicy.default_hybrid_runtime_routing?.retrieval ?? nextPolicy.default_hybrid_runtime_routing?.default ?? nextPolicy.default_runtime_engine ?? "native",
        tooling: nextPolicy.default_hybrid_runtime_routing?.tooling ?? nextPolicy.default_hybrid_runtime_routing?.default ?? nextPolicy.default_runtime_engine ?? "native",
        collaboration: nextPolicy.default_hybrid_runtime_routing?.collaboration ?? nextPolicy.default_hybrid_runtime_routing?.default ?? nextPolicy.default_runtime_engine ?? "native",
      });
    }

    void loadRuntimeProvider();

    return () => {
      cancelled = true;
    };
  }, []);

  const frameworkAdapterRows = useMemo(() => {
    const preferredOrder = ["langgraph", "langchain", "semantic-kernel", "autogen"];
    const keys = Object.keys(frameworkAdapters);
    const orderedKeys = preferredOrder.filter((engine) => keys.includes(engine));
    const extras = keys.filter((engine) => !preferredOrder.includes(engine)).sort();
    const resolved = [...orderedKeys, ...extras];

    return resolved.map((engine) => {
      const probe = frameworkAdapters[engine];
      return {
        engine,
        available: Boolean(probe?.available),
        missingModules: Array.isArray(probe?.missing_modules) ? probe.missing_modules : [],
      };
    });
  }, [frameworkAdapters]);

  const runtimeEngineOptions = useMemo(
    () => ["native", "langgraph", "langchain", "semantic-kernel", "autogen"] as RuntimeEngineName[],
    [],
  );

  const selectedEngineProbe = useMemo(
    () => frameworkAdapters[runtimeStrategy === "hybrid" ? (hybridRouting.default ?? "native") : runtimeEngine],
    [frameworkAdapters, hybridRouting.default, runtimeEngine, runtimeStrategy],
  );

  const effectiveRuntimeEngine = useMemo<RuntimeEngineName>(() => {
    if (!runtimePolicy.allow_runtime_engine_override) {
      return (runtimePolicy.default_runtime_engine as RuntimeEngineName) ?? "native";
    }
    if (runtimeStrategy === "hybrid") {
      return hybridRouting.default ?? "native";
    }
    return runtimeEngine;
  }, [hybridRouting.default, runtimeEngine, runtimePolicy.allow_runtime_engine_override, runtimePolicy.default_runtime_engine, runtimeStrategy]);

  const setHybridRoleEngine = useCallback((role: keyof RuntimeHybridRouting, engine: RuntimeEngineName) => {
    setHybridRouting((current) => ({
      ...current,
      [role]: engine,
    }));
  }, []);

  async function handleSaveDraft() {
    setSaveState("saving");
    try {
      await onSave(graph);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  async function handlePublish() {
    setPublishState("publishing");
    try {
      await onPublish();
      setPublishState("published");
    } catch {
      setPublishState("error");
    }
  }

  async function handleValidate() {
    setValidateState("validating");
    setValidationIssues([]);
    try {
      const validation = await validateGraph({
        nodes: graph.nodes,
        links: graph.links,
      });
      setValidationIssues(validation.issues);
      setValidateState(validation.valid ? "valid" : "invalid");
    } catch {
      setValidateState("error");
    }
  }

  async function handleRunTest() {
    setRunState("running");
    setRunResult(null);
    try {
      const result = await runGraph({
        nodes: graph.nodes,
        links: graph.links,
        input: {
          message: "Test execution from Studio",
          entityType,
          entityId,
          runtime: {
            provider: "openai",
            model: runtimeModel,
            temperature: Number(runtimeTemperature),
            session_id: sessionId,
            use_memory: useMemory,
            engine: effectiveRuntimeEngine,
            strategy: runtimeStrategy,
            hybrid_routing:
              runtimeStrategy === "hybrid"
                ? {
                    default: hybridRouting.default ?? effectiveRuntimeEngine,
                    orchestration: hybridRouting.orchestration ?? hybridRouting.default ?? effectiveRuntimeEngine,
                    retrieval: hybridRouting.retrieval ?? hybridRouting.default ?? effectiveRuntimeEngine,
                    tooling: hybridRouting.tooling ?? hybridRouting.default ?? effectiveRuntimeEngine,
                    collaboration: hybridRouting.collaboration ?? hybridRouting.default ?? effectiveRuntimeEngine,
                  }
                : undefined,
          },
        },
      });
      setRunResult(result);
      setRunState(result.status === "completed" ? "completed" : "failed");
      setValidationIssues(result.validation.issues);
      setValidateState(result.validation.valid ? "valid" : "invalid");
      try {
        const trace = await getObservabilityRunTrace(result.run_id);
        setSelectedTrace(trace);
      } catch {
        setSelectedTrace(null);
      }
    } catch {
      setRunState("error");
    }
  }

  async function handleRefreshMemory() {
    setMemoryBusy(true);
    try {
      const memory = await getMemorySession(sessionId);
      setMemoryCount(memory.count);
    } finally {
      setMemoryBusy(false);
    }
  }

  async function handleClearMemory() {
    setMemoryBusy(true);
    try {
      await clearMemorySession(sessionId);
      setMemoryCount(0);
    } finally {
      setMemoryBusy(false);
    }
  }

  function handleAutoLayout() {
    canvasApiRef.current?.autoLayout({ fitView: true });
  }

  const title = entityType === "agent" ? "Agent Studio" : "Workflow Studio";
  const backHref = entityType === "agent" ? "/builder/agents" : "/builder/workflows";

  return (
    <section className="-m-4 h-[calc(100vh-57px-2rem)] overflow-hidden md:-m-6 md:h-[calc(100vh-57px-3rem)]">
      <div className="relative h-full w-full">
        <ReactFlowCanvas
          className="h-full border-0"
          nodes={graph.nodes}
          links={graph.links}
          readOnly={isReadOnly}
          extraNodeDefinitions={extraNodeDefinitions}
          widgetOptionOverrides={widgetOptionOverrides}
          edgeType={edgeType}
          edgeAnimated={edgeAnimated}
          onGraphChange={handleGraphChange}
          onReady={(api) => {
            canvasApiRef.current = api;
          }}
        />

        <div className="pointer-events-none absolute inset-x-3 top-3 flex items-center justify-between gap-3">
          <div className="pointer-events-auto fx-panel px-3 py-2 text-[var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
            <Link href={backHref} className="text-[11px] font-mono fx-muted underline decoration-dotted underline-offset-4">
              Back to Library
            </Link>
            <div className="mt-1 text-sm font-semibold text-[var(--foreground)]">
              {title} / {entityName}
            </div>
            <div className="text-[11px] font-mono fx-muted">{entityType}_id: {entityId}</div>
            <div className="mt-1 flex items-center gap-1 text-[10px]">
              <span className="fx-muted">collab:</span>
              <span className="font-mono text-[var(--foreground)]">{collabSessionId ? collabSessionId.slice(0, 8) : "--"}</span>
              <span className="fx-muted">role:</span>
              <span className="font-semibold text-[var(--foreground)]">{collabRole}</span>
              <span className="fx-muted">sync:</span>
              <span className="font-semibold text-[var(--foreground)]">{collabSyncState}</span>
            </div>
          </div>

          <div className="pointer-events-auto fx-panel flex items-center gap-2 px-2 py-2 text-[var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
            <span className="hidden text-[10px] uppercase tracking-[0.08em] fx-muted lg:inline">Canvas Actions</span>
            <label className="flex items-center gap-1 text-[10px] fx-muted">
              <span>Edge</span>
              <select
                aria-label="Edge style"
                value={edgeType}
                onChange={(event) => setEdgeType(event.target.value as "smoothstep" | "step" | "straight" | "default" | "simplebezier")}
                className="fx-field px-1 py-0.5 text-[10px]"
              >
                <option value="step">Right-angle</option>
                <option value="smoothstep">Flow (smoothstep)</option>
                <option value="default">Bezier</option>
                <option value="simplebezier">Simple Bezier</option>
                <option value="straight">Straight</option>
              </select>
            </label>
            <label className="flex items-center gap-1 text-[10px] fx-muted">
              <input
                aria-label="Animate edges"
                type="checkbox"
                checked={edgeAnimated}
                onChange={(event) => setEdgeAnimated(event.target.checked)}
              />
              <span>Animate</span>
            </label>
            <button
              onClick={handleAutoLayout}
              className="fx-btn-secondary px-3 py-1.5 text-xs font-medium"
              disabled={graph.nodes.length === 0 || isReadOnly}
              title={graph.nodes.length === 0 ? "Add at least one node to auto-layout the canvas." : "Rearrange nodes to avoid overlap and improve readability."}
            >
              Auto Layout
            </button>
            <button
              onClick={handleValidate}
              className="fx-btn-secondary px-3 py-1.5 text-xs font-medium"
              disabled={validateState === "validating"}
              aria-busy={validateState === "validating"}
            >
              {validateState === "validating" ? "Validating..." : "Validate"}
            </button>
            <button
              onClick={handleRunTest}
              className="fx-btn-secondary px-3 py-1.5 text-xs font-medium"
              disabled={runState === "running"}
              aria-busy={runState === "running"}
            >
              {runState === "running" ? "Running..." : "Run Test"}
            </button>
            <button
              onClick={handleSaveDraft}
              className="fx-btn-secondary px-3 py-1.5 text-xs font-medium"
              disabled={saveState === "saving" || isReadOnly}
              aria-busy={saveState === "saving"}
            >
              {saveState === "saving" ? "Saving..." : "Save Draft"}
            </button>
            <button
              onClick={handlePublish}
              className="fx-btn-primary px-3 py-1.5 text-xs font-medium"
              disabled={publishState === "publishing" || isReadOnly}
              aria-busy={publishState === "publishing"}
            >
              {publishState === "publishing" ? "Publishing..." : "Publish"}
            </button>
          </div>
        </div>

        <div className="pointer-events-none absolute bottom-3 left-3 z-20 fx-panel px-2.5 py-1.5 text-[11px] fx-muted shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
          Tip: right-click canvas to add frontier nodes
        </div>

        <aside className="absolute right-3 top-24 z-20 w-32 fx-panel p-1.5 text-[var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--foreground)]">Diagram Summary</h2>
          <p className="mt-0.5 text-[9px] leading-tight fx-muted">{description}</p>
          <dl className="mt-1.5 grid grid-cols-2 gap-1 text-[10px]">
            <div className="fx-panel p-1">
              <dt className="text-[9px] fx-muted">Nodes</dt>
              <dd className="text-sm font-semibold text-[var(--foreground)]">{summary.nodes}</dd>
            </div>
            <div className="fx-panel p-1">
              <dt className="text-[9px] fx-muted">Edges</dt>
              <dd className="text-sm font-semibold text-[var(--foreground)]">{summary.edges}</dd>
            </div>
          </dl>
          <div className="mt-1.5 space-y-0.5 text-[10px]">
            {summary.topTypes.map(([type, count]) => (
              <div key={type} className="fx-panel flex items-center justify-between px-1 py-0.5">
                <span className="text-[var(--foreground)]">{type}</span>
                <span className="fx-muted">{count}</span>
              </div>
            ))}
          </div>
        </aside>

        <aside className={`absolute bottom-3 right-3 z-20 fx-panel p-2 text-[var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.35)] ${runtimePanelCollapsed ? "w-auto" : "w-[420px]"}`}>
          <div className="mb-1 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--foreground)]">Validation & Runtime</h3>
            <div className="flex items-center gap-2">
              <div className="text-[10px] fx-muted">
                validate={validateState} run={runState}
              </div>
              <button
                onClick={() => setRuntimePanelCollapsed((current) => !current)}
                className="fx-btn-secondary px-2 py-0.5 text-[10px]"
                aria-label={runtimePanelCollapsed ? "Expand Validation & Runtime panel" : "Collapse Validation & Runtime panel"}
                title={runtimePanelCollapsed ? "Expand panel" : "Collapse panel"}
              >
                {runtimePanelCollapsed ? "Expand" : "Collapse"}
              </button>
            </div>
          </div>

          {runtimePanelCollapsed ? (
            <div className="text-[10px] fx-muted">Panel collapsed to maximize canvas space.</div>
          ) : (
            <>

          {wiringIssues.length > 0 && (
            <div className="mb-1 border border-[color-mix(in_srgb,var(--fx-warning)_58%,var(--fx-border)_42%)] bg-[color-mix(in_srgb,var(--fx-warning)_14%,var(--fx-surface)_86%)] p-1 text-[10px] text-[var(--foreground)]">
              <div className="mb-1 font-semibold text-[var(--fx-warning)]">Wiring checks (pre-validate)</div>
              <ul className="max-h-20 list-disc space-y-0.5 overflow-auto pl-4 text-[var(--foreground)]">
                {wiringIssues.slice(0, 6).map((issue) => (
                  <li key={`${issue.code}-${issue.message}`}>{issue.message}</li>
                ))}
              </ul>
            </div>
          )}

          {validationIssues.length > 0 ? (
            <ul className="max-h-24 overflow-auto border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1 text-[10px]">
              {validationIssues.slice(0, 5).map((issue) => (
                <li key={`${issue.code}-${issue.path}`} className="mb-1 border-b border-[var(--fx-border)] pb-1 last:mb-0 last:border-b-0 last:pb-0">
                  <div className="font-semibold text-[var(--fx-danger)]">{issue.code}</div>
                  <div className="text-[var(--foreground)]">{issue.message}</div>
                  <div className="fx-muted">{issue.path}</div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="fx-panel px-2 py-1 text-[10px] fx-muted">No validation issues.</div>
          )}

          {runResult && (
            <div className="mt-1 border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1 text-[10px]">
              <div className="fx-muted">run_id</div>
              <div className="font-mono text-[var(--foreground)]">{runResult.run_id}</div>
              {runResult.runtime && (
                <>
                  <div className="mt-1 fx-muted">runtime engine</div>
                  <div className="font-mono text-[var(--foreground)]">
                    strategy={runResult.runtime.strategy ?? "single"} requested={runResult.runtime.requested_engine ?? "native"} selected={runResult.runtime.selected_engine ?? "native"} executed={runResult.runtime.executed_engine ?? "native"} mode={runResult.runtime.mode ?? "native"}
                  </div>
                  {runResult.runtime.strategy === "hybrid" && runResult.runtime.hybrid_effective_routing && (
                    <>
                      <div className="mt-1 fx-muted">hybrid routing</div>
                      <div className="font-mono text-[var(--foreground)]">
                        {Object.entries(runResult.runtime.hybrid_effective_routing)
                          .map(([role, engine]) => `${role}:${engine}`)
                          .join(" | ") || "(none)"}
                      </div>
                    </>
                  )}
                  {Array.isArray(runResult.runtime.node_dispatches) && runResult.runtime.node_dispatches.length > 0 && (
                    <>
                      <div className="mt-1 fx-muted">node dispatches</div>
                      <ul className="max-h-20 overflow-auto border border-[var(--fx-border)] bg-[var(--fx-input)] p-1 text-[9px] text-[var(--fx-input-text)]">
                        {runResult.runtime.node_dispatches.slice(0, 8).map((dispatch) => (
                          <li key={`${dispatch.node_id}:${dispatch.role ?? "default"}`}>
                            {dispatch.node_id} [{dispatch.role ?? "default"}] {dispatch.requested_engine ?? "native"}→{dispatch.executed_engine ?? "native"} ({dispatch.mode ?? "native"})
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )}
              <div className="mt-1 fx-muted">execution order</div>
              <div className="font-mono text-[var(--foreground)]">{runResult.execution_order.join(" → ") || "(empty)"}</div>
              <div className="mt-1 fx-muted">events</div>
              <div className="text-[var(--foreground)]">{runResult.events.length}</div>
              {runOutputPreview && (
                <>
                  <div className="mt-1 fx-muted">output preview</div>
                  <pre className="max-h-28 overflow-auto whitespace-pre-wrap border border-[var(--fx-border)] bg-[var(--fx-input)] p-1 text-[var(--fx-input-text)]">
                    {runOutputPreview}
                  </pre>
                </>
              )}
            </div>
          )}

          <div className="mt-2 fx-panel p-1.5 text-[10px]">
            <div className="mb-1 fx-muted">Model Runtime</div>
            <div className="mb-1 text-[var(--foreground)]">
              openai={providerStatus?.configured ? "configured" : "not-configured"} mode={providerStatus?.mode ?? "simulated"}
            </div>
            <div className="mb-1 flex items-center justify-between gap-2 text-[9px]">
              <span className="fx-muted">engine_override={runtimePolicy.allow_runtime_engine_override ? "enabled" : "disabled"}</span>
              <span className="fx-muted">effective={effectiveRuntimeEngine}</span>
            </div>
            <div className="mb-1 text-[9px] fx-muted">allowed={(runtimePolicy.allowed_runtime_engines ?? []).join(", ") || "native"}</div>
            <div className="mb-1 text-[9px] fx-muted">Framework adapters</div>
            <ul className="mb-1 max-h-20 overflow-auto border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1">
              {frameworkAdapterRows.length === 0 ? (
                <li className="fx-muted">No adapter probe data.</li>
              ) : (
                frameworkAdapterRows.map((row) => (
                  <li key={row.engine} className="mb-1 border-b border-[var(--fx-border)] pb-1 last:mb-0 last:border-b-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[var(--foreground)]">{row.engine}</span>
                      <span
                        className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold ${row.available ? "border-[color-mix(in_srgb,var(--fx-success)_60%,var(--fx-border)_40%)] bg-[color-mix(in_srgb,var(--fx-success)_20%,transparent)] text-[var(--foreground)]" : "border-[color-mix(in_srgb,var(--fx-warning)_60%,var(--fx-border)_40%)] bg-[color-mix(in_srgb,var(--fx-warning)_18%,transparent)] text-[var(--foreground)]"}`}
                        aria-label={`Runtime adapter ${row.engine} ${row.available ? "ready" : "missing dependencies"}`}
                        title={row.available ? "Adapter dependencies detected" : "Adapter dependencies missing"}
                      >
                        {row.available ? "READY" : "MISSING"}
                      </span>
                    </div>
                    {!row.available && row.missingModules.length > 0 && (
                      <div className="mt-0.5 break-all text-[9px] fx-muted">{row.missingModules.join(", ")}</div>
                    )}
                  </li>
                ))
              )}
            </ul>
            <div className="grid grid-cols-2 gap-1">
              <label className="col-span-2 flex flex-col gap-0.5 fx-muted">
                <span>runtime_strategy</span>
                <select
                  aria-label="Runtime strategy"
                  value={runtimeStrategy}
                  onChange={(event) => setRuntimeStrategy(event.target.value as RuntimeStrategyName)}
                  className="fx-field px-1 py-0.5 text-[10px]"
                >
                  <option value="single">single</option>
                  <option value="hybrid">hybrid (task-routed)</option>
                </select>
              </label>
              <label className="col-span-2 flex flex-col gap-0.5 fx-muted">
                <span>runtime_engine</span>
                <select
                  aria-label="Runtime engine"
                  value={runtimeEngine}
                  onChange={(event) => setRuntimeEngine(event.target.value as RuntimeEngineName)}
                  className="fx-field px-1 py-0.5 text-[10px]"
                  disabled={!runtimePolicy.allow_runtime_engine_override || runtimeStrategy === "hybrid"}
                >
                  {runtimeEngineOptions.map((engine) => {
                    const probe = frameworkAdapters[engine];
                    const depsReady = engine === "native" || Boolean(probe?.available);
                    const allowed = (runtimePolicy.allowed_runtime_engines ?? []).includes(engine);
                    const blockedByAllowlist = runtimePolicy.enforce_runtime_engine_allowlist && !allowed;
                    const label = `${engine}${depsReady ? "" : " (deps missing)"}${blockedByAllowlist ? " (not allowed)" : ""}`;
                    return (
                      <option key={engine} value={engine}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </label>
              {runtimeStrategy === "hybrid" && (
                <>
                  <label className="flex flex-col gap-0.5 fx-muted">
                    <span>route.default</span>
                    <select
                      aria-label="Hybrid route default"
                      value={hybridRouting.default ?? "native"}
                      onChange={(event) => setHybridRoleEngine("default", event.target.value as RuntimeEngineName)}
                      className="fx-field px-1 py-0.5 text-[10px]"
                    >
                      {runtimeEngineOptions.map((engine) => (
                        <option key={`hy-default-${engine}`} value={engine}>{engine}</option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-0.5 fx-muted">
                    <span>route.retrieval</span>
                    <select
                      aria-label="Hybrid route retrieval"
                      value={hybridRouting.retrieval ?? hybridRouting.default ?? "native"}
                      onChange={(event) => setHybridRoleEngine("retrieval", event.target.value as RuntimeEngineName)}
                      className="fx-field px-1 py-0.5 text-[10px]"
                    >
                      {runtimeEngineOptions.map((engine) => (
                        <option key={`hy-retrieval-${engine}`} value={engine}>{engine}</option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-0.5 fx-muted">
                    <span>route.tooling</span>
                    <select
                      aria-label="Hybrid route tooling"
                      value={hybridRouting.tooling ?? hybridRouting.default ?? "native"}
                      onChange={(event) => setHybridRoleEngine("tooling", event.target.value as RuntimeEngineName)}
                      className="fx-field px-1 py-0.5 text-[10px]"
                    >
                      {runtimeEngineOptions.map((engine) => (
                        <option key={`hy-tooling-${engine}`} value={engine}>{engine}</option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-0.5 fx-muted">
                    <span>route.orchestration</span>
                    <select
                      aria-label="Hybrid route orchestration"
                      value={hybridRouting.orchestration ?? hybridRouting.default ?? "native"}
                      onChange={(event) => setHybridRoleEngine("orchestration", event.target.value as RuntimeEngineName)}
                      className="fx-field px-1 py-0.5 text-[10px]"
                    >
                      {runtimeEngineOptions.map((engine) => (
                        <option key={`hy-orchestration-${engine}`} value={engine}>{engine}</option>
                      ))}
                    </select>
                  </label>
                  <label className="col-span-2 flex flex-col gap-0.5 fx-muted">
                    <span>route.collaboration</span>
                    <select
                      aria-label="Hybrid route collaboration"
                      value={hybridRouting.collaboration ?? hybridRouting.default ?? "native"}
                      onChange={(event) => setHybridRoleEngine("collaboration", event.target.value as RuntimeEngineName)}
                      className="fx-field px-1 py-0.5 text-[10px]"
                    >
                      {runtimeEngineOptions.map((engine) => (
                        <option key={`hy-collaboration-${engine}`} value={engine}>{engine}</option>
                      ))}
                    </select>
                  </label>
                </>
              )}
              <label className="flex flex-col gap-0.5 fx-muted">
                <span>model</span>
                <input
                  aria-label="Runtime model"
                  value={runtimeModel}
                  onChange={(event) => setRuntimeModel(event.target.value)}
                  className="fx-field px-1 py-0.5 text-[10px]"
                />
              </label>
              <label className="flex flex-col gap-0.5 fx-muted">
                <span>temperature</span>
                <input
                  aria-label="Runtime temperature"
                  value={runtimeTemperature}
                  onChange={(event) => setRuntimeTemperature(event.target.value)}
                  className="fx-field px-1 py-0.5 text-[10px]"
                />
              </label>
              <label className="col-span-2 flex flex-col gap-0.5 fx-muted">
                <span>session_id</span>
                <input
                  aria-label="Runtime session id"
                  value={sessionId}
                  onChange={(event) => setSessionId(event.target.value)}
                  className="fx-field px-1 py-0.5 text-[10px]"
                />
              </label>
            </div>
            <label className="mt-1 flex items-center gap-1 text-[var(--foreground)]">
              <input type="checkbox" checked={useMemory} onChange={(event) => setUseMemory(event.target.checked)} />
              <span>Enable memory context</span>
            </label>
            {!runtimePolicy.allow_runtime_engine_override && (
              <div className="mt-1 text-[9px] fx-muted">
                Engine override is disabled by platform policy; runs will use default engine ({runtimePolicy.default_runtime_engine}).
              </div>
            )}
            {runtimeStrategy === "hybrid" && (
              <div className="mt-1 text-[9px] fx-muted">
                Hybrid mode routes agent tasks by role: retrieval/tooling/orchestration/collaboration/default.
              </div>
            )}
            {runtimePolicy.allow_runtime_engine_override && effectiveRuntimeEngine !== "native" && selectedEngineProbe && !selectedEngineProbe.available && (
              <div className="mt-1 text-[9px] text-[var(--fx-warning)]">
                Selected engine dependencies are missing; runtime may fall back to compatibility mode or fail in strict mode.
              </div>
            )}
            <div className="mt-1 flex items-center justify-between">
              <span className="fx-muted">memory entries: {memoryCount}</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleRefreshMemory}
                  className="fx-btn-secondary px-2 py-0.5 text-[10px]"
                  disabled={memoryBusy}
                  aria-busy={memoryBusy}
                >
                  Refresh
                </button>
                <button
                  onClick={handleClearMemory}
                  className="fx-btn-warning px-2 py-0.5 text-[10px]"
                  disabled={memoryBusy}
                  aria-busy={memoryBusy}
                >
                  Clear
                </button>
              </div>
            </div>
          </div>

          <div className="mt-2 fx-panel p-1.5 text-[10px]">
            <div className="mb-1 flex items-center justify-between">
              <span className="fx-muted">Collaboration</span>
              <span className="font-mono text-[var(--foreground)]">v{collabVersion}</span>
            </div>
            <div className="mb-1 text-[var(--foreground)]">
              user={collabUserId.slice(-10)} role={collabRole} sync={collabSyncState}
            </div>
            <ul className="max-h-20 overflow-auto border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1">
              {collabParticipants.length === 0 ? (
                <li className="fx-muted">No active participants.</li>
              ) : (
                collabParticipants.map((participant) => (
                  <li key={participant.user_id} className="mb-1 border-b border-[var(--fx-border)] pb-1 last:mb-0 last:border-b-0 last:pb-0">
                    <div className="text-[var(--foreground)]">{participant.display_name}</div>
                    <div className="fx-muted">{participant.role} · {new Date(participant.last_seen_at).toLocaleTimeString()}</div>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="mt-2 fx-panel p-1.5 text-[10px]">
            <div className="mb-1 fx-muted">Observability</div>
            {observabilityDashboard ? (
              <>
                <div className="grid grid-cols-2 gap-1 text-[var(--foreground)]">
                  <div className="fx-panel p-1">runs: {observabilityDashboard.summary.total_runs}</div>
                  <div className="fx-panel p-1">tokens: {observabilityDashboard.summary.token_estimate}</div>
                  <div className="fx-panel p-1">cost: ${observabilityDashboard.summary.cost_estimate_usd.toFixed(4)}</div>
                  <div className="fx-panel p-1">latency avg: {observabilityDashboard.summary.average_latency_ms} ms</div>
                </div>
                <div className="mt-1 text-[9px] fx-muted">Recent runs</div>
                <ul className="max-h-20 overflow-auto border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1">
                  {observabilityDashboard.runs.map((run) => (
                    <li key={run.run_id} className="mb-1 border-b border-[var(--fx-border)] pb-1 last:mb-0 last:border-b-0 last:pb-0">
                      <button
                        className="w-full text-left"
                        onClick={async () => {
                          try {
                            const trace = await getObservabilityRunTrace(run.run_id);
                            setSelectedTrace(trace);
                          } catch {
                            setSelectedTrace(null);
                          }
                        }}
                      >
                        <div className="font-mono text-[var(--foreground)]">{run.run_id}</div>
                        <div className="fx-muted">{run.status} · {run.token_estimate ?? 0} tok · {run.duration_ms ?? 0} ms</div>
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <div className="fx-muted">No observability metrics yet.</div>
            )}

            {selectedTrace && (
              <div className="mt-1 border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-1">
                <div className="font-mono text-[var(--foreground)]">trace {selectedTrace.run_id}</div>
                <div className="fx-muted">status {selectedTrace.status}</div>
                <div className="mt-1 text-[var(--foreground)]">events {selectedTrace.event_count} · nodes {selectedTrace.node_count} · edges {selectedTrace.edge_count}</div>
              </div>
            )}
          </div>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
