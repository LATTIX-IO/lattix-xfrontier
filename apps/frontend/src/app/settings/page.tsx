"use client";

import { useEffect, useRef, useState } from "react";
import { getAtfAlignmentReport, getPlatformSettings, savePlatformSettings } from "@/lib/api";
import type { AtfAlignmentReport } from "@/types/frontier";

const sectionNav = [
  { id: "section-brand", label: "Brand & Identity" },
  { id: "section-security", label: "Security & Governance" },
  { id: "section-runtime", label: "Runtime Policy" },
  { id: "section-user-defaults", label: "User Defaults" },
] as const;

export default function SettingsPage() {
  const runtimeEngineOptions = ["native", "langgraph", "langchain", "semantic-kernel", "autogen"] as const;
  const recommendedHybridRouting = {
    default: "native",
    orchestration: "langgraph",
    retrieval: "langchain",
    tooling: "semantic-kernel",
    collaboration: "autogen",
  } as const;
  const [activeSection, setActiveSection] = useState<string>(sectionNav[0].id);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [atfReport, setAtfReport] = useState<AtfAlignmentReport | null>(null);
  const [atfLoading, setAtfLoading] = useState(true);
  const [orgName, setOrgName] = useState("Lattix xFrontier");
  const [orgSlug, setOrgSlug] = useState("lattix-frontier");
  const [supportEmail, setSupportEmail] = useState("support@lattix.io");
  const [website, setWebsite] = useState("https://lattix.io");
  const [defaultKickoffWorkflow, setDefaultKickoffWorkflow] = useState("Auto-select from intent");
  const [preferredReviewDepth, setPreferredReviewDepth] = useState("Standard");
  const [idleTimeout, setIdleTimeout] = useState("30 minutes");
  const [localOnlyMode, setLocalOnlyMode] = useState(true);
  const [maskSecrets, setMaskSecrets] = useState(true);
  const [requireHumanApproval, setRequireHumanApproval] = useState(false);
  const [emergencyReadOnlyMode, setEmergencyReadOnlyMode] = useState(false);
  const [blockNewRuns, setBlockNewRuns] = useState(false);
  const [blockGraphRuns, setBlockGraphRuns] = useState(false);
  const [blockToolCalls, setBlockToolCalls] = useState(false);
  const [blockRetrievalCalls, setBlockRetrievalCalls] = useState(false);
  const [requireAuthenticatedRequests, setRequireAuthenticatedRequests] = useState(false);
  const [requireA2aRuntimeHeaders, setRequireA2aRuntimeHeaders] = useState(false);
  const [defaultGuardrailRulesetId, setDefaultGuardrailRulesetId] = useState("");
  const [globalBlockedKeywords, setGlobalBlockedKeywords] = useState("");
  const [collaborationMaxAgents, setCollaborationMaxAgents] = useState("8");
  const [defaultRuntimeStrategy, setDefaultRuntimeStrategy] = useState<"single" | "hybrid">("single");
  const [defaultHybridRouting, setDefaultHybridRouting] = useState<{
    default: string;
    orchestration: string;
    retrieval: string;
    tooling: string;
    collaboration: string;
  }>({
    default: "native",
    orchestration: "native",
    retrieval: "native",
    tooling: "native",
    collaboration: "native",
  });

  useEffect(() => {
    let cancelled = false;
    async function loadSettings() {
      const [settings, report] = await Promise.all([getPlatformSettings(), getAtfAlignmentReport()]);
      if (cancelled) {
        return;
      }
      if (settings.org_name) setOrgName(settings.org_name);
      if (settings.org_slug) setOrgSlug(settings.org_slug);
      if (settings.support_email) setSupportEmail(settings.support_email);
      if (settings.website) setWebsite(settings.website);
      if (settings.default_kickoff_workflow) setDefaultKickoffWorkflow(settings.default_kickoff_workflow);
      if (settings.preferred_review_depth) setPreferredReviewDepth(settings.preferred_review_depth);
      if (settings.idle_timeout) setIdleTimeout(settings.idle_timeout);
      setLocalOnlyMode(settings.local_only_mode);
      setMaskSecrets(settings.mask_secrets_in_events);
      setRequireHumanApproval(settings.require_human_approval);
      setEmergencyReadOnlyMode(Boolean(settings.emergency_read_only_mode));
      setBlockNewRuns(Boolean(settings.block_new_runs));
      setBlockGraphRuns(Boolean(settings.block_graph_runs));
      setBlockToolCalls(Boolean(settings.block_tool_calls));
      setBlockRetrievalCalls(Boolean(settings.block_retrieval_calls));
      setRequireAuthenticatedRequests(Boolean(settings.require_authenticated_requests));
      setRequireA2aRuntimeHeaders(Boolean(settings.require_a2a_runtime_headers));
      setDefaultGuardrailRulesetId(settings.default_guardrail_ruleset_id ?? "");
      setGlobalBlockedKeywords(settings.global_blocked_keywords.join(", "));
      setCollaborationMaxAgents(String(settings.collaboration_max_agents));
      setDefaultRuntimeStrategy((settings.default_runtime_strategy ?? "single") as "single" | "hybrid");
      setDefaultHybridRouting({
        default: settings.default_hybrid_runtime_routing?.default ?? settings.default_runtime_engine ?? "native",
        orchestration: settings.default_hybrid_runtime_routing?.orchestration ?? settings.default_hybrid_runtime_routing?.default ?? settings.default_runtime_engine ?? "native",
        retrieval: settings.default_hybrid_runtime_routing?.retrieval ?? settings.default_hybrid_runtime_routing?.default ?? settings.default_runtime_engine ?? "native",
        tooling: settings.default_hybrid_runtime_routing?.tooling ?? settings.default_hybrid_runtime_routing?.default ?? settings.default_runtime_engine ?? "native",
        collaboration: settings.default_hybrid_runtime_routing?.collaboration ?? settings.default_hybrid_runtime_routing?.default ?? settings.default_runtime_engine ?? "native",
      });
      setAtfReport(report);
      setAtfLoading(false);
      setLoaded(true);
    }

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 },
    );
    for (const { id } of sectionNav) {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    }
    return () => observerRef.current?.disconnect();
  }, []);

  async function handleSavePlatformSettings() {
    setSaveState("saving");
    try {
      const maxAgents = Number(collaborationMaxAgents);
      await savePlatformSettings({
        org_name: orgName,
        org_slug: orgSlug,
        support_email: supportEmail,
        website: website,
        default_kickoff_workflow: defaultKickoffWorkflow,
        preferred_review_depth: preferredReviewDepth,
        idle_timeout: idleTimeout,
        local_only_mode: localOnlyMode,
        mask_secrets_in_events: maskSecrets,
        require_human_approval: requireHumanApproval,
        emergency_read_only_mode: emergencyReadOnlyMode,
        block_new_runs: blockNewRuns,
        block_graph_runs: blockGraphRuns,
        block_tool_calls: blockToolCalls,
        block_retrieval_calls: blockRetrievalCalls,
        require_authenticated_requests: requireAuthenticatedRequests,
        require_a2a_runtime_headers: requireA2aRuntimeHeaders,
        default_guardrail_ruleset_id: defaultGuardrailRulesetId.trim() || null,
        global_blocked_keywords: globalBlockedKeywords
          .split(",")
          .map((item) => item.trim())
          .filter((item) => item.length > 0),
        collaboration_max_agents: Number.isFinite(maxAgents) && maxAgents > 0 ? maxAgents : 8,
        default_runtime_strategy: defaultRuntimeStrategy,
        default_hybrid_runtime_routing: {
          default: defaultHybridRouting.default,
          orchestration: defaultHybridRouting.orchestration,
          retrieval: defaultHybridRouting.retrieval,
          tooling: defaultHybridRouting.tooling,
          collaboration: defaultHybridRouting.collaboration,
        },
      });
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 2500);
    } catch {
      setSaveState("error");
      setTimeout(() => setSaveState("idle"), 4000);
    }
  }

  function handleResetToRecommendedHybridProfile() {
    setDefaultRuntimeStrategy("hybrid");
    setDefaultHybridRouting({
      default: recommendedHybridRouting.default,
      orchestration: recommendedHybridRouting.orchestration,
      retrieval: recommendedHybridRouting.retrieval,
      tooling: recommendedHybridRouting.tooling,
      collaboration: recommendedHybridRouting.collaboration,
    });
  }

  const atfPillars = atfReport?.pillars ?? null;
  const topGaps = atfPillars
    ? Object.entries(atfPillars)
        .flatMap(([pillar, details]) => (details.gaps ?? []).map((gap) => `${pillar.replace(/_/g, " ")}: ${gap}`))
        .slice(0, 3)
    : [];

  const maturityLabel = atfReport?.maturity_estimate ? atfReport.maturity_estimate.toUpperCase() : "UNKNOWN";

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between border-b border-[var(--ui-border)] pb-2">
        <div>
          <p className="text-[11px] uppercase tracking-wide fx-muted">Console / Settings</p>
          <h1 className="text-xl font-semibold">Organization Settings</h1>
          <p className="fx-muted text-sm">Manage platform identity, runtime policy defaults, and operational safety baselines.</p>
        </div>
        <div className="flex items-center gap-2">
          {saveState === "error" ? <p className="text-xs text-red-300">Could not save platform settings.</p> : null}
          <button
            className="fx-btn-primary px-3 py-2 text-sm"
            onClick={handleSavePlatformSettings}
            disabled={!loaded || saveState === "saving"}
            aria-label="Save preferences"
          >
            {saveState === "saving" ? "Saving..." : saveState === "saved" ? "Saved" : "Save changes"}
          </button>
        </div>
      </div>

      <article className="fx-panel p-3" aria-live="polite">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold">ATF posture snapshot</h2>
            <p className="fx-muted text-xs">Live alignment estimate from trust controls and recent audit evidence.</p>
          </div>
          <div className="rounded border border-[var(--ui-border)] bg-[hsl(var(--card))] px-2 py-1 text-xs font-medium text-[var(--foreground)]">
            {atfLoading ? "Loading…" : `${atfReport?.coverage_percent ?? 0}% • ${maturityLabel}`}
          </div>
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-4">
          <div className="rounded border border-[var(--fx-border)] px-2 py-2 text-xs">
            <p className="fx-muted">Audit events (24h)</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{atfReport?.evidence.audit_event_count_24h ?? 0}</p>
          </div>
          <div className="rounded border border-[var(--fx-border)] px-2 py-2 text-xs">
            <p className="fx-muted">Allowed (24h)</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{atfReport?.evidence.audit_allowed_24h ?? 0}</p>
          </div>
          <div className="rounded border border-[var(--fx-border)] px-2 py-2 text-xs">
            <p className="fx-muted">Blocked (24h)</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{atfReport?.evidence.audit_blocked_24h ?? 0}</p>
          </div>
          <div className="rounded border border-[var(--fx-border)] px-2 py-2 text-xs">
            <p className="fx-muted">Errors (24h)</p>
            <p className="mt-1 text-base font-semibold text-[var(--foreground)]">{atfReport?.evidence.audit_error_24h ?? 0}</p>
          </div>
        </div>

        {topGaps.length > 0 ? (
          <div className="mt-3 rounded border border-[var(--fx-border)] bg-[hsl(var(--card))] px-2 py-2 text-xs">
            <p className="font-medium text-[var(--foreground)]">Top ATF gaps</p>
            <ul className="mt-1 list-disc space-y-1 pl-4 text-[var(--foreground)]">
              {topGaps.map((gap) => (
                <li key={gap}>{gap}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </article>

      <div className="grid gap-3 xl:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="fx-panel h-fit p-2">
          <div className="px-2 pb-2 text-[11px] uppercase tracking-wide fx-muted">Settings</div>
          <nav className="space-y-1 text-xs">
            {sectionNav.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                className={`block w-full rounded px-2 py-1.5 text-left transition ${
                  activeSection === item.id
                    ? "bg-[var(--fx-nav-hover)] font-semibold text-[hsl(var(--foreground))]"
                    : "text-[var(--fx-muted)] hover:bg-[var(--fx-nav-hover)] hover:text-[var(--foreground)]"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </aside>

        <div className="space-y-3">
          <article id="section-brand" className="fx-panel p-3 scroll-mt-32">
            <h2 className="text-sm font-semibold">Brand and identity</h2>
            <p className="fx-muted text-xs">Operational details visible across collaboration, approvals, and audit exports.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <label className="block text-xs">
                Organization name
                <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
              </label>
              <label className="block text-xs">
                Organization slug
                <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={orgSlug} onChange={(e) => setOrgSlug(e.target.value)} />
              </label>
              <label className="block text-xs">
                Support email
                <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={supportEmail} onChange={(e) => setSupportEmail(e.target.value)} />
              </label>
              <label className="block text-xs">
                Website
                <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={website} onChange={(e) => setWebsite(e.target.value)} />
              </label>
            </div>
          </article>

          <article id="section-security" className="fx-panel p-3 scroll-mt-32">
            <h2 className="text-sm font-semibold">Security and governance</h2>
            <p className="fx-muted text-xs">Default controls applied across workspace sessions and run execution.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Mask sensitive values in previews</span>
                <input type="checkbox" checked={maskSecrets} onChange={(event) => setMaskSecrets(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Local-only mode</span>
                <input type="checkbox" checked={localOnlyMode} onChange={(event) => setLocalOnlyMode(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs md:col-span-2">
                <span>Require human approval on all workflow runs</span>
                <input type="checkbox" checked={requireHumanApproval} onChange={(event) => setRequireHumanApproval(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs md:col-span-2">
                <span>Emergency read-only mode (block write actions)</span>
                <input type="checkbox" checked={emergencyReadOnlyMode} onChange={(event) => setEmergencyReadOnlyMode(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Block new workflow runs</span>
                <input type="checkbox" checked={blockNewRuns} onChange={(event) => setBlockNewRuns(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Block graph runs</span>
                <input type="checkbox" checked={blockGraphRuns} onChange={(event) => setBlockGraphRuns(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Block tool calls</span>
                <input type="checkbox" checked={blockToolCalls} onChange={(event) => setBlockToolCalls(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs">
                <span>Block retrieval calls</span>
                <input type="checkbox" checked={blockRetrievalCalls} onChange={(event) => setBlockRetrievalCalls(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs md:col-span-2">
                <span>Require authenticated write requests</span>
                <input type="checkbox" checked={requireAuthenticatedRequests} onChange={(event) => setRequireAuthenticatedRequests(event.target.checked)} />
              </label>
              <label className="flex items-center justify-between gap-3 border border-[var(--fx-border)] px-2 py-2 text-xs md:col-span-2">
                <span>Require A2A runtime headers (subject/signature/nonce)</span>
                <input type="checkbox" checked={requireA2aRuntimeHeaders} onChange={(event) => setRequireA2aRuntimeHeaders(event.target.checked)} />
              </label>
              <label className="block text-xs md:col-span-2">
                Default guardrail ruleset ID
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={defaultGuardrailRulesetId}
                  onChange={(event) => setDefaultGuardrailRulesetId(event.target.value)}
                  placeholder="12121212-1212-4121-8121-121212121212"
                />
              </label>
              <label className="block text-xs md:col-span-2">
                Globally blocked keywords
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={globalBlockedKeywords}
                  onChange={(event) => setGlobalBlockedKeywords(event.target.value)}
                  placeholder="private_key,secret,password"
                />
              </label>
            </div>
          </article>

          <article id="section-runtime" className="fx-panel p-3 scroll-mt-32">
            <h2 className="text-sm font-semibold">Runtime policy</h2>
            <p className="fx-muted text-xs">Default execution strategy and role-based framework routing profile.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <label className="block text-xs">
                Max collaborating agents per run
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={collaborationMaxAgents}
                  onChange={(event) => setCollaborationMaxAgents(event.target.value)}
                  inputMode="numeric"
                />
              </label>
              <label className="block text-xs">
                Default runtime strategy
                <select
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={defaultRuntimeStrategy}
                  onChange={(event) => setDefaultRuntimeStrategy(event.target.value as "single" | "hybrid")}
                >
                  <option value="single">single</option>
                  <option value="hybrid">hybrid</option>
                </select>
              </label>
            </div>

            <div className="mt-3 space-y-2 border border-[var(--fx-border)] p-2">
              <div className="flex items-center justify-between">
                <div className="text-xs uppercase tracking-wide fx-muted">Global hybrid role → engine profile</div>
                <button
                  type="button"
                  className="fx-btn-secondary px-2 py-1 text-xs"
                  onClick={handleResetToRecommendedHybridProfile}
                >
                  Reset to recommended profile
                </button>
              </div>

              <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                <label className="block text-xs">
                  default
                  <select
                    className="fx-field mt-1 w-full px-2 py-2 text-sm"
                    value={defaultHybridRouting.default}
                    onChange={(event) =>
                      setDefaultHybridRouting((current) => ({
                        ...current,
                        default: event.target.value,
                      }))
                    }
                  >
                    {runtimeEngineOptions.map((engine) => (
                      <option key={`settings-default-${engine}`} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-xs">
                  orchestration
                  <select
                    className="fx-field mt-1 w-full px-2 py-2 text-sm"
                    value={defaultHybridRouting.orchestration}
                    onChange={(event) =>
                      setDefaultHybridRouting((current) => ({
                        ...current,
                        orchestration: event.target.value,
                      }))
                    }
                  >
                    {runtimeEngineOptions.map((engine) => (
                      <option key={`settings-orchestration-${engine}`} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-xs">
                  retrieval
                  <select
                    className="fx-field mt-1 w-full px-2 py-2 text-sm"
                    value={defaultHybridRouting.retrieval}
                    onChange={(event) =>
                      setDefaultHybridRouting((current) => ({
                        ...current,
                        retrieval: event.target.value,
                      }))
                    }
                  >
                    {runtimeEngineOptions.map((engine) => (
                      <option key={`settings-retrieval-${engine}`} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-xs">
                  tooling
                  <select
                    className="fx-field mt-1 w-full px-2 py-2 text-sm"
                    value={defaultHybridRouting.tooling}
                    onChange={(event) =>
                      setDefaultHybridRouting((current) => ({
                        ...current,
                        tooling: event.target.value,
                      }))
                    }
                  >
                    {runtimeEngineOptions.map((engine) => (
                      <option key={`settings-tooling-${engine}`} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-xs">
                  collaboration
                  <select
                    className="fx-field mt-1 w-full px-2 py-2 text-sm"
                    value={defaultHybridRouting.collaboration}
                    onChange={(event) =>
                      setDefaultHybridRouting((current) => ({
                        ...current,
                        collaboration: event.target.value,
                      }))
                    }
                  >
                    {runtimeEngineOptions.map((engine) => (
                      <option key={`settings-collaboration-${engine}`} value={engine}>
                        {engine}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>
          </article>

          <article id="section-user-defaults" className="fx-panel p-3 scroll-mt-32">
            <h2 className="text-sm font-semibold">User defaults</h2>
            <p className="fx-muted text-xs">Personal productivity defaults for review and session management.</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <label className="block text-xs">
                Default kickoff workflow
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={defaultKickoffWorkflow} onChange={(e) => setDefaultKickoffWorkflow(e.target.value)}>
                  <option>Auto-select from intent</option>
                  <option>Investor Outreach Pack</option>
                  <option>Prospect Outreach Pack</option>
                </select>
              </label>
              <label className="block text-xs">
                Preferred review depth
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={preferredReviewDepth} onChange={(e) => setPreferredReviewDepth(e.target.value)}>
                  <option>Concise</option>
                  <option>Standard</option>
                  <option>Detailed</option>
                </select>
              </label>
              <label className="block text-xs md:col-span-2">
                Idle timeout
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={idleTimeout} onChange={(e) => setIdleTimeout(e.target.value)}>
                  <option>15 minutes</option>
                  <option>30 minutes</option>
                  <option>60 minutes</option>
                </select>
              </label>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
