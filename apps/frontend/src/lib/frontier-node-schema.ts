export type WidgetSpec = {
  key: string;
  label: string;
  kind: "text" | "number" | "combo" | "toggle";
  defaultValue: string | number | boolean;
  options?: string[];
  multiline?: boolean;
  help?: string;
  placeholder?: string;
};

export type PortSpec = {
  name: string;
  type: string;
};

type NodeSchema = {
  inputs: PortSpec[];
  outputs: PortSpec[];
  defaults: Record<string, unknown>;
  widgets: WidgetSpec[];
  inputAliases?: Record<string, string>;
  outputAliases?: Record<string, string>;
};

function normalizeBaseNodeType(type: string): string {
  if (type.startsWith("frontier/")) {
    return type.slice("frontier/".length);
  }
  if (type.startsWith("agent/")) {
    return "agent";
  }
  return type;
}

const SCHEMAS: Record<string, NodeSchema> = {
  trigger: {
    inputs: [{ name: "in", type: "flow" }],
    outputs: [
      { name: "out", type: "flow" },
      { name: "payload", type: "data" },
    ],
    defaults: {
      trigger_mode: "manual",
      schedule_preset: "daily",
      schedule_time: "09:00",
      schedule_day_of_week: "1",
      schedule_day_of_month: "1",
      default_message: "",
      schedule_cron: "0 9 * * 1-5",
      schedule_timezone: "UTC",
      webhook_path: "/hooks/frontier/trigger",
      webhook_secret_ref: "",
      api_event_name: "event.workflow.start",
      tool_event_name: "tool.completed",
      human_queue: "needs-review",
      tags: [],
    },
    widgets: [
      {
        key: "trigger_mode",
        label: "trigger_mode",
        kind: "combo",
        defaultValue: "manual",
        options: ["manual", "schedule", "webhook", "api_event", "tool_event", "human_feedback"],
        help: "How this workflow starts. Manual = click run. Schedule = time-based. Webhook/API/tool/human modes trigger from external events.",
      },
      {
        key: "schedule_preset",
        label: "schedule_preset",
        kind: "combo",
        defaultValue: "daily",
        options: ["hourly", "daily", "weekdays", "weekends", "weekly", "monthly", "custom"],
        help: "Human-friendly schedule choice. Use custom only when you need an advanced CRON expression.",
      },
      {
        key: "schedule_time",
        label: "schedule_time (HH:MM)",
        kind: "text",
        defaultValue: "09:00",
        placeholder: "09:00",
        help: "Local time used by non-hourly presets (24-hour format). Example: 17:30.",
      },
      {
        key: "schedule_day_of_week",
        label: "schedule_day_of_week",
        kind: "combo",
        defaultValue: "1",
        options: ["0", "1", "2", "3", "4", "5", "6"],
        help: "Used by weekly preset. 0=Sunday, 1=Monday ... 6=Saturday.",
      },
      {
        key: "schedule_day_of_month",
        label: "schedule_day_of_month",
        kind: "combo",
        defaultValue: "1",
        options: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28"],
        help: "Used by monthly preset. Pick day 1-28 for consistent monthly schedules.",
      },
      {
        key: "schedule_cron",
        label: "schedule_cron",
        kind: "text",
        defaultValue: "0 9 * * 1-5",
        placeholder: "0 9 * * 1-5",
        help: "Advanced fallback schedule format. Prefer schedule presets unless you need custom expressions.",
      },
      {
        key: "schedule_timezone",
        label: "schedule_timezone",
        kind: "combo",
        defaultValue: "UTC",
        options: ["UTC", "America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London"],
        help: "Timezone used when translating schedule presets/time into runtime schedule behavior.",
      },
      {
        key: "webhook_path",
        label: "webhook_path",
        kind: "text",
        defaultValue: "/hooks/frontier/trigger",
        help: "Path endpoint for webhook trigger mode.",
      },
      {
        key: "webhook_secret_ref",
        label: "webhook_secret_ref",
        kind: "text",
        defaultValue: "",
        help: "Secret reference used to verify webhook signatures.",
      },
      {
        key: "api_event_name",
        label: "api_event_name",
        kind: "text",
        defaultValue: "event.workflow.start",
        help: "Event key listened to in api_event mode.",
      },
      {
        key: "tool_event_name",
        label: "tool_event_name",
        kind: "text",
        defaultValue: "tool.completed",
        help: "Event name listened to in tool_event mode.",
      },
      {
        key: "human_queue",
        label: "human_queue",
        kind: "text",
        defaultValue: "needs-review",
        help: "Queue/channel to listen to in human_feedback mode.",
      },
    ],
    outputAliases: { output: "out", message: "payload" },
  },
  prompt: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "context", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "prompt", type: "prompt" },
    ],
    defaults: {
      objective: "general_assistant",
      style: "concise",
      audience: "technical",
      safety_level: "balanced",
      include_citations: false,
      system_prompt_text: "",
    },
    widgets: [
      {
        key: "objective",
        label: "objective",
        kind: "combo",
        defaultValue: "general_assistant",
        options: ["general_assistant", "agent_execution", "research", "planning", "compliance", "summarization", "code_review", "incident_response", "sales_support", "knowledge_extraction", "creative_writing"],
        help: "Primary outcome this system prompt should optimize. Used to shape planning and response framing.",
      },
      {
        key: "style",
        label: "style",
        kind: "combo",
        defaultValue: "concise",
        options: ["concise", "detailed", "executive", "step_by_step", "socratic", "instructional", "evidence_based", "policy_aligned"],
        help: "Communication style only. Example: policy_aligned means wording aligns to policy language, but does NOT replace guardrail enforcement.",
      },
      {
        key: "audience",
        label: "audience",
        kind: "combo",
        defaultValue: "technical",
        options: ["operator", "technical", "executive", "customer", "analyst", "developer", "security", "compliance", "legal", "sales", "finance", "hr", "general_public"],
        help: "Intended reader persona. This controls wording depth, jargon level, and output framing.",
      },
      {
        key: "safety_level",
        label: "safety_level",
        kind: "combo",
        defaultValue: "balanced",
        options: ["very_strict", "strict", "high", "balanced", "moderate", "permissive"],
        help: "Prompt steering strictness. This influences generation behavior only; guardrail node still performs enforceable policy checks.",
      },
      {
        key: "include_citations",
        label: "include_citations",
        kind: "toggle",
        defaultValue: false,
        help: "When enabled, asks model to add source/citation notes when factual claims are made.",
      },
      {
        key: "system_prompt_text",
        label: "system_prompt_text",
        kind: "text",
        defaultValue: "",
        multiline: true,
        help: "Primary system prompt content fed into downstream agent runtime via the prompt port.",
      },
    ],
    inputAliases: { data: "context" },
    outputAliases: { output: "prompt", system_prompt: "prompt" },
  },
  agent: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "prompt", type: "prompt" },
      { name: "guardrail", type: "guardrail" },
      { name: "memory", type: "memory" },
      { name: "context", type: "data" },
      { name: "retrieval", type: "retrieval" },
      { name: "tool_result", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "response", type: "data" },
      { name: "retrieval_query", type: "data" },
      { name: "tool_request", type: "tool" },
      { name: "state_delta", type: "data" },
      { name: "memory", type: "memory" },
      { name: "guardrail", type: "guardrail" },
    ],
    defaults: {
      agent_id: "",
      role: "",
      model: "gpt-5.2",
      temperature: 0.2,
      max_steps: 8,
      timeout_ms: 45000,
      execution_mode: "sync",
      system_prompt: "",
    },
    widgets: [
      { key: "agent_id", label: "agent_id", kind: "text", defaultValue: "", help: "Target agent identity to execute. Usually maps to seeded agent definitions." },
      { key: "role", label: "role", kind: "combo", defaultValue: "general", options: ["general", "planner", "executor", "reviewer", "specialist"], help: "High-level runtime role hint used for execution behavior framing." },
      { key: "model", label: "model", kind: "combo", defaultValue: "gpt-5.2", options: ["gpt-5.2", "gpt-5.2-mini", "gpt-4.1", "gpt-4.1-mini"], help: "Model used for generation in this node runtime." },
      { key: "temperature", label: "temperature", kind: "number", defaultValue: 0.2, help: "Randomness control. Lower is more deterministic; higher is more creative." },
      { key: "max_steps", label: "max_steps", kind: "number", defaultValue: 8, help: "Bound on iterative reasoning/delegation steps for this runtime node." },
      { key: "timeout_ms", label: "timeout_ms", kind: "number", defaultValue: 45000, help: "Execution timeout per node run in milliseconds. Increase for long-running tasks." },
      { key: "execution_mode", label: "execution_mode", kind: "combo", defaultValue: "sync", options: ["sync", "async"], help: "sync waits for completion in-line; async is intended for background/deferred execution semantics." },
      { key: "system_prompt", label: "system_prompt", kind: "text", defaultValue: "", multiline: true, help: "Inline prompt fallback. If a prompt node is connected, connected prompt typically takes precedence depending on runtime composition order." },
    ],
    outputAliases: { output: "out", tool_api: "tool_request", query: "retrieval_query", request: "tool_request" },
  },
  "tool-call": {
    inputs: [
      { name: "in", type: "flow" },
      { name: "request", type: "tool" },
      { name: "auth_context", type: "data" },
      { name: "context", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "result", type: "data" },
      { name: "status", type: "data" },
      { name: "guardrail", type: "guardrail" },
    ],
    defaults: { tool_id: "tool/unspecified", method: "POST", timeout_ms: 30000, retry_count: 2 },
    widgets: [
      { key: "tool_id", label: "tool_id", kind: "combo", defaultValue: "tool/unspecified", options: ["tool/unspecified", "tool/search", "tool/http", "tool/retrieval", "tool/code", "tool/sql", "tool/file", "tool/email", "tool/slack", "tool/mcp"], help: "Tool or integration identifier to invoke." },
      { key: "method", label: "method", kind: "combo", defaultValue: "POST", options: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], help: "HTTP verb for API-style tools." },
      { key: "endpoint_url", label: "endpoint_url", kind: "text", defaultValue: "", help: "Target endpoint URL. Must pass egress allowlist policies at runtime." },
      { key: "auth_type", label: "auth_type", kind: "combo", defaultValue: "none", options: ["none", "api_key", "bearer", "oauth2", "basic", "mcp_token"], help: "Authentication strategy to apply for outbound call auth context." },
      { key: "auth_secret_ref", label: "auth_secret_ref", kind: "text", defaultValue: "", help: "Secret reference (not raw secret) used to resolve credentials at runtime." },
      { key: "input_schema", label: "input_schema", kind: "text", defaultValue: "", multiline: true, help: "Optional JSON schema or contract notes for expected input payload shape." },
      { key: "mcp_server_url", label: "mcp_server_url", kind: "text", defaultValue: "", help: "MCP endpoint URL. Must be approved by platform allowed_mcp_server_urls." },
      { key: "mcp_tool_name", label: "mcp_tool_name", kind: "text", defaultValue: "", help: "Tool/function name exposed by the MCP server." },
      { key: "timeout_ms", label: "timeout_ms", kind: "number", defaultValue: 30000, help: "Max tool execution time in milliseconds." },
      { key: "retry_count", label: "retry_count", kind: "number", defaultValue: 2, help: "Retry attempts for transient failures." },
    ],
    inputAliases: { tool_input: "request", data: "context" },
    outputAliases: { output: "out", tool_output: "result" },
  },
  retrieval: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "query", type: "data" },
      { name: "filters", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "documents", type: "retrieval" },
      { name: "grounding_context", type: "data" },
    ],
    defaults: { source_type: "hybrid", top_k: 5, score_threshold: 0.2 },
    widgets: [
      { key: "source_type", label: "source_type", kind: "combo", defaultValue: "hybrid", options: ["vector", "keyword", "hybrid", "semantic", "graph", "sql", "api"], help: "Retrieval strategy/backend type. hybrid typically combines lexical + vector retrieval." },
      { key: "source_id", label: "source_id", kind: "text", defaultValue: "kb://default", help: "Registered retrieval source identifier (allowlisted on backend)." },
      { key: "source_url", label: "source_url", kind: "text", defaultValue: "", help: "Optional direct retrieval endpoint URL if your retrieval adapter is API-backed." },
      { key: "auth_type", label: "auth_type", kind: "combo", defaultValue: "none", options: ["none", "api_key", "bearer", "oauth2", "basic"], help: "Authentication strategy for retrieval endpoint access when needed." },
      { key: "auth_secret_ref", label: "auth_secret_ref", kind: "text", defaultValue: "", help: "Secret reference for retrieval auth credentials." },
      { key: "index_name", label: "index_name", kind: "text", defaultValue: "", help: "Index/collection/table name for retrieval engines (e.g., vector DB index)." },
      { key: "top_k", label: "top_k", kind: "number", defaultValue: 5, help: "Maximum number of documents/chunks returned by retrieval before reranking/post-filtering." },
      { key: "score_threshold", label: "score_threshold", kind: "number", defaultValue: 0.2, help: "Minimum relevance score needed to keep results." },
      { key: "embedding_model", label: "embedding_model", kind: "text", defaultValue: "", help: "Embedding model identifier for vector-based retrieval setups." },
    ],
    inputAliases: { data: "query", request: "query" },
    outputAliases: { output: "out", retrieval: "documents", data: "grounding_context" },
  },
  memory: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "read_query", type: "data" },
      { name: "write_payload", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "memory_state", type: "memory" },
      { name: "context", type: "data" },
    ],
    defaults: { action: "append", scope: "session", session_id: "" },
    widgets: [
      { key: "action", label: "action", kind: "combo", defaultValue: "append", options: ["append", "read", "clear"], help: "append writes new memory, read fetches memory, clear deletes memory for target scope." },
      { key: "scope", label: "scope", kind: "combo", defaultValue: "session", options: ["run", "session", "user", "tenant", "agent", "workflow", "global"], help: "Partition used to resolve memory bucket identity and isolation." },
      { key: "session_id", label: "session_id", kind: "text", defaultValue: "", help: "Explicit session key for session-scoped memory. Supports variable expressions." },
      { key: "user_id", label: "user_id", kind: "text", defaultValue: "", help: "User identifier for user-scoped memory (e.g., var.currentUser)." },
      { key: "tenant_id", label: "tenant_id", kind: "text", defaultValue: "", help: "Tenant identifier for tenant-scoped memory (e.g., var.currentTenant)." },
      { key: "agent_id", label: "agent_id", kind: "text", defaultValue: "", help: "Agent identifier for agent-scoped memory to help agent-specific learning/context retention." },
      { key: "workflow_id", label: "workflow_id", kind: "text", defaultValue: "", help: "Workflow identifier for workflow-scoped memory contexts." },
      { key: "dimension_key", label: "dimension_key", kind: "text", defaultValue: "", help: "Optional custom bucket identity override for advanced segmentation." },
    ],
    inputAliases: { payload: "write_payload", data: "read_query", query: "read_query" },
    outputAliases: { output: "out", memory: "memory_state", data: "context" },
  },
  guardrail: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "candidate_output", type: "data" },
      { name: "context", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "approved_output", type: "data" },
      { name: "violations", type: "data" },
      { name: "decision", type: "guardrail" },
    ],
    defaults: {
      stage: "output",
      ruleset_id: "",
      tripwire_action: "reject_content",
      run_in_parallel: false,
      blocked_keywords: [],
      detect_secrets: true,
      reject_message: "Blocked by policy",
    },
    widgets: [
      { key: "stage", label: "stage", kind: "combo", defaultValue: "output", options: ["input", "output", "tool_input", "tool_output"], help: "When guardrail runs in execution lifecycle." },
      { key: "ruleset_id", label: "ruleset_id", kind: "combo", defaultValue: "", options: [], help: "Published guardrail ruleset selection from Guardrails builder." },
      { key: "tripwire_action", label: "tripwire_action", kind: "combo", defaultValue: "reject_content", options: ["allow", "reject_content", "raise_exception"], help: "Action to take when violations are detected." },
      { key: "run_in_parallel", label: "run_in_parallel", kind: "toggle", defaultValue: false, help: "Run asynchronously for input/tool-input styles where applicable." },
      { key: "detect_secrets", label: "detect_secrets", kind: "toggle", defaultValue: true, help: "Enable pattern checks for likely secrets in payload content." },
      { key: "reject_message", label: "reject_message", kind: "text", defaultValue: "Blocked by policy", help: "Replacement message when tripwire_action is reject_content." },
    ],
    inputAliases: { candidate: "candidate_output", data: "candidate_output" },
    outputAliases: { output: "out", approved: "approved_output", guardrail: "decision", flagged: "violations" },
  },
  "human-review": {
    inputs: [
      { name: "in", type: "flow" },
      { name: "candidate", type: "data" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "approved", type: "data" },
      { name: "feedback", type: "data" },
    ],
    defaults: { reviewer_group: "", required_approvals: 1, sla_minutes: 120 },
    widgets: [
      { key: "reviewer_group", label: "reviewer_group", kind: "combo", defaultValue: "security", options: ["security", "legal", "ops", "compliance"], help: "Team/group required to review this branch output." },
      { key: "required_approvals", label: "required_approvals", kind: "number", defaultValue: 1, help: "Number of approvals required before continuing." },
      { key: "sla_minutes", label: "sla_minutes", kind: "number", defaultValue: 120, help: "SLA window for review completion in minutes." },
    ],
    outputAliases: { output: "out" },
  },
  manifold: {
    inputs: [
      { name: "in_a", type: "flow" },
      { name: "in_b", type: "flow" },
      { name: "in_c", type: "flow" },
      { name: "in_d", type: "flow" },
    ],
    outputs: [
      { name: "out", type: "flow" },
      { name: "data", type: "data" },
    ],
    defaults: { logic_mode: "OR", min_required: 1 },
    widgets: [
      { key: "logic_mode", label: "logic_mode", kind: "combo", defaultValue: "OR", options: ["AND", "OR"], help: "How many incoming branches must pass before output propagates." },
      { key: "min_required", label: "min_required", kind: "number", defaultValue: 1, help: "Minimum number of active inbound sources required." },
    ],
    outputAliases: { output: "out" },
  },
  output: {
    inputs: [
      { name: "in", type: "flow" },
      { name: "result", type: "data" },
    ],
    outputs: [{ name: "out", type: "flow" }],
    defaults: { destination: "artifact_store", format: "json" },
    widgets: [
      { key: "destination", label: "destination", kind: "combo", defaultValue: "artifact_store", options: ["artifact_store", "webhook", "email", "queue"], help: "Final publication target for run output." },
      { key: "format", label: "format", kind: "combo", defaultValue: "json", options: ["json", "markdown", "text"], help: "Output serialization format." },
    ],
    inputAliases: { "in-flow": "in", data: "result", approved: "result", approved_output: "result", payload: "result" },
  },
};

function schemaFor(type: string): NodeSchema {
  const base = normalizeBaseNodeType(type);
  return SCHEMAS[base] ?? {
    inputs: [{ name: "in", type: "flow" }],
    outputs: [{ name: "out", type: "flow" }],
    defaults: {},
    widgets: [],
  };
}

export function getNodePorts(type: string): { inputs: PortSpec[]; outputs: PortSpec[] } {
  const schema = schemaFor(type);
  return {
    inputs: schema.inputs,
    outputs: schema.outputs,
  };
}

export function getNodeDefaultConfig(type: string): Record<string, unknown> {
  const base = normalizeBaseNodeType(type);
  const schema = schemaFor(type);
  const defaults = { ...schema.defaults };
  if (base === "agent" && type.startsWith("agent/")) {
    const specificAgentId = type.split("/")[1] || "";
    defaults.agent_id = specificAgentId;
  }
  return defaults;
}

export function getNodeWidgets(type: string): WidgetSpec[] {
  const base = normalizeBaseNodeType(type);
  const schema = schemaFor(type);
  if (base === "agent" && type.startsWith("agent/")) {
    const specificAgentId = type.split("/")[1] || "";
    return schema.widgets.map((widget) => {
      if (widget.key === "agent_id") {
        return {
          ...widget,
          kind: "combo",
          defaultValue: specificAgentId || "current",
          options: specificAgentId ? [specificAgentId, "current"] : ["current"],
        };
      }
      return widget;
    });
  }
  return schema.widgets;
}

export function normalizeNodeTypeForSchema(type: string): string {
  return normalizeBaseNodeType(type);
}

export function resolveNodePortAlias(
  type: string,
  direction: "input" | "output",
  handleName?: string | null,
): string | null {
  const schema = schemaFor(type);
  const fallback = direction === "input" ? schema.inputs[0]?.name : schema.outputs[0]?.name;
  const original = (handleName || "").trim() || fallback || null;
  if (!original) {
    return null;
  }

  const aliases = direction === "input" ? schema.inputAliases : schema.outputAliases;
  if (aliases && aliases[original]) {
    return aliases[original];
  }

  const candidates = direction === "input" ? schema.inputs : schema.outputs;
  if (candidates.some((port) => port.name === original)) {
    return original;
  }

  if (aliases && aliases[original.toLowerCase()]) {
    return aliases[original.toLowerCase()];
  }

  return fallback || original;
}
