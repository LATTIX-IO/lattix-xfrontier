export type AppMode = "user" | "builder";

export type OperatorSession = {
  authenticated: boolean;
  actor: string;
  principal_id: string;
  principal_type: "user" | "agent" | "service" | "npe" | string;
  display_name: string;
  subject: string;
  email?: string;
  preferred_username?: string;
  auth_mode: string;
  provider?: string;
  roles: string[];
  capabilities: {
    can_admin: boolean;
    can_builder: boolean;
  };
  allowed_modes: AppMode[];
  default_mode: AppMode;
  oidc: {
    configured: boolean;
    issuer: string;
    audience: string;
    provider: string;
    validation_error?: string;
  };
};

export type PlatformVersionStatus = {
  current_version: string;
  latest_version: string;
  update_available: boolean;
  install_mode: "editable" | "wheel" | string;
  update_command: string;
  release_notes_url?: string;
  checked_at: string;
  source?: string;
  summary: string;
};

export type RunStatus =
  | "Running"
  | "Blocked"
  | "Needs Review"
  | "Done"
  | "Failed";

export type WorkflowRunSummary = {
  id: string;
  title: string;
  status: RunStatus;
  updatedAt: string;
  progressLabel: string;
};

export type WorkflowRunEvent = {
  id: string;
  type:
    | "user_message"
    | "agent_message"
    | "step_started"
    | "step_completed"
    | "guardrail_result"
    | "artifact_created"
    | "approval_required"
    | "approval_decision"
    | "error";
  title: string;
  summary: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
};

export type ArtifactSummary = {
  id: string;
  name: string;
  status: "Draft" | "Needs Review" | "Approved" | "Blocked";
  version: number;
};

export type ArtifactDetail = ArtifactSummary & {
  run_id?: string | null;
  run_title?: string | null;
  createdAt: string;
  content: string;
};

export type GeneratedCodeArtifact = ArtifactSummary & {
  framework: "microsoft-agent-framework" | "langgraph";
  language: "python";
  path: string;
  summary: string;
  content: string;
  generated_at: string;
  entity_type: "agent" | "workflow";
  entity_id: string;
};

export type InboxItem = {
  id: string;
  runId: string;
  runName: string;
  artifactType: string;
  reason: string;
  queue: "Needs Review" | "Needs Approval" | "Clarifications Requested" | "Blocked by Guardrails";
};

export type WorkflowDefinition = {
  id: string;
  name: string;
  description: string;
  version: number;
  status: "draft" | "published" | "archived";
  security_config?: SecurityScopeConfig;
};

export type SecurityClassification = "public" | "internal" | "confidential" | "restricted";

export type PlatformSignalEnforcement = "off" | "audit" | "block_high" | "raise_high";

export type SecurityScopeConfig = {
  classification?: SecurityClassification;
  guardrail_ruleset_id?: string | null;
  blocked_keywords?: string[];
  allowed_egress_hosts?: string[];
  allowed_retrieval_sources?: string[];
  allowed_mcp_server_urls?: string[];
  allowed_runtime_engines?: string[];
  allowed_memory_scopes?: string[];
  max_tool_calls_per_run?: number;
  max_retrieval_items?: number;
  max_collaboration_agents?: number;
  require_human_approval?: boolean;
  require_human_approval_for_high_risk_tools?: boolean;
  allow_runtime_override?: boolean;
  enable_platform_signals?: boolean;
  platform_signal_enforcement?: PlatformSignalEnforcement;
};

export type SecurityImmutableBaseline = {
  enforce_capability_filter: boolean;
  enforce_policy_gate: boolean;
  fail_closed_policy_decisions: boolean;
  enforce_signed_a2a_messages: boolean;
  enforce_a2a_replay_protection: boolean;
  require_readonly_rootfs_for_sandbox: boolean;
  require_non_root_sandbox_user: boolean;
  require_egress_mediation_when_network_enabled: boolean;
  allow_filter_chain_reordering: boolean;
  allow_custom_policy_code: boolean;
};

export type SecurityPolicyResponse = {
  immutable_baseline: SecurityImmutableBaseline;
  platform_defaults: Required<SecurityScopeConfig> & { classification: SecurityClassification; guardrail_ruleset_id: string | null };
  workflow_overrides: SecurityScopeConfig;
  agent_overrides: SecurityScopeConfig;
  effective: Required<SecurityScopeConfig> & { classification: SecurityClassification; guardrail_ruleset_id: string | null };
  backend_enforced_controls?: string[];
  configurable_controls?: string[];
};

export type AgentDefinition = {
  id: string;
  name: string;
  version: number;
  status: "draft" | "published" | "archived";
  type: "form" | "graph";
  config_json?: {
    schema_version?: string;
    source_agent_id?: string;
    meta?: Record<string, unknown>;
    runtime?: {
      model_defaults?: Record<string, unknown>;
      engine_policy?: Record<string, unknown>;
      framework_mappings?: Record<string, Record<string, string>>;
      framework_profiles?: Record<string, Record<string, unknown>>;
      [key: string]: unknown;
    };
    reasoning?: Record<string, unknown>;
    knowledge?: Record<string, unknown>;
    integrations?: Record<string, unknown>;
    mcp?: Record<string, unknown>;
    a2a?: Record<string, unknown>;
    tools?: Record<string, unknown>;
    memory?: Record<string, unknown>;
    guardrails?: Record<string, unknown>;
    iam?: {
      principal_id?: string;
      principal_type?: "user" | "agent" | "service" | "npe";
      provider?: string;
      auth_mode?: string;
      display_name?: string;
      subject?: string;
      agent_id?: string;
      service_account_id?: string;
      client_id?: string;
      roles?: string[];
      groups?: string[];
      provisioning?: Record<string, unknown>;
      recommended_claims?: Record<string, unknown>;
      [key: string]: unknown;
    };
    security?: SecurityScopeConfig;
    graph_json?: {
      nodes?: Array<{ id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> }>;
      links?: Array<{ from: string; to: string; from_port?: string; to_port?: string }>;
    };
    [key: string]: unknown;
  };
};

export type GuardrailRuleSet = {
  id: string;
  name: string;
  version: number;
  status: "draft" | "published" | "archived";
  config_json?: Record<string, unknown>;
};

export type PlatformSettings = {
  org_name?: string;
  org_slug?: string;
  support_email?: string;
  website?: string;
  default_kickoff_workflow?: string;
  preferred_review_depth?: string;
  idle_timeout?: string;
  local_only_mode: boolean;
  mask_secrets_in_events: boolean;
  require_human_approval: boolean;
  require_human_approval_for_high_risk_tools?: boolean;
  emergency_read_only_mode?: boolean;
  block_new_runs?: boolean;
  block_graph_runs?: boolean;
  block_tool_calls?: boolean;
  block_retrieval_calls?: boolean;
  require_authenticated_requests?: boolean;
  require_a2a_runtime_headers?: boolean;
  a2a_require_signed_messages?: boolean;
  a2a_replay_protection?: boolean;
  default_guardrail_ruleset_id: string | null;
  global_blocked_keywords: string[];
  collaboration_max_agents: number;
  max_tool_calls_per_run?: number;
  max_retrieval_items?: number;
  default_runtime_engine?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
  default_runtime_strategy?: "single" | "hybrid";
  default_hybrid_runtime_routing?: {
    default?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
    orchestration?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
    retrieval?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
    tooling?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
    collaboration?: "native" | "langgraph" | "langchain" | "semantic-kernel" | "autogen";
  };
  allowed_runtime_engines?: string[];
  allow_runtime_engine_override?: boolean;
  enforce_runtime_engine_allowlist?: boolean;
  enforce_egress_allowlist?: boolean;
  allowed_egress_hosts?: string[];
  enforce_local_network_only?: boolean;
  allow_local_network_hostnames?: boolean;
  allowed_retrieval_sources?: string[];
  retrieval_require_local_source_url?: boolean;
  allowed_mcp_server_urls?: string[];
  mcp_require_local_server?: boolean;
  high_risk_tool_patterns?: string[];
  enable_foss_guardrail_signals?: boolean;
  foss_guardrail_signal_enforcement?: PlatformSignalEnforcement;
  enforce_integration_policies?: boolean;
  require_signed_integrations?: boolean;
  require_sandbox_for_third_party?: boolean;
  allow_local_unsigned_integrations?: boolean;
};

export type IntegrationDefinition = {
  id: string;
  name: string;
  type: "http" | "database" | "queue" | "vector" | "custom";
  status: "draft" | "configured" | "error" | "archived";
  base_url: string;
  auth_type: "none" | "api_key" | "bearer" | "oauth2" | "basic";
  secret_ref: string;
  secret_configured?: boolean;
  metadata_json?: Record<string, unknown>;
  capabilities?: string[];
  permission_scopes?: string[];
  data_access?: string[];
  egress_allowlist?: string[];
  publisher?: "first_party" | "third_party" | "custom";
  execution_mode?: "local" | "sandboxed";
  signature_verified?: boolean;
  approved_for_marketplace?: boolean;
};

export type AgentTemplate = {
  id: string;
  name: string;
  description: string;
  category: "ops" | "security" | "sales" | "finance" | "general";
  status: "active" | "deprecated";
  config_json?: Record<string, unknown>;
};

export type PlaybookDefinition = {
  id: string;
  name: string;
  description: string;
  category: "go_to_market" | "security" | "support" | "operations" | "other";
  status: "active" | "deprecated";
  metadata_json?: Record<string, unknown>;
  graph_json?: {
    nodes?: Array<{ id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> }>;
    links?: Array<{ from: string; to: string; from_port?: string; to_port?: string }>;
  };
};

export type TemplateCatalogItem = {
  id: string;
  source_id: string;
  template_type: "agent" | "workflow" | "playbook";
  name: string;
  description: string;
  category: string;
  status: "active" | "deprecated";
  version?: number | null;
};

export type ObservabilityRunTrace = {
  run_id: string;
  status: string;
  event_count: number;
  node_count: number;
  edge_count: number;
  duration_ms?: number;
  token_estimate?: number;
  cost_estimate_usd?: number;
  latency_by_stage_ms?: Record<string, number>;
};

export type AuditEvent = {
  id: string;
  action: string;
  actor: string;
  outcome: "allowed" | "blocked" | "error";
  created_at: string;
  metadata: Record<string, unknown>;
};

export type AtfAlignmentReport = {
  generated_at: string;
  framework: string;
  coverage_percent: number;
  maturity_estimate: "intern" | "junior" | "senior" | "principal";
  pillars: Record<
    "identity" | "behavior_monitoring" | "data_governance" | "segmentation" | "incident_response",
    {
      status: "partial" | "strong";
      controls: Record<string, unknown>;
      gaps: string[];
    }
  >;
  evidence: {
    audit_window_hours: number;
    audit_event_count_24h: number;
    audit_allowed_24h: number;
    audit_blocked_24h: number;
    audit_error_24h: number;
    total_audit_events: number;
    run_count_total: number;
  };
};

export type CollaborationParticipant = {
  user_id: string;
  principal_id?: string | null;
  principal_type?: "user" | "agent" | "service" | "npe";
  auth_subject?: string | null;
  display_name: string;
  role: "owner" | "editor" | "viewer";
  last_seen_at: string;
  metadata_json?: Record<string, unknown>;
};

export type CollaborationSession = {
  id: string;
  entity_type: "agent" | "workflow";
  entity_id: string;
  graph_json: {
    nodes?: Array<{ id: string; title: string; type: string; x: number; y: number; config?: Record<string, unknown> }>;
    links?: Array<{ from: string; to: string; from_port?: string; to_port?: string }>;
  };
  version: number;
  updated_at: string;
  participants: CollaborationParticipant[];
};
