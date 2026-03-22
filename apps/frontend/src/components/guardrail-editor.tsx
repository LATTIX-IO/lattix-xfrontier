"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { publishGuardrailRuleset, saveGuardrailRuleset } from "@/lib/api";
import type { GuardrailRuleSet } from "@/types/frontier";

type ControlRow = {
  group: "Jailbreak" | "Content safety" | "Protected materials";
  riskType: string;
  interventionPoint: string;
  action: "Block" | "Review";
};

const defaultControls: ControlRow[] = [
  { group: "Jailbreak", riskType: "Jailbreak", interventionPoint: "User input", action: "Block" },
  { group: "Content safety", riskType: "Hate: Medium blocking", interventionPoint: "User input, Output", action: "Block" },
  { group: "Content safety", riskType: "Self-harm: Medium blocking", interventionPoint: "User input, Output", action: "Block" },
  { group: "Content safety", riskType: "Sexual: Medium blocking", interventionPoint: "User input, Output", action: "Block" },
  { group: "Content safety", riskType: "Violence: Medium blocking", interventionPoint: "User input, Output", action: "Block" },
  { group: "Protected materials", riskType: "Protected material for code", interventionPoint: "Output", action: "Block" },
  { group: "Protected materials", riskType: "Protected material for text", interventionPoint: "Output", action: "Block" },
];

type Props = {
  mode: "new" | "edit";
  ruleset?: GuardrailRuleSet;
};

export function GuardrailEditor({ mode, ruleset }: Props) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"guardrails" | "blocklists">("guardrails");
  const [selectedControlIds, setSelectedControlIds] = useState<string[]>(defaultControls.map((_, i) => String(i)));
  const existingConfig = (ruleset?.config_json ?? {}) as Record<string, unknown>;
  const [displayName, setDisplayName] = useState(ruleset?.name ?? "New Guardrail Set");
  const [stage, setStage] = useState(String(existingConfig.stage ?? "output"));
  const [tripwireAction, setTripwireAction] = useState(String(existingConfig.tripwire_action ?? "reject_content"));
  const [detectSecrets, setDetectSecrets] = useState(Boolean(existingConfig.detect_secrets ?? true));
  const [runInParallel, setRunInParallel] = useState(Boolean(existingConfig.run_in_parallel ?? false));
  const [blockedKeywords, setBlockedKeywords] = useState(Array.isArray(existingConfig.blocked_keywords) ? (existingConfig.blocked_keywords as unknown[]).filter((item): item is string => typeof item === "string").join(", ") : "");
  const [requiredKeywords, setRequiredKeywords] = useState(Array.isArray(existingConfig.required_keywords) ? (existingConfig.required_keywords as unknown[]).filter((item): item is string => typeof item === "string").join(", ") : "");
  const [rejectMessage, setRejectMessage] = useState(String(existingConfig.reject_message ?? "Blocked by policy"));
  const [minLength, setMinLength] = useState(String(existingConfig.min_length ?? ""));
  const [maxLength, setMaxLength] = useState(String(existingConfig.max_length ?? ""));
  const [applyModel, setApplyModel] = useState(String(existingConfig.apply_model ?? "all"));
  const [applyWorkflow, setApplyWorkflow] = useState(String(existingConfig.apply_workflow ?? "all"));
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [publishState, setPublishState] = useState<"idle" | "publishing" | "published" | "error">("idle");
  const publishId = ruleset?.id;

  function parseList(value: string): string[] {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function buildConfigPayload(): Record<string, unknown> {
    const minParsed = Number(minLength);
    const maxParsed = Number(maxLength);
    return {
      stage,
      tripwire_action: tripwireAction,
      detect_secrets: detectSecrets,
      run_in_parallel: runInParallel,
      blocked_keywords: parseList(blockedKeywords),
      required_keywords: parseList(requiredKeywords),
      reject_message: rejectMessage,
      min_length: Number.isFinite(minParsed) && minLength !== "" ? minParsed : null,
      max_length: Number.isFinite(maxParsed) && maxLength !== "" ? maxParsed : null,
      selected_controls: selectedControlIds,
      apply_model: applyModel,
      apply_workflow: applyWorkflow,
    };
  }

  async function handleSaveDraft() {
    setSaveState("saving");
    try {
      await saveGuardrailRuleset({
        id: ruleset?.id,
        name: displayName,
        config_json: buildConfigPayload(),
      });
      setSaveState("saved");
      router.refresh();
    } catch {
      setSaveState("error");
    }
  }

  async function handlePublish() {
    if (!publishId) {
      return;
    }
    setPublishState("publishing");
    try {
      await publishGuardrailRuleset(publishId);
      setPublishState("published");
      router.refresh();
    } catch {
      setPublishState("error");
    }
  }

  function toggleControl(id: string) {
    setSelectedControlIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{mode === "new" ? "Create Guardrail Set" : "Guardrail Set Editor"}</h1>
        <div className="mt-2 max-w-xl">
          <label className="block text-sm">
            Guardrail set name
            <input
              className="fx-field mt-1 w-full px-2 py-2 text-sm"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Core Messaging Guardrails"
            />
          </label>
        </div>
        {ruleset ? <p className="font-mono text-xs text-[var(--foreground)]">guardrail_id: {ruleset.id}</p> : null}
      </header>

      <div className="fx-panel p-1">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab("guardrails")}
            className={`px-3 py-2 text-sm ${activeTab === "guardrails" ? "fx-nav-active" : "hover:bg-[var(--fx-nav-hover)]"}`}
          >
            Guardrails
          </button>
          <button
            onClick={() => setActiveTab("blocklists")}
            className={`px-3 py-2 text-sm ${activeTab === "blocklists" ? "fx-nav-active" : "hover:bg-[var(--fx-nav-hover)]"}`}
          >
            Blocklists
          </button>
        </div>
      </div>

      {activeTab === "guardrails" ? (
        <div className="grid gap-4 xl:grid-cols-[260px_1fr]">
          <aside className="fx-panel p-3">
            <h2 className="mb-2 text-sm font-semibold">Create guardrail controls</h2>
            <ol className="space-y-2 text-xs">
              <li className="border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-2">
                <p className="font-semibold">1. Add controls</p>
                <p className="fx-muted">Select risk controls to detect and respond to flagged behavior.</p>
              </li>
              <li className="border border-[var(--fx-border)] p-2">
                <p className="font-semibold">2. Select agents and models</p>
                <p className="fx-muted">Apply controls to model endpoints and workflow executions.</p>
              </li>
              <li className="border border-[var(--fx-border)] p-2">
                <p className="font-semibold">3. Review</p>
                <p className="fx-muted">Confirm interventions and actions before publishing.</p>
              </li>
            </ol>

            <label className="mt-3 block text-xs">
              Risk group filter
              <select className="fx-field mt-1 w-full px-2 py-2 text-xs">
                <option>All controls</option>
                <option>Jailbreak</option>
                <option>Content safety</option>
                <option>Protected materials</option>
              </select>
            </label>
          </aside>

          <div className="space-y-3">
            <div className="fx-panel overflow-hidden">
              <table className="w-full text-sm">
                <thead className="fx-table-head text-xs">
                  <tr>
                    <th className="px-3 py-2 text-left">Select</th>
                    <th className="px-3 py-2 text-left">Risk type</th>
                    <th className="px-3 py-2 text-left">Intervention point</th>
                    <th className="px-3 py-2 text-left">Action</th>
                    <th className="px-3 py-2 text-left">Group</th>
                  </tr>
                </thead>
                <tbody>
                  {defaultControls.map((control, index) => {
                    const id = String(index);
                    return (
                      <tr key={`${control.group}-${control.riskType}`} className="border-t border-[var(--fx-border)]">
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={selectedControlIds.includes(id)}
                            onChange={() => toggleControl(id)}
                            aria-label={`Select ${control.riskType}`}
                          />
                        </td>
                        <td className="px-3 py-2 text-[var(--foreground)]">{control.riskType}</td>
                        <td className="fx-muted px-3 py-2">{control.interventionPoint}</td>
                        <td className="px-3 py-2 text-[var(--foreground)]">{control.action}</td>
                        <td className="fx-muted px-3 py-2">{control.group}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="fx-panel p-3">
              <h3 className="mb-2 text-sm font-semibold">Apply to targets</h3>
              <div className="grid gap-2 md:grid-cols-2">
                <label className="block text-xs">
                  Models
                  <select className="fx-field mt-1 w-full px-2 py-2 text-xs" value={applyModel} onChange={(event) => setApplyModel(event.target.value)}>
                    <option value="all">All default models</option>
                    <option value="gpt-5.2">gpt-5.2</option>
                    <option value="gpt-5.2-mini">gpt-5.2-mini</option>
                  </select>
                </label>
                <label className="block text-xs">
                  Workflows
                  <select className="fx-field mt-1 w-full px-2 py-2 text-xs" value={applyWorkflow} onChange={(event) => setApplyWorkflow(event.target.value)}>
                    <option value="all">All workflows</option>
                    <option value="investor-outreach-pack">Investor Outreach Pack</option>
                    <option value="prospect-outreach-pack">Prospect Outreach Pack</option>
                  </select>
                </label>
              </div>

              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <label className="block text-xs">
                  Stage
                  <select className="fx-field mt-1 w-full px-2 py-2 text-xs" value={stage} onChange={(event) => setStage(event.target.value)}>
                    <option value="input">Input</option>
                    <option value="output">Output</option>
                    <option value="tool_input">Tool Input</option>
                    <option value="tool_output">Tool Output</option>
                  </select>
                </label>
                <label className="block text-xs">
                  Tripwire action
                  <select className="fx-field mt-1 w-full px-2 py-2 text-xs" value={tripwireAction} onChange={(event) => setTripwireAction(event.target.value)}>
                    <option value="allow">Allow</option>
                    <option value="reject_content">Reject content</option>
                    <option value="raise_exception">Raise exception</option>
                  </select>
                </label>
                <label className="block text-xs md:col-span-2">
                  Blocked keywords (comma-separated)
                  <input
                    className="fx-field mt-1 w-full px-2 py-2 text-xs"
                    value={blockedKeywords}
                    onChange={(event) => setBlockedKeywords(event.target.value)}
                    placeholder="password,private_key,internal-only"
                  />
                </label>
                <label className="block text-xs md:col-span-2">
                  Required keywords (comma-separated)
                  <input
                    className="fx-field mt-1 w-full px-2 py-2 text-xs"
                    value={requiredKeywords}
                    onChange={(event) => setRequiredKeywords(event.target.value)}
                    placeholder="approved,citation"
                  />
                </label>
                <label className="block text-xs">
                  Min length
                  <input
                    className="fx-field mt-1 w-full px-2 py-2 text-xs"
                    value={minLength}
                    onChange={(event) => setMinLength(event.target.value)}
                    inputMode="numeric"
                    placeholder="0"
                  />
                </label>
                <label className="block text-xs">
                  Max length
                  <input
                    className="fx-field mt-1 w-full px-2 py-2 text-xs"
                    value={maxLength}
                    onChange={(event) => setMaxLength(event.target.value)}
                    inputMode="numeric"
                    placeholder="4000"
                  />
                </label>
                <label className="block text-xs md:col-span-2">
                  Reject message
                  <textarea
                    className="fx-field mt-1 min-h-20 w-full px-2 py-2 text-xs"
                    value={rejectMessage}
                    onChange={(event) => setRejectMessage(event.target.value)}
                  />
                </label>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={detectSecrets} onChange={(event) => setDetectSecrets(event.target.checked)} />
                  Detect secrets in payload
                </label>
                <label className="flex items-center gap-2 text-xs">
                  <input type="checkbox" checked={runInParallel} onChange={(event) => setRunInParallel(event.target.checked)} />
                  Run in parallel
                </label>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  onClick={handleSaveDraft}
                  className="fx-btn-secondary px-3 py-2 text-sm"
                  disabled={saveState === "saving"}
                >
                  {saveState === "saving" ? "Saving..." : saveState === "saved" ? "Saved" : "Save draft"}
                </button>
                {publishId ? (
                  <button onClick={handlePublish} className="fx-btn-primary px-3 py-2 text-sm" disabled={publishState === "publishing"}>
                    {publishState === "publishing" ? "Publishing..." : publishState === "published" ? "Published" : "Publish"}
                  </button>
                ) : null}
                {(saveState === "error" || publishState === "error") ? (
                  <p className="text-xs text-red-300">Unable to persist guardrail changes. Check backend connectivity.</p>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="fx-panel p-4">
          <h2 className="mb-2 text-sm font-semibold">Blocklists</h2>
          <p className="fx-muted text-sm">Manage blocked terms and patterns for prompts and outputs.</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div className="border border-[var(--fx-border)] p-3 text-sm">
              <p className="font-semibold">Global restricted terms</p>
              <ul className="fx-muted mt-2 list-disc pl-5 text-xs">
                <li>Confidential customer identifiers</li>
                <li>Unapproved claims language</li>
              </ul>
            </div>
            <div className="border border-[var(--fx-border)] p-3 text-sm">
              <p className="font-semibold">Custom regex patterns</p>
              <p className="fx-muted mt-2 text-xs">Add expression-based filters for workflow-specific blocking.</p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
