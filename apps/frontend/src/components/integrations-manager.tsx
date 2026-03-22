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
type OauthGrantType = "client_credentials" | "authorization_code";

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

export function IntegrationsManager() {
  const [items, setItems] = useState<IntegrationDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [type, setType] = useState<IntegrationDefinition["type"]>("http");
  const [baseUrl, setBaseUrl] = useState("");
  const [authType, setAuthType] = useState<IntegrationDefinition["auth_type"]>("none");
  const [secretRef, setSecretRef] = useState("");
  const [apiKeyLocation, setApiKeyLocation] = useState<ApiKeyLocation>("header");
  const [apiKeyName, setApiKeyName] = useState("x-api-key");
  const [bearerPrefix, setBearerPrefix] = useState("Bearer");
  const [basicUsername, setBasicUsername] = useState("");
  const [oauthTokenUrl, setOauthTokenUrl] = useState("");
  const [oauthClientId, setOauthClientId] = useState("");
  const [oauthGrantType, setOauthGrantType] = useState<OauthGrantType>("client_credentials");
  const [oauthScopes, setOauthScopes] = useState("");
  const [oauthAudience, setOauthAudience] = useState("");
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
    return {
      method: "oauth2",
      grant_type: oauthGrantType,
      token_url: oauthTokenUrl.trim(),
      client_id: oauthClientId.trim(),
      scopes: oauthScopes
        .split(/[\s,]+/)
        .map((value) => value.trim())
        .filter(Boolean),
      audience: oauthAudience.trim(),
    };
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
    setOauthTokenUrl("");
    setOauthClientId("");
    setOauthGrantType("client_credentials");
    setOauthScopes("");
    setOauthAudience("");
  }

  async function handleCreate() {
    setStatusMessage("");
    const metadata_json: Record<string, unknown> = {
      auth: buildAuthMetadata(),
    };

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
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      const result = await testIntegration(id);
      const warnings = result.diagnostics?.warnings ?? [];
      const warningSuffix = warnings.length > 0 ? ` • warnings: ${warnings.join("; ")}` : "";
      setStatusMessage(`${result.message}${warningSuffix}`);
      await refresh();
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(id: string) {
    await deleteIntegration(id);
    await refresh();
    setStatusMessage("Integration removed.");
  }

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Integration Manager</h1>
        <p className="fx-muted">Configure local connectors for tools, data stores, queues, and APIs.</p>
      </header>

      <div className="fx-panel p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide">Add integration</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm">
            Name
            <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} placeholder="Salesforce API" />
          </label>
          <label className="block text-sm">
            Type
            <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={type} onChange={(event) => setType(event.target.value as IntegrationDefinition["type"])}>
              <option value="http">HTTP API</option>
              <option value="database">Database</option>
              <option value="queue">Queue</option>
              <option value="vector">Vector Store</option>
              <option value="custom">Custom</option>
            </select>
          </label>
          <label className="block text-sm md:col-span-2">
            Base URL / DSN
            <input className="fx-field mt-1 w-full px-2 py-2 text-sm" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1 or postgresql://..." />
          </label>
          <label className="block text-sm">
            Auth type
            <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={authType} onChange={(event) => setAuthType(event.target.value as IntegrationDefinition["auth_type"])}>
              <option value="none">None</option>
              <option value="api_key">API key</option>
              <option value="bearer">Bearer token</option>
              <option value="oauth2">OAuth2</option>
              <option value="basic">Basic</option>
            </select>
          </label>

          {authType === "none" ? (
            <div className="md:col-span-2 rounded-md border border-[var(--fx-border)] bg-[var(--fx-surface-elevated)] p-3 text-xs text-[var(--foreground)]">
              No authentication selected. Secret fields are hidden.
            </div>
          ) : null}

          {authType === "api_key" ? (
            <>
              <label className="block text-sm">
                API key location
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={apiKeyLocation} onChange={(event) => setApiKeyLocation(event.target.value as ApiKeyLocation)}>
                  <option value="header">HTTP Header</option>
                  <option value="query">Query string</option>
                </select>
              </label>
              <label className="block text-sm">
                API key field name
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
            <label className="block text-sm">
              Token prefix
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={bearerPrefix}
                onChange={(event) => setBearerPrefix(event.target.value)}
                placeholder="Bearer"
              />
            </label>
          ) : null}

          {authType === "basic" ? (
            <label className="block text-sm">
              Username
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={basicUsername}
                onChange={(event) => setBasicUsername(event.target.value)}
                placeholder="service-account"
              />
            </label>
          ) : null}

          {authType === "oauth2" ? (
            <>
              <label className="block text-sm md:col-span-2">
                Token URL
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={oauthTokenUrl}
                  onChange={(event) => setOauthTokenUrl(event.target.value)}
                  placeholder="https://login.example.com/oauth2/token"
                />
              </label>
              <label className="block text-sm">
                Client ID
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={oauthClientId}
                  onChange={(event) => setOauthClientId(event.target.value)}
                  placeholder="frontier-client"
                />
              </label>
              <label className="block text-sm">
                Grant type
                <select className="fx-field mt-1 w-full px-2 py-2 text-sm" value={oauthGrantType} onChange={(event) => setOauthGrantType(event.target.value as OauthGrantType)}>
                  <option value="client_credentials">Client credentials</option>
                  <option value="authorization_code">Authorization code</option>
                </select>
              </label>
              <label className="block text-sm">
                Scopes
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={oauthScopes}
                  onChange={(event) => setOauthScopes(event.target.value)}
                  placeholder="read write admin"
                />
              </label>
              <label className="block text-sm">
                Audience (optional)
                <input
                  className="fx-field mt-1 w-full px-2 py-2 text-sm"
                  value={oauthAudience}
                  onChange={(event) => setOauthAudience(event.target.value)}
                  placeholder="https://api.example.com"
                />
              </label>
            </>
          ) : null}

          {authType !== "none" ? (
            <label className="block text-sm md:col-span-2">
              Secret reference
              <input
                className="fx-field mt-1 w-full px-2 py-2 text-sm"
                value={secretRef}
                onChange={(event) => setSecretRef(event.target.value)}
                placeholder={
                  authType === "oauth2"
                    ? "secret/oauth/client-secret"
                    : authType === "basic"
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

      <div className="fx-panel overflow-hidden">
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
                <tr key={item.id} className="border-t border-[var(--fx-border)] align-top">
                  <td className="px-3 py-2">{item.name}</td>
                  <td className="px-3 py-2">{item.type}</td>
                  <td className="px-3 py-2">{item.status}</td>
                  <td className="px-3 py-2">
                    <div>{item.auth_type}</div>
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
                          <p className={lastTest.ok ? "text-emerald-300" : "text-rose-300"}>{lastTest.ok ? "OK" : "Failed"}</p>
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
                      <button onClick={() => handleTest(item.id)} className="fx-btn-secondary px-2 py-1 text-xs" disabled={testingId === item.id}>
                        {testingId === item.id ? "Testing..." : "Test"}
                      </button>
                      <button onClick={() => handleDelete(item.id)} className="fx-btn-warning px-2 py-1 text-xs">Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {statusMessage ? <p className="text-xs text-[var(--foreground)]">{statusMessage}</p> : null}
    </section>
  );
}
