import {
  AgentDefinition,
  AgentTemplate,
  ArtifactDetail,
  ArtifactSummary,
  AtfAlignmentReport,
  AuditEvent,
  CollaborationSession,
  GuardrailRuleSet,
  InboxItem,
  IntegrationDefinition,
  ObservabilityRunTrace,
  OperatorSession,
  PlaybookDefinition,
  PlatformVersionStatus,
  PlatformSettings,
  SecurityPolicyResponse,
  TemplateCatalogItem,
  WorkflowDefinition,
  WorkflowRunEvent,
  WorkflowRunSummary,
} from "@/types/frontier";
export type { ObservabilityRunTrace } from "@/types/frontier";

/* ------------------------------------------------------------------ */
/*  Configuration helpers                                              */
/* ------------------------------------------------------------------ */

function getApiBase(): string {
  if (typeof window === "undefined") {
    return process.env.API_BASE_URL_INTERNAL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  }

  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
}

function getRequestIdentityHeaders(): Record<string, string> {
  const actor = (process.env.NEXT_PUBLIC_FRONTIER_ACTOR ?? "").trim();
  const headers: Record<string, string> = {};
  if (actor) {
    headers["x-frontier-actor"] = actor;
  }
  return headers;
}

/* ------------------------------------------------------------------ */
/*  Retry with exponential backoff                                     */
/* ------------------------------------------------------------------ */

async function fetchWithRetry(
  url: string,
  init: RequestInit | undefined,
  retries = 2,
  baseDelayMs = 500,
): Promise<Response> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, init);
      // Retry on 502/503/504 (transient server errors)
      if (res.status >= 502 && res.status <= 504 && attempt < retries) {
        await delay(baseDelayMs * 2 ** attempt);
        continue;
      }
      return res;
    } catch (err) {
      lastError = err;
      if (attempt < retries) {
        await delay(baseDelayMs * 2 ** attempt);
      }
    }
  }
  throw lastError;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ------------------------------------------------------------------ */
/*  API connectivity tracking (client-side only)                       */
/* ------------------------------------------------------------------ */

type ApiStatusListener = (connected: boolean) => void;
const apiStatusListeners = new Set<ApiStatusListener>();
let lastApiConnected = true;

export function onApiStatusChange(listener: ApiStatusListener): () => void {
  apiStatusListeners.add(listener);
  return () => { apiStatusListeners.delete(listener); };
}

function setApiConnected(connected: boolean) {
  if (connected !== lastApiConnected) {
    lastApiConnected = connected;
    apiStatusListeners.forEach((fn) => fn(connected));
  }
}

type Json = Record<string, unknown> | unknown[];

type CacheEntry<T> = {
  value: T;
  expiresAt: number;
};

const responseCache = new Map<string, CacheEntry<unknown>>();
const EMPTY_WORKFLOWS: WorkflowDefinition[] = [];
const EMPTY_RUNS: WorkflowRunSummary[] = [];
const EMPTY_EVENTS: WorkflowRunEvent[] = [];
const EMPTY_INBOX: InboxItem[] = [];
const EMPTY_ARTIFACTS: ArtifactSummary[] = [];
const EMPTY_AGENTS: AgentDefinition[] = [];
const EMPTY_GUARDRAILS: GuardrailRuleSet[] = [];
const DEFAULT_RUN_DETAIL: WorkflowRunDetail = {
  artifacts: [],
  status: "Running",
  graph: { nodes: [], links: [] },
  agent_traces: [],
  approvals: { required: false, pending: false },
};

function readCachedValue<T>(cacheKey: string): T | null {
  const cached = responseCache.get(cacheKey);
  if (!cached) {
    return null;
  }
  if (cached.expiresAt <= Date.now()) {
    responseCache.delete(cacheKey);
    return null;
  }
  return cached.value as T;
}

function writeCachedValue<T>(cacheKey: string, value: T, ttlMs: number): T {
  responseCache.set(cacheKey, { value, expiresAt: Date.now() + ttlMs });
  return value;
}

const FRONTIER_GRAPH_SCHEMA_VERSION = "frontier-graph/1.0";

export type GraphCanvasPayload = {
  schema_version?: string;
  nodes: Array<{ id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> }>;
  links: Array<{ from: string; to: string; from_port?: string; to_port?: string }>;
  input?: Record<string, unknown>;
};

function withGraphSchemaVersion(payload: GraphCanvasPayload): GraphCanvasPayload {
  return {
    ...payload,
    schema_version: payload.schema_version ?? FRONTIER_GRAPH_SCHEMA_VERSION,
  };
}

export type RuntimeProvider = {
  provider: string;
  configured: boolean;
  model: string;
  mode: "live" | "simulated";
};

export type RuntimeFrameworkAdapterProbe = {
  engine: string;
  available: boolean;
  missing_modules: string[];
};

export type RuntimeProvidersResponse = {
  providers: RuntimeProvider[];
  framework_adapters?: Record<string, RuntimeFrameworkAdapterProbe>;
};

export type UserRuntimeProviderConfig = {
  provider: string;
  configured: boolean;
  model: string;
  base_url: string;
  api_key_masked: string;
  updated_at: string;
  source: "user" | "environment";
};

export type RuntimeEngineName = "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";

export type RuntimeStrategyName = "single" | "hybrid";

export type RuntimeHybridRole = "default" | "orchestration" | "retrieval" | "tooling" | "collaboration";

export type RuntimeHybridRouting = Partial<Record<RuntimeHybridRole, RuntimeEngineName>>;

export type PlatformRuntimePolicySettings = Pick<
  PlatformSettings,
  | "default_runtime_engine"
  | "default_runtime_strategy"
  | "default_hybrid_runtime_routing"
  | "allowed_runtime_engines"
  | "allow_runtime_engine_override"
  | "enforce_runtime_engine_allowlist"
>;

export type GraphValidationResponse = {
  valid: boolean;
  issues: Array<{ code: string; message: string; path: string }>;
};

export type GraphRunResponse = {
  run_id: string;
  status: "completed" | "failed";
  execution_order: string[];
  node_results: Record<string, Record<string, unknown>>;
  events: Array<{
    id: string;
    node_id: string;
    type: "node_started" | "node_completed" | "node_failed";
    title: string;
    summary: string;
    created_at: string;
  }>;
  validation: GraphValidationResponse;
  runtime?: {
    requested_engine?: string;
    selected_engine?: string;
    executed_engine?: string;
    mode?: string;
    strategy?: RuntimeStrategyName | string;
    allow_override?: boolean;
    allowed_engines?: string[];
    node_mapping?: Record<string, string>;
    adapter_probe?: {
      engine?: string;
      available?: boolean;
      missing_modules?: string[];
    };
    hybrid_routing?: RuntimeHybridRouting;
    hybrid_effective_routing?: RuntimeHybridRouting;
    hybrid_role_modes?: Partial<Record<RuntimeHybridRole, string>>;
    hybrid_resolution_notes?: string[];
    node_dispatches?: Array<{
      node_id: string;
      node_title?: string;
      role?: string;
      requested_engine?: string;
      executed_engine?: string;
      mode?: string;
    }>;
  };
};

export type MemorySessionResponse = {
  session_id: string;
  count: number;
  entries: Array<{ id: string; at: string; node_id: string; content: string }>;
};

export type IntegrationTestResponse = {
  ok: boolean;
  id: string;
  status: string;
  message: string;
  diagnostics?: {
    checks?: Record<string, boolean>;
    masked?: {
      base_url?: string;
      secret_ref?: string;
    };
    warnings?: string[];
  };
};

export type ObservabilityDashboardResponse = {
  summary: {
    total_runs: number;
    failed_or_blocked_runs: number;
    token_estimate: number;
    cost_estimate_usd: number;
    average_latency_ms: number;
  };
  runs: ObservabilityRunTrace[];
};

export type WorkflowRunDetail = {
  artifacts: ArtifactSummary[];
  status: string;
  graph?: {
    nodes: Array<{ id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> }>;
    links: Array<{ from: string; to: string; from_port?: string; to_port?: string }>;
  };
  agent_traces?: Array<{
    agent: string;
    reasoningSummary: string;
    actions: string[];
    output: string;
  }>;
  approvals?: {
    required?: boolean;
    pending?: boolean;
    artifact_id?: string;
    version?: number;
    scope?: string;
  };
};

async function safeFetch<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    const res = await fetchWithRetry(
      `${getApiBase()}${path}`,
      {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...getRequestIdentityHeaders(),
          ...(init?.headers ?? {}),
        },
        cache: "no-store",
      },
    );

    if (!res.ok) {
      setApiConnected(true); // Server reachable, just returned an error
      return fallback;
    }

    setApiConnected(true);
    return (await res.json()) as T;
  } catch {
    setApiConnected(false);
    return fallback;
  }
}

async function strictFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetchWithRetry(
    `${getApiBase()}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...getRequestIdentityHeaders(),
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    },
  );

  setApiConnected(true);

  if (!res.ok) {
    let details = "";
    try {
      details = await res.text();
    } catch {
      details = "";
    }
    throw new Error(`Request failed (${res.status})${details ? `: ${details}` : ""}`);
  }

  return (await res.json()) as T;
}

export async function getPublishedWorkflows(): Promise<WorkflowDefinition[]> {
  return safeFetch<WorkflowDefinition[]>("/workflows/published", EMPTY_WORKFLOWS);
}

export async function createWorkflowRun(
  payload: Json,
  options?: { timeoutMs?: number; signal?: AbortSignal },
): Promise<{ id: string; status: string }> {
  const timeoutMs = options?.timeoutMs ?? 120000;
  const timeoutController = new AbortController();
  const timeoutHandle = setTimeout(() => {
    timeoutController.abort(new Error("Run creation is taking longer than expected"));
  }, timeoutMs);

  const abortForwarder = () => timeoutController.abort(options?.signal?.reason);
  options?.signal?.addEventListener("abort", abortForwarder, { once: true });

  try {
    const res = await fetch(`${getApiBase()}/workflow-runs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getRequestIdentityHeaders(),
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: timeoutController.signal,
    });

    if (!res.ok) {
      let details = "";
      try {
        details = await res.text();
      } catch {
        details = "";
      }
      throw new Error(`Failed to create run (${res.status})${details ? `: ${details}` : ""}`);
    }

    return (await res.json()) as { id: string; status: string };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Run creation timed out after ${Math.round(timeoutMs / 1000)}s. The model/backend may still be processing; please retry in a moment.`);
    }
    if (error instanceof Error && /taking longer than expected/i.test(error.message)) {
      throw new Error(`Run creation timed out after ${Math.round(timeoutMs / 1000)}s. The model/backend may still be processing; please retry in a moment.`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutHandle);
    options?.signal?.removeEventListener("abort", abortForwarder);
  }
}

export async function getWorkflowRuns(status?: string): Promise<WorkflowRunSummary[]> {
  const suffix = status ? `?status=${encodeURIComponent(status)}` : "";
  const cacheKey = `workflow-runs:${status ?? "all"}`;
  const cached = readCachedValue<WorkflowRunSummary[]>(cacheKey);
  if (cached) {
    return cached;
  }
  const value = await safeFetch<WorkflowRunSummary[]>(`/workflow-runs${suffix}`, EMPTY_RUNS);
  return writeCachedValue(cacheKey, value, 5000);
}

export async function getWorkflowRun(_id: string): Promise<WorkflowRunDetail> {
  const cacheKey = `workflow-run:${_id}`;
  const cached = readCachedValue<WorkflowRunDetail>(cacheKey);
  if (cached) {
    return cached;
  }
  const value = await safeFetch<WorkflowRunDetail>(`/workflow-runs/${_id}`, DEFAULT_RUN_DETAIL);
  return writeCachedValue(cacheKey, value, 1500);
}

export async function getWorkflowRunEvents(id: string): Promise<WorkflowRunEvent[]> {
  const cacheKey = `workflow-run-events:${id}`;
  const cached = readCachedValue<WorkflowRunEvent[]>(cacheKey);
  if (cached) {
    return cached;
  }
  const value = await safeFetch<WorkflowRunEvent[]>(`/workflow-runs/${id}/events`, EMPTY_EVENTS);
  return writeCachedValue(cacheKey, value, 1500);
}

export function streamWorkflowRun(
  id: string,
  handlers: {
    onMessage: (event: { id: string; type: string; createdAt: string; payload: Record<string, unknown> }) => void;
    onError?: () => void;
  },
): () => void {
  const controller = new AbortController();
  void (async () => {
    try {
      const res = await fetch(`${getApiBase()}/workflow-runs/${encodeURIComponent(id)}/stream`, {
        method: "GET",
        headers: {
          ...getRequestIdentityHeaders(),
        },
        cache: "no-store",
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        handlers.onError?.();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame
            .split("\n")
            .find((candidate) => candidate.startsWith("data:"));
          if (!line) {
            continue;
          }
          try {
            handlers.onMessage(
              JSON.parse(line.slice(5).trim()) as {
                id: string;
                type: string;
                createdAt: string;
                payload: Record<string, unknown>;
              },
            );
          } catch {
            handlers.onError?.();
          }
        }
      }
    } catch {
      if (!controller.signal.aborted) {
        handlers.onError?.();
      }
    }
  })();
  return () => {
    controller.abort();
  };
}

export async function archiveWorkflowRun(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/workflow-runs/${id}/archive`, { method: "POST" });
}

export async function createArtifactVersion(
  id: string,
  payload: Json,
): Promise<{ ok: boolean; artifactId: string }> {
  return strictFetch(`/artifacts/${id}/versions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitApproval(payload: Json): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>("/approvals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getInbox(): Promise<InboxItem[]> {
  const cached = readCachedValue<InboxItem[]>("inbox");
  if (cached) {
    return cached;
  }
  const value = await safeFetch<InboxItem[]>("/inbox", EMPTY_INBOX);
  return writeCachedValue("inbox", value, 5000);
}

export async function getArtifacts(): Promise<ArtifactSummary[]> {
  return safeFetch<ArtifactSummary[]>("/artifacts", EMPTY_ARTIFACTS);
}

export async function getArtifact(id: string): Promise<ArtifactDetail | null> {
  return safeFetch<ArtifactDetail | null>(`/artifacts/${id}`, null);
}

// Builder mode endpoints
export async function getWorkflowDefinitions(): Promise<WorkflowDefinition[]> {
  return safeFetch<WorkflowDefinition[]>("/workflow-definitions", EMPTY_WORKFLOWS);
}

export async function saveWorkflowDefinition(payload: Json): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>("/workflow-definitions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function publishWorkflowDefinition(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/workflow-definitions/${id}/publish`, { method: "POST" });
}

export async function archiveWorkflowDefinition(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/workflow-definitions/${id}/archive`, { method: "POST" });
}

export async function deleteWorkflowDefinition(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/workflow-definitions/${id}`, { method: "DELETE" });
}

export async function getAgentDefinitions(): Promise<AgentDefinition[]> {
  return safeFetch<AgentDefinition[]>("/agent-definitions", EMPTY_AGENTS);
}

export async function getAgentDefinition(id: string): Promise<AgentDefinition | null> {
  return safeFetch<AgentDefinition | null>(`/agent-definitions/${id}`, null);
}

export async function saveAgentDefinition(payload: Json): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>("/agent-definitions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function publishAgentDefinition(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/agent-definitions/${id}/publish`, { method: "POST" });
}

export async function deleteAgentDefinition(id: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/agent-definitions/${id}`, { method: "DELETE" });
}

export async function getNodeDefinitions(options?: { includeInternal?: boolean }): Promise<Array<{ type_key: string; title?: string; description: string; category?: string; color?: string }>> {
  const suffix = options?.includeInternal ? "?include_internal=true" : "";
  return safeFetch(`/node-definitions${suffix}`, [
    { type_key: "frontier/trigger", title: "Trigger", description: "Workflow trigger/intake node", category: "Core", color: "#6ca0ff" },
    { type_key: "frontier/agent", title: "Agent", description: "Delegates to a selected agent definition", category: "Agent", color: "#1f7f53" },
    { type_key: "frontier/prompt", title: "Prompt", description: "Compose reusable system prompt instructions and pass them to agent nodes", category: "Agent", color: "#5f4bb6" },
    { type_key: "frontier/tool-call", title: "Tool / API Call", description: "Invokes external API or tool", category: "Integration", color: "#6fd3ff" },
    { type_key: "frontier/retrieval", title: "Retrieval", description: "Retrieves ranked context", category: "Knowledge", color: "#8a6717" },
    { type_key: "frontier/guardrail", title: "Guardrail", description: "Checks content against guardrail rules", category: "Control", color: "#9f3550" },
    { type_key: "frontier/human-review", title: "Human Review", description: "Requires human approval before next step", category: "Control", color: "#8d5c1a" },
    { type_key: "frontier/manifold", title: "Manifold", description: "Consolidates multiple inbound flows via AND/OR logic", category: "Logic", color: "#7863d3" },
    { type_key: "frontier/output", title: "Output", description: "Final output emission", category: "Core", color: "#69a3ff" },
  ]);
}

export async function getGuardrailRulesets(): Promise<GuardrailRuleSet[]> {
  return safeFetch<GuardrailRuleSet[]>("/guardrail-rulesets", EMPTY_GUARDRAILS);
}

export async function getWorkflowSecurityPolicy(workflowId: string): Promise<SecurityPolicyResponse> {
  return safeFetch<SecurityPolicyResponse>(`/workflows/${workflowId}/security-policy`, {
    immutable_baseline: {} as SecurityPolicyResponse["immutable_baseline"],
    platform_defaults: {} as SecurityPolicyResponse["platform_defaults"],
    workflow_overrides: {},
    agent_overrides: {},
    effective: {} as SecurityPolicyResponse["effective"],
  });
}

export async function getAgentSecurityPolicy(agentId: string): Promise<SecurityPolicyResponse> {
  return safeFetch<SecurityPolicyResponse>(`/agents/${agentId}/security-policy`, {
    immutable_baseline: {} as SecurityPolicyResponse["immutable_baseline"],
    platform_defaults: {} as SecurityPolicyResponse["platform_defaults"],
    workflow_overrides: {},
    agent_overrides: {},
    effective: {} as SecurityPolicyResponse["effective"],
  });
}

export async function saveGuardrailRuleset(payload: Json): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>("/guardrail-rulesets", { ok: true }, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function publishGuardrailRuleset(id: string): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>(`/guardrail-rulesets/${id}/publish`, { ok: true }, { method: "POST" });
}

export async function deleteGuardrailRuleset(id: string): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>(`/guardrail-rulesets/${id}`, { ok: true }, { method: "DELETE" });
}

export async function deleteNodeDefinition(id: string): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>(`/node-definitions/${id}`, { ok: true }, { method: "DELETE" });
}

export async function validateGraph(payload: GraphCanvasPayload): Promise<GraphValidationResponse> {
  return safeFetch<GraphValidationResponse>(
    "/graph/validate",
    { valid: true, issues: [] },
    {
      method: "POST",
      body: JSON.stringify(withGraphSchemaVersion(payload)),
    },
  );
}

export async function runGraph(payload: GraphCanvasPayload): Promise<GraphRunResponse> {
  return safeFetch<GraphRunResponse>(
    "/graph/runs",
    {
      run_id: "local-fallback-run",
      status: "completed",
      execution_order: payload.nodes.map((node) => node.id),
      node_results: {},
      events: [],
      validation: { valid: true, issues: [] },
      runtime: {
        requested_engine: "native",
        selected_engine: "native",
        executed_engine: "native",
        mode: "native",
        allow_override: false,
        allowed_engines: ["native"],
      },
    },
    {
      method: "POST",
      body: JSON.stringify(withGraphSchemaVersion(payload)),
    },
  );
}

export async function getRuntimeProviders(): Promise<RuntimeProvidersResponse> {
  return safeFetch<RuntimeProvidersResponse>("/runtime/providers", {
    providers: [
      {
        provider: "openai",
        configured: false,
        model: "gpt-5.2",
        mode: "simulated",
      },
    ],
    framework_adapters: {
      langgraph: { engine: "langgraph", available: false, missing_modules: ["langgraph", "langchain_openai"] },
      langchain: { engine: "langchain", available: false, missing_modules: ["langchain_core", "langchain_openai"] },
      "semantic-kernel": { engine: "semantic-kernel", available: false, missing_modules: ["semantic_kernel"] },
      autogen: { engine: "autogen", available: false, missing_modules: ["autogen_agentchat|autogen"] },
    },
  });
}

export async function getUserRuntimeProviders(): Promise<UserRuntimeProviderConfig[]> {
  return safeFetch<UserRuntimeProviderConfig[]>("/runtime/user-providers", []);
}

export async function saveUserRuntimeProvider(
  provider: string,
  payload: { api_key?: string; model?: string; base_url?: string },
): Promise<UserRuntimeProviderConfig> {
  return strictFetch<UserRuntimeProviderConfig>(
    `/runtime/user-providers/${encodeURIComponent(provider)}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    },
  );
}

export async function deleteUserRuntimeProvider(provider: string): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>(`/runtime/user-providers/${encodeURIComponent(provider)}`, {
    method: "DELETE",
  });
}

export async function getMemorySession(sessionId: string): Promise<MemorySessionResponse> {
  return safeFetch<MemorySessionResponse>(`/memory/${encodeURIComponent(sessionId)}`, {
    session_id: sessionId,
    count: 0,
    entries: [],
  });
}

export async function clearMemorySession(sessionId: string): Promise<{ ok: boolean; session_id: string }> {
  return strictFetch<{ ok: boolean; session_id: string }>(
    `/memory/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

export async function getPlatformSettings(): Promise<PlatformSettings> {
  const cached = readCachedValue<PlatformSettings>("platform-settings");
  if (cached) {
    return cached;
  }
  const value = await safeFetch<PlatformSettings>("/platform/settings", {
    org_name: "Lattix xFrontier",
    org_slug: "lattix-frontier",
    support_email: "support@lattix.io",
    website: "https://lattix.io",
    default_kickoff_workflow: "Auto-select from intent",
    preferred_review_depth: "Standard",
    idle_timeout: "30 minutes",
    local_only_mode: true,
    mask_secrets_in_events: true,
    require_human_approval: false,
    require_human_approval_for_high_risk_tools: true,
    emergency_read_only_mode: false,
    block_new_runs: false,
    block_graph_runs: false,
    block_tool_calls: false,
    block_retrieval_calls: false,
    require_authenticated_requests: false,
    require_a2a_runtime_headers: false,
    a2a_require_signed_messages: true,
    a2a_replay_protection: true,
    default_guardrail_ruleset_id: null,
    global_blocked_keywords: [],
    collaboration_max_agents: 8,
    max_tool_calls_per_run: 8,
    max_retrieval_items: 8,
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
    enforce_egress_allowlist: false,
    allowed_egress_hosts: [],
    enforce_local_network_only: true,
    allow_local_network_hostnames: true,
    allowed_retrieval_sources: [],
    retrieval_require_local_source_url: true,
    allowed_mcp_server_urls: [],
    mcp_require_local_server: true,
    high_risk_tool_patterns: [],
    enable_foss_guardrail_signals: true,
    foss_guardrail_signal_enforcement: "block_high",
  });
  return writeCachedValue("platform-settings", value, 30000);
}

export async function getOperatorSession(): Promise<OperatorSession> {
  const cached = readCachedValue<OperatorSession>("operator-session");
  if (cached) {
    return cached;
  }
  const value = await safeFetch<OperatorSession>("/auth/session", {
    authenticated: false,
    actor: "anonymous",
    principal_id: "anonymous",
    principal_type: "user",
    display_name: "Anonymous",
    subject: "",
    email: "",
    preferred_username: "",
    auth_mode: "shared-token",
    provider: "",
    roles: [],
    capabilities: {
      can_admin: false,
      can_builder: false,
    },
    allowed_modes: ["user"],
    default_mode: "user",
    oidc: {
      configured: false,
      issuer: "",
      audience: "",
      provider: "",
      validation_error: "",
    },
  });
  return writeCachedValue("operator-session", value, 15000);
}

export async function loginWithLocalPassword(payload: {
  username: string;
  password: string;
}): Promise<{ ok: boolean; authenticated: boolean; provider: string; mode: string }> {
  return strictFetch<{ ok: boolean; authenticated: boolean; provider: string; mode: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function registerWithLocalPassword(payload: {
  username: string;
  email: string;
  display_name: string;
  password: string;
}): Promise<{ ok: boolean; authenticated: boolean; provider: string; mode: string; created: boolean }> {
  return strictFetch<{ ok: boolean; authenticated: boolean; provider: string; mode: string; created: boolean }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logoutOperator(): Promise<{ ok: boolean }> {
  return strictFetch<{ ok: boolean }>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getPlatformVersionStatus(): Promise<PlatformVersionStatus> {
  const cached = readCachedValue<PlatformVersionStatus>("platform-version");
  if (cached) {
    return cached;
  }
  const value = await safeFetch<PlatformVersionStatus>("/platform/version", {
    current_version: "0.0.0",
    latest_version: "0.0.0",
    update_available: false,
    status: "unknown",
    install_mode: "wheel",
    update_command: "lattix update",
    release_notes_url: "",
    checked_at: new Date().toISOString(),
    source: "",
    summary: "Version metadata is unavailable right now.",
  });
  return writeCachedValue("platform-version", value, 30000);
}

export async function getPlatformSecurityPolicy(): Promise<SecurityPolicyResponse> {
  return safeFetch<SecurityPolicyResponse>("/platform/security-policy", {
    immutable_baseline: {
      enforce_capability_filter: true,
      enforce_policy_gate: true,
      fail_closed_policy_decisions: true,
      enforce_signed_a2a_messages: true,
      enforce_a2a_replay_protection: true,
      require_readonly_rootfs_for_sandbox: true,
      require_non_root_sandbox_user: true,
      require_egress_mediation_when_network_enabled: true,
      allow_filter_chain_reordering: false,
      allow_custom_policy_code: false,
    },
    platform_defaults: {
      classification: "internal",
      guardrail_ruleset_id: null,
      blocked_keywords: [],
      allowed_egress_hosts: [],
      allowed_retrieval_sources: [],
      allowed_mcp_server_urls: [],
      allowed_runtime_engines: ["native"],
      allowed_memory_scopes: ["run", "session", "user", "tenant", "agent", "workflow", "global"],
      max_tool_calls_per_run: 8,
      max_retrieval_items: 8,
      max_collaboration_agents: 8,
      require_human_approval: false,
      require_human_approval_for_high_risk_tools: true,
      allow_runtime_override: false,
      enable_platform_signals: true,
      platform_signal_enforcement: "block_high",
    },
    workflow_overrides: {},
    agent_overrides: {},
    effective: {
      classification: "internal",
      guardrail_ruleset_id: null,
      blocked_keywords: [],
      allowed_egress_hosts: [],
      allowed_retrieval_sources: [],
      allowed_mcp_server_urls: [],
      allowed_runtime_engines: ["native"],
      allowed_memory_scopes: ["run", "session", "user", "tenant", "agent", "workflow", "global"],
      max_tool_calls_per_run: 8,
      max_retrieval_items: 8,
      max_collaboration_agents: 8,
      require_human_approval: false,
      require_human_approval_for_high_risk_tools: true,
      allow_runtime_override: false,
      enable_platform_signals: true,
      platform_signal_enforcement: "block_high",
    },
    backend_enforced_controls: [],
    configurable_controls: [],
  });
}

export async function savePlatformSettings(payload: Json): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>("/platform/settings", { ok: true }, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAgentTemplates(): Promise<AgentTemplate[]> {
  return safeFetch<AgentTemplate[]>("/templates/agents", []);
}

export async function getTemplateCatalog(): Promise<TemplateCatalogItem[]> {
  return safeFetch<TemplateCatalogItem[]>("/templates/catalog", []);
}

export async function instantiateAgentTemplate(templateId: string, payload: Json): Promise<{ ok: boolean; id: string }> {
  return strictFetch<{ ok: boolean; id: string }>(`/templates/agents/${templateId}/instantiate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function instantiateWorkflowTemplate(workflowId: string, payload: Json): Promise<{ ok: boolean; id: string }> {
  return strictFetch<{ ok: boolean; id: string }>(`/templates/workflows/${workflowId}/instantiate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPlaybooks(): Promise<PlaybookDefinition[]> {
  return safeFetch<PlaybookDefinition[]>("/playbooks", []);
}

export async function getPlaybook(id: string): Promise<PlaybookDefinition | null> {
  return safeFetch<PlaybookDefinition | null>(`/playbooks/${id}`, null);
}

export async function instantiatePlaybook(playbookId: string, payload: Json): Promise<{ ok: boolean; id: string }> {
  return strictFetch<{ ok: boolean; id: string }>(`/playbooks/${playbookId}/instantiate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getObservabilityRunTrace(runId: string): Promise<ObservabilityRunTrace | null> {
  return safeFetch<ObservabilityRunTrace | null>(`/observability/runs/${runId}/trace`, null);
}

export async function getObservabilityDashboard(): Promise<ObservabilityDashboardResponse> {
  return safeFetch<ObservabilityDashboardResponse>("/observability/dashboard", {
    summary: {
      total_runs: 0,
      failed_or_blocked_runs: 0,
      token_estimate: 0,
      cost_estimate_usd: 0,
      average_latency_ms: 0,
    },
    runs: [],
  });
}

export async function getAuditEvents(limit = 200): Promise<{ count: number; events: AuditEvent[] }> {
  const bounded = Math.max(1, Math.min(1000, Math.trunc(limit)));
  return safeFetch<{ count: number; events: AuditEvent[] }>(`/audit/events?limit=${bounded}`, {
    count: 0,
    events: [],
  });
}

export async function getAtfAlignmentReport(): Promise<AtfAlignmentReport> {
  return safeFetch<AtfAlignmentReport>("/audit/atf-alignment-report", {
    generated_at: new Date().toISOString(),
    framework: "CSA Agentic Trust Framework",
    coverage_percent: 0,
    maturity_estimate: "intern",
    pillars: {
      identity: { status: "partial", controls: {}, gaps: [] },
      behavior_monitoring: { status: "partial", controls: {}, gaps: [] },
      data_governance: { status: "partial", controls: {}, gaps: [] },
      segmentation: { status: "partial", controls: {}, gaps: [] },
      incident_response: { status: "partial", controls: {}, gaps: [] },
    },
    evidence: {
      audit_window_hours: 24,
      audit_event_count_24h: 0,
      audit_allowed_24h: 0,
      audit_blocked_24h: 0,
      audit_error_24h: 0,
      total_audit_events: 0,
      run_count_total: 0,
    },
  });
}

export async function joinCollaborationSession(payload: {
  entity_type: "agent" | "workflow";
  entity_id: string;
  user_id?: string;
  principal_id?: string;
  principal_type?: "user" | "agent" | "service" | "npe";
  auth_subject?: string;
  display_name: string;
  role?: "owner" | "editor" | "viewer";
}): Promise<{ ok: boolean; session: CollaborationSession; participant: { user_id: string; principal_id?: string; principal_type?: "user" | "agent" | "service" | "npe"; auth_subject?: string | null; display_name: string; role: "owner" | "editor" | "viewer" } }> {
  return strictFetch("/collab/sessions/join", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCollaborationSession(sessionId: string): Promise<CollaborationSession | null> {
  return safeFetch<CollaborationSession | null>(`/collab/sessions/${encodeURIComponent(sessionId)}`, null);
}

export async function syncCollaborationSession(
  sessionId: string,
  payload: {
    user_id?: string;
    principal_id?: string;
    base_version?: number;
    graph_json?: GraphCanvasPayload;
    force?: boolean;
  },
): Promise<{ ok: boolean; conflict?: boolean; message?: string; version: number; graph_json: GraphCanvasPayload; updated_at: string }> {
  return strictFetch(`/collab/sessions/${encodeURIComponent(sessionId)}/sync`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateCollaborationPermissions(
  sessionId: string,
  payload: {
    actor_user_id?: string;
    actor_principal_id?: string;
    target_user_id?: string;
    target_principal_id?: string;
    role: "owner" | "editor" | "viewer";
  },
): Promise<{ ok: boolean; session: CollaborationSession }> {
  return strictFetch(`/collab/sessions/${encodeURIComponent(sessionId)}/permissions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getIntegrations(): Promise<IntegrationDefinition[]> {
  return safeFetch<IntegrationDefinition[]>("/integrations", []);
}

export async function saveIntegration(payload: Json): Promise<{ ok: boolean; id: string }> {
  return safeFetch<{ ok: boolean; id: string }>("/integrations", { ok: true, id: "" }, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function testIntegration(id: string): Promise<IntegrationTestResponse> {
  return safeFetch<IntegrationTestResponse>(
    `/integrations/${id}/test`,
    { ok: false, id, status: "error", message: "Unable to test integration", diagnostics: { warnings: ["Backend unavailable"] } },
    { method: "POST" },
  );
}

export async function deleteIntegration(id: string): Promise<{ ok: boolean }> {
  return safeFetch<{ ok: boolean }>(`/integrations/${id}`, { ok: true }, { method: "DELETE" });
}
