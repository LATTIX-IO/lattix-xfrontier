"use client";

import { useEffect, useState } from "react";
import { deleteIntegration, getIntegrations, saveIntegration, testIntegration } from "@/lib/api";
import type { IntegrationDefinition } from "@/types/frontier";

type LastTestMetadata = {
  at?: string;
  ok?: boolean;
  warnings?: string[];
  checks?: Record<string, boolean>;
};

type ApiKeyLocation = "header" | "query";
type SupportedAuthType = Exclude<IntegrationDefinition["auth_type"], "oauth2">;

function readLastTest(metadata: Record<string, unknown> | undefined): LastTestMetadata | null {
  if (!metadata || typeof metadata !== "object") {
    return null;
  }
  const raw = metadata.last_test;
  if (!raw || typeof raw !== "object") {
    return null;
  }
  return raw as LastTestMetadata;
}

function readAuthConfig(metadata: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!metadata || typeof metadata !== "object") {
    return {};
  }
  const raw = metadata.auth;
  if (!raw || typeof raw !== "object") {
    return {};
  }
  return raw as Record<string, unknown>;
}

function authSummary(item: IntegrationDefinition): string {
  const auth = readAuthConfig(item.metadata_json);
  if (item.auth_type === "none") {
    return "No auth";
  }
  if (item.auth_type === "api_key") {
    const location = String(auth.location ?? "header");
    const keyName = String(auth.key_name ?? "x-api-key");
    return `API key via ${location} (${keyName})`;
  }
  if (item.auth_type === "bearer") {
    const prefix = String(auth.prefix ?? "Bearer");
    return `${prefix} token`;
  }
  if (item.auth_type === "basic") {
    const username = String(auth.username ?? "").trim();
    return username ? `Basic auth (${username})` : "Basic auth";
  }
  if (item.auth_type === "oauth2") {
    const grantType = String(auth.grant_type ?? "client_credentials");
    const clientId = String(auth.client_id ?? "").trim();
    return clientId ? `OAuth2 ${grantType} (${clientId})` : `OAuth2 ${grantType}`;
  }
  return item.auth_type;
}

function integrationStatusTone(status: string): string {
  if (/configured|active|healthy|connected/i.test(status)) {
    return "border-[color-mix(in_srgb,var(--fx-success)_36%,var(--ui-border))] bg-[color-mix(in_srgb,var(--fx-success)_12%,transparent)] text-[var(--foreground)]";
  }
  if (/failed|error|blocked/i.test(status)) {
    return "border-[color-mix(in_srgb,var(--fx-danger)_36%,var(--ui-border))] bg-[color-mix(in_srgb,var(--fx-danger)_10%,transparent)] text-[var(--foreground)]";
  }
  return "border-[var(--ui-border)] bg-[hsl(var(--card))] text-[var(--foreground)]";
}

export function IntegrationsManager() {
  const [items, setItems] = useState<IntegrationDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [type, setType] = useState<IntegrationDefinition["type"]>("http");
  const [baseUrl, setBaseUrl] = useState("");
  const [authType, setAuthType] = useState<SupportedAuthType>("none");
  const [secretRef, setSecretRef] = useState("");
  const [apiKeyLocation, setApiKeyLocation] = useState<ApiKeyLocation>("header");
  const [apiKeyName, setApiKeyName] = useState("x-api-key");
  const [bearerPrefix, setBearerPrefix] = useState("Bearer");
  const [basicUsername, setBasicUsername] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [testingId, setTestingId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const integrations = await getIntegrations();
      setItems(integrations);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (authType === "none") {
      setSecretRef("");
    }
  }, [authType]);

  function buildAuthMetadata(): Record<string, unknown> {
    if (authType === "none") {
      return { method: "none" };
    }
    if (authType === "api_key") {
      return {
        method: "api_key",
        location: apiKeyLocation,
        key_name: apiKeyName.trim() || "x-api-key",
      };
    }
    if (authType === "bearer") {
      return {
        method: "bearer",
        prefix: bearerPrefix.trim() || "Bearer",
      };
    }
    if (authType === "basic") {
      return {
        method: "basic",
        username: basicUsername.trim(),
      };
    }
    return { method: "none" };
  }

  function resetForm() {
    setName("");
    setType("http");
    setBaseUrl("");
    setAuthType("none");
    setSecretRef("");
    setApiKeyLocation("header");
    setApiKeyName("x-api-key");
    setBearerPrefix("Bearer");
    setBasicUsername("");
  }

  async function handleCreate() {
    setStatusMessage("");
    const metadata_json: Record<string, unknown> = {
      auth: buildAuthMetadata(),
    };
    try {
      await saveIntegration({
        name: name.trim() || "Untitled Integration",
        type,
        base_url: baseUrl,
        auth_type: authType,
        secret_ref: authType === "none" ? "" : secretRef.trim(),
        status: "draft",
        metadata_json,
      });
      resetForm();
      await refresh();
      setStatusMessage("Integration saved.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Unable to save integration.");
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      const result = await testIntegration(id);
      const warnings = result.diagnostics?.warnings ?? [];
      const warningSuffix = warnings.length > 0 ? ` • warnings: ${warnings.join("; ")}` : "";
      setStatusMessage(`${result.message}${warningSuffix}`);
      await refresh();
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Unable to test integration.");
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteIntegration(id);
      await refresh();
      setStatusMessage("Integration removed.");
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Unable to remove integration.");
    }
  }

  return (
    <section className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-4 rounded-[1.7rem] border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--card))_97%,hsl(var(--background))_3%)] px-5 py-4 shadow-[0_22px_56px_rgba(15,23,42,0.06)]">
        <div className="max-w-2xl">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">Builder workspace</p>
          <h1 className="mt-2 text-[1.5rem] font-semibold tracking-[-0.03em] text-[var(--foreground)]">Integration Manager</h1>
          <p className="mt-2 text-sm leading-6 text-[var(--fx-muted)]">Configure local connectors for tools, data stores, queues, and APIs without losing the runtime posture or secret-handling rules attached to them.</p>
        </div>
        <div className="grid min-w-[220px] gap-2 sm:grid-cols-2">
          <div className="rounded-[1rem] border border-[var(--fx-border)] bg-[hsl(var(--card)/0.8)] px-3 py-2.5">
            <p className="text-[0.72rem] font-medium text-[var(--fx-muted)]">Configured</p>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">{items.length}</p>
          </div>
          <div className="rounded-[1rem] border border-[var(--fx-border)] bg-[hsl(var(--card)/0.8)] px-3 py-2.5">
            <p className="text-[0.72rem] font-medium text-[var(--fx-muted)]">Auth modes</p>
            <p className="mt-1 text-lg font-semibold text-[var(--foreground)]">4</p>
          </div>
        </div>
      </header>

      <div className="fx-panel rounded-[1.6rem] p-5 shadow-[0_20px_48px_rgba(15,23,42,0.05)]">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">New connector</p>
            <h2 className="mt-2 text-[1.1rem] font-semibold tracking-[-0.02em] text-[var(--foreground)]">Add integration</h2>
            <p className="mt-1 text-sm leading-6 text-[var(--fx-muted)]">Register the endpoint, choose the auth shape the runtime can actually exercise, and keep credentials behind a secret reference.</p>
          </div>
          <div className="fx-pill px-3 py-1.5 text-[0.72rem] font-medium text-[var(--fx-muted)]">Secrets stay server-side</div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm text-[var(--foreground)]">
            <span className="font-medium">Name</span>
            <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} placeholder="Salesforce API" />
          </label>
          <label className="block text-sm text-[var(--foreground)]">
            <span className="font-medium">Type</span>
            <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={type} onChange={(event) => setType(event.target.value as IntegrationDefinition["type"])}>
              <option value="http">HTTP API</option>
              <option value="database">Database</option>
              <option value="queue">Queue</option>
              <option value="vector">Vector Store</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <label className="block text-sm text-[var(--foreground)] md:col-span-2">
            <span className="font-medium">Base URL / DSN</span>
            <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1 or postgresql://..." />
          </label>
          <label className="block text-sm text-[var(--foreground)]">
            <span className="font-medium">Auth type</span>
            <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={authType} onChange={(event) => setAuthType(event.target.value as SupportedAuthType)}>
              <option value="none">None</option>
              <option value="api_key">API key</option>
              <option value="bearer">Bearer token</option>
              <option value="basic">Basic</option>
            </select>
            <span className="mt-1 block text-[11px] fx-muted">
              Interactive OAuth2 is not wired through the backend test/send path yet, so new integrations are limited to auth modes the runtime can actually exercise.
            </span>
          </label>

          {authType === "none" ? (
            <div className="md:col-span-2 rounded-[1rem] border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-3 text-xs text-[var(--foreground)]">
              No authentication selected. Secret fields are hidden.
            </div>
          ) : null}

          {authType === "api_key" ? (
            <>
              <label className="block text-sm text-[var(--foreground)]">
                <span className="font-medium">API key location</span>
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={apiKeyLocation} onChange={(event) => setApiKeyLocation(event.target.value as ApiKeyLocation)}>
                  <option value="header">HTTP Header</option>
                  <option value="query">Query string</option>
                </select>
              </label>
              <label className="block text-sm text-[var(--foreground)]">
                <span className="font-medium">API key field name</span>
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={apiKeyName}
                  onChange={(event) => setApiKeyName(event.target.value)}
                  placeholder="x-api-key"
                />
              </label>
            </>
          ) : null}

          {authType === "bearer" ? (
            <label className="block text-sm text-[var(--foreground)]">
              <span className="font-medium">Token prefix</span>
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={bearerPrefix}
                onChange={(event) => setBearerPrefix(event.target.value)}
                placeholder="Bearer"
              />
            </label>
          ) : null}

          {authType === "basic" ? (
            <label className="block text-sm text-[var(--foreground)]">
              <span className="font-medium">Username</span>
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={basicUsername}
                onChange={(event) => setBasicUsername(event.target.value)}
                placeholder="service-account"
              />
            </label>
          ) : null}

          {authType !== "none" ? (
            <label className="block text-sm text-[var(--foreground)] md:col-span-2">
              <span className="font-medium">Secret reference</span>
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={secretRef}
                onChange={(event) => setSecretRef(event.target.value)}
                placeholder={
                  authType === "basic"
                      ? "secret/db/password"
                      : "secret/integrations/service-token"
                }
              />
              <span className="mt-1 block text-[11px] fx-muted">
                Use a secret reference path (for example: <code>secret/team/name</code>) — do not paste raw credentials.
              </span>
            </label>
          ) : null}
        </div>

        <div className="mt-3">
          <button onClick={handleCreate} className="fx-btn-primary px-3 py-2 text-sm">
            Save integration
          </button>
        </div>
      </div>

      <div className="fx-panel overflow-hidden rounded-[1.6rem] shadow-[0_20px_48px_rgba(15,23,42,0.05)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--ui-border)] px-4 py-4">
          <div>
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-[var(--fx-muted)]">Inventory</p>
            <h2 className="mt-2 text-[1.05rem] font-semibold tracking-[-0.02em] text-[var(--foreground)]">Saved integrations</h2>
          </div>
          <div className="fx-pill px-3 py-1.5 text-[0.72rem] font-medium text-[var(--fx-muted)]">Test before promoting to live traffic</div>
        </div>
        <table className="w-full text-sm">
          <thead className="fx-table-head">
            <tr>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Type</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Auth</th>
              <th className="px-3 py-2 text-left">Secret ref</th>
              <th className="px-3 py-2 text-left">Last test</th>
              <th className="px-3 py-2 text-left">Base URL / DSN</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-3 py-3 text-xs text-[var(--foreground)]" colSpan={8}>Loading integrations...</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-xs text-[var(--foreground)]" colSpan={8}>No integrations configured yet.</td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-[var(--fx-border)] align-top hover:bg-[hsl(var(--muted)/0.16)]">
                  <td className="px-3 py-3 font-medium text-[var(--foreground)]">{item.name}</td>
                  <td className="px-3 py-3">
                    <span className="fx-pill px-2.5 py-1 text-[0.72rem] font-medium text-[var(--foreground)]">{item.type}</span>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[0.72rem] font-medium ${integrationStatusTone(item.status)}`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div>
                      <span className="fx-pill px-2.5 py-1 text-[0.72rem] font-medium text-[var(--foreground)]">{item.auth_type}</span>
                    </div>
                    <div className="fx-muted text-[11px]">{authSummary(item)}</div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{item.secret_ref || "(none)"}</td>
                  <td className="px-3 py-2 text-xs">
                    {(() => {
                      const lastTest = readLastTest(item.metadata_json);
                      if (!lastTest) {
                        return <span className="fx-muted">Not tested</span>;
                      }
                      return (
                        <div className="space-y-0.5">
                          <p className={lastTest.ok ? "text-[var(--fx-success)]" : "text-[var(--fx-danger)]"}>{lastTest.ok ? "OK" : "Failed"}</p>
                          {Array.isArray(lastTest.warnings) && lastTest.warnings.length > 0 ? (
                            <p className="fx-muted">{lastTest.warnings.length} warning(s)</p>
                          ) : null}
                        </div>
                      );
                    })()}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{item.base_url || "(unset)"}</td>
                  <td className="px-3 py-2">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => handleTest(item.id)} className="fx-btn-secondary px-2.5 py-1.5 text-xs" disabled={testingId === item.id}>
                        {testingId === item.id ? "Testing..." : "Test"}
                      </button>
                      <button onClick={() => handleDelete(item.id)} className="fx-btn-warning px-2.5 py-1.5 text-xs">Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {statusMessage ? <p className="rounded-[1rem] border border-[var(--fx-border)] bg-[hsl(var(--card)/0.84)] px-3 py-2 text-xs text-[var(--foreground)]">{statusMessage}</p> : null}
    </section>
  );
}
