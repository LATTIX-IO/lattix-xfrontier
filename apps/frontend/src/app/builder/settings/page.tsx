"use client";

import { useEffect, useMemo, useState } from "react";
import { getPlatformSecurityPolicy, getPlatformSettings, savePlatformSettings } from "@/lib/api";
import { useToast } from "@/components/toast";
import type { PlatformSettings, PlatformSignalEnforcement, SecurityPolicyResponse } from "@/types/frontier";

const runtimeEngineOptions = ["native", "langgraph", "langchain", "semantic-kernel", "autogen"] as const;
const signalEnforcementOptions: Array<{ value: PlatformSignalEnforcement; label: string }> = [
  { value: "off", label: "Off" },
  { value: "audit", label: "Audit only" },
  { value: "block_high", label: "Block high-risk" },
  { value: "raise_high", label: "Escalate high-risk" },
];

function toListString(values?: string[]): string {
  return (values ?? []).join(", ");
}

function parseList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function numberOrFallback(value: string, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function ToggleField({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="flex items-start justify-between gap-3 rounded border border-[var(--fx-border)] px-3 py-3 text-sm">
      <div className="min-w-0 space-y-1">
        <div className="font-medium text-[var(--foreground)]">{label}</div>
        <p className="fx-muted text-xs leading-5">{description}</p>
      </div>
      <input type="checkbox" className="mt-1 h-4 w-4 shrink-0" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

function ListField({
  label,
  description,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  description: string;
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
}) {
  return (
    <label className="block text-xs">
      <span className="font-medium text-[var(--foreground)]">{label}</span>
      <span className="mt-1 block fx-muted leading-5">{description}</span>
      <textarea
        className="fx-field mt-2 min-h-24 w-full px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

export default function BuilderSettingsPage() {
  const { addToast } = useToast();
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [policy, setPolicy] = useState<SecurityPolicyResponse | null>(null);
  const [guardrailRulesetId, setGuardrailRulesetId] = useState("");
  const [blockedKeywords, setBlockedKeywords] = useState("");
  const [allowedEgressHosts, setAllowedEgressHosts] = useState("");
  const [allowedRetrievalSources, setAllowedRetrievalSources] = useState("");
  const [allowedMcpServers, setAllowedMcpServers] = useState("");
  const [allowedRuntimeEngines, setAllowedRuntimeEngines] = useState("");
  const [highRiskToolPatterns, setHighRiskToolPatterns] = useState("");
  const [maxToolCalls, setMaxToolCalls] = useState("8");
  const [maxRetrievalItems, setMaxRetrievalItems] = useState("8");
  const [maxCollaborationAgents, setMaxCollaborationAgents] = useState("8");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [settingsResponse, policyResponse] = await Promise.all([getPlatformSettings(), getPlatformSecurityPolicy()]);
        if (cancelled) {
          return;
        }
        setSettings(settingsResponse);
        setPolicy(policyResponse);
        setGuardrailRulesetId(settingsResponse.default_guardrail_ruleset_id ?? "");
        setBlockedKeywords(toListString(settingsResponse.global_blocked_keywords));
        setAllowedEgressHosts(toListString(settingsResponse.allowed_egress_hosts));
        setAllowedRetrievalSources(toListString(settingsResponse.allowed_retrieval_sources));
        setAllowedMcpServers(toListString(settingsResponse.allowed_mcp_server_urls));
        setAllowedRuntimeEngines(toListString(settingsResponse.allowed_runtime_engines));
        setHighRiskToolPatterns(toListString(settingsResponse.high_risk_tool_patterns));
        setMaxToolCalls(String(settingsResponse.max_tool_calls_per_run ?? 8));
        setMaxRetrievalItems(String(settingsResponse.max_retrieval_items ?? 8));
        setMaxCollaborationAgents(String(settingsResponse.collaboration_max_agents ?? 8));
        setLoaded(true);
      } catch {
        if (!cancelled) {
          addToast("error", "Could not load builder security settings.");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [addToast]);

  const effectiveSummary = useMemo(() => {
    if (!policy) {
      return [] as string[];
    }
    return [
      `Classification: ${policy.effective.classification}`,
      `Tool calls capped at ${policy.effective.max_tool_calls_per_run} per run`,
      `Retrieval capped at ${policy.effective.max_retrieval_items} items`,
      `Runtime engines: ${policy.effective.allowed_runtime_engines.join(", ") || "none"}`,
      `Platform signals: ${policy.effective.enable_platform_signals ? policy.effective.platform_signal_enforcement : "off"}`,
    ];
  }, [policy]);

  async function handleSave() {
    if (!settings) {
      return;
    }

    setSaving(true);
    try {
      const payload = {
        default_guardrail_ruleset_id: guardrailRulesetId.trim() || null,
        global_blocked_keywords: parseList(blockedKeywords),
        allowed_egress_hosts: parseList(allowedEgressHosts),
        allowed_retrieval_sources: parseList(allowedRetrievalSources),
        allowed_mcp_server_urls: parseList(allowedMcpServers),
        allowed_runtime_engines: parseList(allowedRuntimeEngines),
        high_risk_tool_patterns: parseList(highRiskToolPatterns),
        max_tool_calls_per_run: numberOrFallback(maxToolCalls, settings.max_tool_calls_per_run ?? 8),
        max_retrieval_items: numberOrFallback(maxRetrievalItems, settings.max_retrieval_items ?? 8),
        collaboration_max_agents: numberOrFallback(maxCollaborationAgents, settings.collaboration_max_agents ?? 8),
        require_human_approval: Boolean(settings.require_human_approval),
        require_human_approval_for_high_risk_tools: Boolean(settings.require_human_approval_for_high_risk_tools ?? true),
        enforce_egress_allowlist: Boolean(settings.enforce_egress_allowlist),
        enforce_local_network_only: Boolean(settings.enforce_local_network_only),
        allow_local_network_hostnames: Boolean(settings.allow_local_network_hostnames),
        retrieval_require_local_source_url: Boolean(settings.retrieval_require_local_source_url),
        mcp_require_local_server: Boolean(settings.mcp_require_local_server),
        default_runtime_engine: settings.default_runtime_engine ?? "native",
        allow_runtime_engine_override: Boolean(settings.allow_runtime_engine_override),
        require_authenticated_requests: Boolean(settings.require_authenticated_requests),
        require_a2a_runtime_headers: Boolean(settings.require_a2a_runtime_headers),
        a2a_require_signed_messages: Boolean(settings.a2a_require_signed_messages ?? true),
        a2a_replay_protection: Boolean(settings.a2a_replay_protection ?? true),
        enable_foss_guardrail_signals: Boolean(settings.enable_foss_guardrail_signals ?? true),
        foss_guardrail_signal_enforcement: settings.foss_guardrail_signal_enforcement ?? "block_high",
      };

      await savePlatformSettings(payload);
      const [settingsResponse, policyResponse] = await Promise.all([getPlatformSettings(), getPlatformSecurityPolicy()]);
      setSettings(settingsResponse);
      setPolicy(policyResponse);
      addToast("success", "Builder security settings saved.");
    } catch {
      addToast("error", "Could not save builder security settings. Check guardrail references and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--ui-border)] pb-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide fx-muted">Builder / Security</p>
          <h1 className="text-xl font-semibold">Security Configuration</h1>
          <p className="fx-muted max-w-3xl text-sm leading-6">
            Configure the bounded inputs builders are allowed to tune. The enforcement rails stay server-side — because letting the UI reorder policy gates would be a very exciting outage.
          </p>
        </div>
        <button className="fx-btn-primary px-3 py-2 text-sm" disabled={!loaded || saving || !settings} onClick={handleSave}>
          {saving ? "Saving..." : "Save security defaults"}
        </button>
      </div>

      <article className="fx-panel p-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Immutable backend baseline</h2>
            <p className="fx-muted text-xs leading-5">These controls are enforced below the UI and cannot be disabled from builder settings.</p>
          </div>
          <div className="rounded border border-[var(--fx-border)] px-2 py-1 text-xs text-[var(--foreground)]">
            Default classification: <span className="font-semibold">{policy?.platform_defaults.classification ?? "internal"}</span>
          </div>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {Object.entries(policy?.immutable_baseline ?? {}).map(([key, value]) => (
            <div key={key} className="rounded border border-[var(--fx-border)] bg-[hsl(var(--card))] px-3 py-2 text-xs">
              <p className="font-medium text-[var(--foreground)] break-words">{key.replace(/_/g, " ")}</p>
              <p className="mt-1 fx-muted">{value ? "Enforced" : "Not exposed"}</p>
            </div>
          ))}
        </div>
      </article>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Guardrails and approvals</h2>
            <p className="fx-muted text-xs leading-5">Set the default safety envelope that workflows and agents may only tighten.</p>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Published guardrail ruleset</span>
                <span className="mt-1 block fx-muted">Optional published ruleset ID applied as the default baseline.</span>
                <input className="fx-field mt-2 w-full px-3 py-2 text-sm" value={guardrailRulesetId} onChange={(e) => setGuardrailRulesetId(e.target.value)} />
              </label>
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Platform signal enforcement</span>
                <span className="mt-1 block fx-muted">Controls how FOSS guardrail signals affect execution.</span>
                <select
                  className="fx-field mt-2 w-full px-3 py-2 text-sm"
                  value={settings?.foss_guardrail_signal_enforcement ?? "block_high"}
                  onChange={(e) => setSettings((current) => (current ? { ...current, foss_guardrail_signal_enforcement: e.target.value as PlatformSignalEnforcement } : current))}
                >
                  {signalEnforcementOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-3 grid gap-2 lg:grid-cols-2">
              <ToggleField
                label="Require approval for every run"
                description="Escalates every run into a human review lane before completion or export."
                checked={Boolean(settings?.require_human_approval)}
                onChange={(next) => setSettings((current) => (current ? { ...current, require_human_approval: next } : current))}
              />
              <ToggleField
                label="Require approval for high-risk tools"
                description="Keeps sensitive tools behind a reviewer, even when the rest of the run can proceed automatically."
                checked={Boolean(settings?.require_human_approval_for_high_risk_tools ?? true)}
                onChange={(next) => setSettings((current) => (current ? { ...current, require_human_approval_for_high_risk_tools: next } : current))}
              />
              <ToggleField
                label="Enable platform signals"
                description="Runs prompt injection, exfiltration, and related signal checks as part of the baseline guardrail path."
                checked={Boolean(settings?.enable_foss_guardrail_signals ?? true)}
                onChange={(next) => setSettings((current) => (current ? { ...current, enable_foss_guardrail_signals: next } : current))}
              />
              <ToggleField
                label="Require authenticated requests"
                description="Blocks anonymous writes to admin and orchestration routes unless a caller identity is supplied."
                checked={Boolean(settings?.require_authenticated_requests)}
                onChange={(next) => setSettings((current) => (current ? { ...current, require_authenticated_requests: next } : current))}
              />
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              <ListField
                label="Blocked keywords"
                description="Global prompt keywords blocked before workflow execution begins. Comma-separated."
                value={blockedKeywords}
                onChange={setBlockedKeywords}
                placeholder="credential dump, exfiltrate, ssn"
              />
              <ListField
                label="High-risk tool patterns"
                description="Tool names or patterns that should stay on the sharp end of approval gates. Comma-separated."
                value={highRiskToolPatterns}
                onChange={setHighRiskToolPatterns}
                placeholder="shell.exec, file.delete, terraform.apply"
              />
            </div>
          </article>

          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Network and retrieval boundaries</h2>
            <p className="fx-muted text-xs leading-5">Shape the maximum egress and data-source surface area available to workflows and agents.</p>
            <div className="mt-3 grid gap-2 lg:grid-cols-2">
              <ToggleField
                label="Enforce egress allowlist"
                description="Only destinations in the allowlist may be contacted when network egress is enabled."
                checked={Boolean(settings?.enforce_egress_allowlist)}
                onChange={(next) => setSettings((current) => (current ? { ...current, enforce_egress_allowlist: next } : current))}
              />
              <ToggleField
                label="Local-network only mode"
                description="Restricts runtime calls to local or approved private-network destinations."
                checked={Boolean(settings?.enforce_local_network_only)}
                onChange={(next) => setSettings((current) => (current ? { ...current, enforce_local_network_only: next } : current))}
              />
              <ToggleField
                label="Allow local hostnames"
                description="Permits localhost-style hostnames when local-network mode is active."
                checked={Boolean(settings?.allow_local_network_hostnames)}
                onChange={(next) => setSettings((current) => (current ? { ...current, allow_local_network_hostnames: next } : current))}
              />
              <ToggleField
                label="Require local retrieval sources"
                description="Prevents retrieval connectors from pulling from remote sources outside approved local URLs."
                checked={Boolean(settings?.retrieval_require_local_source_url)}
                onChange={(next) => setSettings((current) => (current ? { ...current, retrieval_require_local_source_url: next } : current))}
              />
              <ToggleField
                label="Require local MCP servers"
                description="Restricts MCP connections to local or explicitly approved servers."
                checked={Boolean(settings?.mcp_require_local_server)}
                onChange={(next) => setSettings((current) => (current ? { ...current, mcp_require_local_server: next } : current))}
              />
              <ToggleField
                label="Require A2A runtime headers"
                description="Requires agent-to-agent requests to include runtime identity headers for enforcement and tracing."
                checked={Boolean(settings?.require_a2a_runtime_headers)}
                onChange={(next) => setSettings((current) => (current ? { ...current, require_a2a_runtime_headers: next } : current))}
              />
              <ToggleField
                label="Require signed A2A messages"
                description="Maintains signed message validation on agent-to-agent payloads."
                checked={Boolean(settings?.a2a_require_signed_messages ?? true)}
                onChange={(next) => setSettings((current) => (current ? { ...current, a2a_require_signed_messages: next } : current))}
              />
              <ToggleField
                label="Enable A2A replay protection"
                description="Protects collaborative calls against message replay."
                checked={Boolean(settings?.a2a_replay_protection ?? true)}
                onChange={(next) => setSettings((current) => (current ? { ...current, a2a_replay_protection: next } : current))}
              />
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <ListField
                label="Allowed egress hosts"
                description="Explicit destinations builders may reach when allowlist enforcement is on."
                value={allowedEgressHosts}
                onChange={setAllowedEgressHosts}
                placeholder="api.openai.com, localhost, graph.microsoft.com"
              />
              <ListField
                label="Allowed retrieval sources"
                description="Knowledge sources that retrieval nodes can query by default."
                value={allowedRetrievalSources}
                onChange={setAllowedRetrievalSources}
                placeholder="kb://default, file://docs, sqlite:///memory.db"
              />
              <ListField
                label="Allowed MCP servers"
                description="Server URLs available to MCP-enabled agents and workflows."
                value={allowedMcpServers}
                onChange={setAllowedMcpServers}
                placeholder="http://localhost:8787, https://mcp.notion.com/mcp"
              />
            </div>
          </article>

          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Runtime and collaboration ceilings</h2>
            <p className="fx-muted text-xs leading-5">Cap how far builders can stretch engines, tools, retrieval, and collaboration at lower scopes.</p>
            <div className="mt-3 grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Max tool calls per run</span>
                <input className="fx-field mt-2 w-full px-3 py-2 text-sm" value={maxToolCalls} onChange={(e) => setMaxToolCalls(e.target.value)} />
              </label>
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Max retrieval items</span>
                <input className="fx-field mt-2 w-full px-3 py-2 text-sm" value={maxRetrievalItems} onChange={(e) => setMaxRetrievalItems(e.target.value)} />
              </label>
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Max collaborators</span>
                <input className="fx-field mt-2 w-full px-3 py-2 text-sm" value={maxCollaborationAgents} onChange={(e) => setMaxCollaborationAgents(e.target.value)} />
              </label>
              <label className="block text-xs">
                <span className="font-medium text-[var(--foreground)]">Default runtime engine</span>
                <select
                  className="fx-field mt-2 w-full px-3 py-2 text-sm"
                  value={settings?.default_runtime_engine ?? "native"}
                  onChange={(e) => setSettings((current) => (current ? { ...current, default_runtime_engine: e.target.value as PlatformSettings["default_runtime_engine"] } : current))}
                >
                  {runtimeEngineOptions.map((engine) => (
                    <option key={engine} value={engine}>{engine}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-3 grid gap-2 lg:grid-cols-2">
              <ToggleField
                label="Allow runtime override"
                description="Lets workflow and agent scopes narrow engine choices, but only inside the platform allowlist."
                checked={Boolean(settings?.allow_runtime_engine_override)}
                onChange={(next) => setSettings((current) => (current ? { ...current, allow_runtime_engine_override: next } : current))}
              />
              <div className="rounded border border-[var(--fx-border)] px-3 py-3 text-sm">
                <p className="font-medium text-[var(--foreground)]">Builder-visible default memory scopes</p>
                <p className="mt-1 fx-muted text-xs leading-5">{policy?.platform_defaults.allowed_memory_scopes.join(", ") ?? "run, session, user, tenant, agent, workflow, global"}</p>
              </div>
            </div>

            <div className="mt-3">
              <ListField
                label="Allowed runtime engines"
                description="Comma-separated engine allowlist available to workflows and agents beneath the platform scope."
                value={allowedRuntimeEngines}
                onChange={setAllowedRuntimeEngines}
                placeholder="native, langgraph, langchain"
              />
            </div>
          </article>
        </div>

        <aside className="space-y-4">
          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Effective platform summary</h2>
            <p className="fx-muted text-xs leading-5">What lower scopes inherit before they add tighter overrides.</p>
            <ul className="mt-3 space-y-2 text-sm text-[var(--foreground)]">
              {effectiveSummary.map((item) => (
                <li key={item} className="rounded border border-[var(--fx-border)] px-3 py-2 break-words">{item}</li>
              ))}
            </ul>
          </article>

          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Server-owned controls</h2>
            <p className="fx-muted text-xs leading-5">The UI can tune inputs, but these safety rails remain backend-owned.</p>
            <ul className="mt-3 space-y-2 text-xs">
              {(policy?.backend_enforced_controls ?? []).map((item) => (
                <li key={item} className="rounded border border-[var(--fx-border)] px-3 py-2 text-[var(--foreground)] break-words">
                  {item.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          </article>

          <article className="fx-panel p-3">
            <h2 className="text-sm font-semibold">Builder contract</h2>
            <p className="fx-muted text-xs leading-5">Workflows and agents may only tighten these settings; they cannot widen the platform envelope.</p>
            <ul className="mt-3 list-disc space-y-2 pl-4 text-xs text-[var(--foreground)]">
              {(policy?.configurable_controls ?? []).map((item) => (
                <li key={item} className="break-words">{item.replace(/_/g, " ")}</li>
              ))}
            </ul>
          </article>
        </aside>
      </div>
    </section>
  );
}
