import type { Metadata } from "next";

import { LocalAuthPanel } from "@/components/auth/local-auth-panel";
import { getOperatorSession } from "@/lib/api";
import type { OperatorSession } from "@/types/frontier";

export const dynamic = "force-dynamic";

type AuthUiConfig = {
  authMode: "oidc" | "shared-token" | "unknown";
  provider: string;
  providerLabel: string;
  issuer: string;
  signinUrl: string;
  signupUrl: string;
  scopes: string[];
  audience: string;
  clientId: string;
  isConfigured: boolean;
  validationError: string;
  browserFlowConfigured: boolean;
  browserFlowError: string;
};

type SearchParamValue = string | string[] | undefined;

type AuthPageProps = {
  searchParams?: Promise<Record<string, SearchParamValue>> | Record<string, SearchParamValue>;
};

function isLocalHostname(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase();
  return normalized === "localhost" || normalized === "127.0.0.1" || normalized === "::1" || normalized.endsWith(".localhost");
}

function parseAbsoluteHttpUrl(value: string): URL | null {
  const candidate = value.trim();
  if (!candidate) {
    return null;
  }
  try {
    const parsed = new URL(candidate);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return null;
    }
    if (!parsed.hostname || parsed.username || parsed.password || parsed.hash) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function oidcRedirectMatchesIssuer(candidateUrl: string, issuer: string): boolean {
  const candidate = parseAbsoluteHttpUrl(candidateUrl);
  const parsedIssuer = parseAbsoluteHttpUrl(issuer);
  if (!candidate || !parsedIssuer) {
    return false;
  }
  if (candidate.origin !== parsedIssuer.origin) {
    return false;
  }
  if (parsedIssuer.protocol !== "https:" && !isLocalHostname(parsedIssuer.hostname)) {
    return false;
  }
  return true;
}

function firstSearchParamValue(value: SearchParamValue): string {
  if (Array.isArray(value)) {
    return String(value[0] ?? "").trim();
  }
  return String(value ?? "").trim();
}

function getAuthUiConfigFromSession(session: OperatorSession | null): AuthUiConfig {
  const authMode = String(session?.auth_mode ?? process.env.FRONTIER_AUTH_MODE ?? "").trim().toLowerCase();
  const provider = String(
    session?.oidc?.provider
      ?? session?.provider
      ?? process.env.FRONTIER_AUTH_OIDC_PROVIDER
      ?? "",
  ).trim().toLowerCase();
  const issuer = String(session?.oidc?.issuer ?? process.env.FRONTIER_AUTH_OIDC_ISSUER ?? "").trim();
  const authorizationUrl = (process.env.FRONTIER_AUTH_OIDC_AUTHORIZATION_URL ?? "").trim();
  const signinUrl = (process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL ?? authorizationUrl).trim();
  const signupUrl = (process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL ?? authorizationUrl).trim();
  const scopes = (process.env.FRONTIER_AUTH_OIDC_SCOPES ?? "")
    .split(/\s+/)
    .map((scope) => scope.trim())
    .filter(Boolean);
  const audience = String(session?.oidc?.audience ?? process.env.FRONTIER_AUTH_OIDC_AUDIENCE ?? "").trim();
  const clientId = (process.env.FRONTIER_AUTH_OIDC_CLIENT_ID ?? "").trim();
  const browserFlowConfigured = Boolean(session?.oidc?.browser_flow_configured);
  const browserFlowError = String(session?.oidc?.browser_flow_error ?? "").trim();
  const sessionConfigured = Boolean(session?.oidc?.configured);

  const normalizedMode: AuthUiConfig["authMode"] = authMode === "oidc"
    ? "oidc"
    : authMode === "shared-token"
      ? "shared-token"
      : "unknown";

  const providerLabel = provider === "casdoor"
    ? "Casdoor"
    : provider === "oidc"
      ? "OIDC Provider"
      : provider
        ? provider.replace(/[-_]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
        : "OIDC Provider";

  let validationError = "";
  const issuerUrl = parseAbsoluteHttpUrl(issuer);
  if (normalizedMode === "oidc") {
    const backendValidationError = session?.oidc?.validation_error?.trim() ?? "";
    if (backendValidationError) {
      validationError = backendValidationError;
    } else if (!browserFlowConfigured) {
      if (!issuerUrl) {
        validationError = "OIDC issuer must be a valid absolute http(s) URL.";
      } else if (!oidcRedirectMatchesIssuer(signinUrl, issuer)) {
        validationError = "Sign-in URL must belong to the configured OIDC issuer origin.";
      } else if (!oidcRedirectMatchesIssuer(signupUrl, issuer)) {
        validationError = "Sign-up URL must belong to the configured OIDC issuer origin.";
      }
    }
  }

  const redirectFlowConfigured = Boolean(signinUrl && signupUrl && issuer)
    && Boolean(sessionConfigured || Boolean(signinUrl && signupUrl && issuer))
    && !validationError;
  const isConfigured = normalizedMode === "oidc"
    && !validationError
    && (browserFlowConfigured || redirectFlowConfigured);

  return {
    authMode: normalizedMode,
    provider,
    providerLabel,
    issuer,
    signinUrl,
    signupUrl,
    scopes,
    audience,
    clientId,
    isConfigured,
    validationError,
    browserFlowConfigured,
    browserFlowError,
  };
}

export const metadata: Metadata = {
  title: "Sign in | Lattix xFrontier",
  description: "Authenticate with your configured IAM provider to access Lattix xFrontier.",
};

export default async function AuthPage({ searchParams }: AuthPageProps = {}) {
  const [operatorSession, resolvedSearchParams] = await Promise.all([
    getOperatorSession(),
    Promise.resolve(searchParams ?? {}),
  ]);
  const config = getAuthUiConfigFromSession(operatorSession);
  const issuerUrl = parseAbsoluteHttpUrl(config.issuer);
  const useLocalCasdoorPanel = config.isConfigured
    && config.provider === "casdoor"
    && Boolean(issuerUrl?.hostname && isLocalHostname(issuerUrl.hostname));
  const externalOidcBrowserSupported = config.authMode === "oidc"
    && config.isConfigured
    && config.browserFlowConfigured
    && !useLocalCasdoorPanel;
  const browserInteractiveAuthSupported = useLocalCasdoorPanel || externalOidcBrowserSupported;
  const authQueryError = firstSearchParamValue(resolvedSearchParams.error);

  const browserAuthStatusMessage = config.authMode === "shared-token"
    ? "This environment is using the shared-token fallback instead of interactive IAM login. The browser cannot mint or store that operator token here, so an admin has to provision credentials out of band or switch the install to local OIDC-backed sign-in."
    : browserInteractiveAuthSupported
      ? useLocalCasdoorPanel
        ? `Configured against ${config.issuer}. Users can authenticate through the provider and the backend will validate issuer, audience, and JWKS before granting console access.`
        : `Configured against ${config.issuer}. Browser redirects now land back in xFrontier through the backend callback exchange, so external OIDC sign-in completes end to end.`
      : config.isConfigured
        ? config.browserFlowError
          ? config.browserFlowError
          : `Configured against ${config.issuer}, but browser sign-in is still missing required callback or token-exchange settings.`
        : config.validationError
          ? config.validationError
          : "OIDC is selected, but the IAM endpoints are incomplete. Finish the issuer and sign-in/sign-up URLs in your install environment to activate this portal.";

  const statusTone = browserInteractiveAuthSupported
    ? "border-[color-mix(in_srgb,var(--fx-success)_45%,var(--ui-border)_55%)] bg-[color-mix(in_srgb,var(--fx-success)_10%,transparent)]"
    : "border-[color-mix(in_srgb,var(--fx-warning)_50%,var(--ui-border)_50%)] bg-[color-mix(in_srgb,var(--fx-warning)_12%,transparent)]";

  const authPageSummary = useLocalCasdoorPanel
    ? "Sign in with local operator credentials without leaving xFrontier."
    : config.authMode === "shared-token"
      ? "Interactive browser login is unavailable in this shared-token environment."
      : externalOidcBrowserSupported
        ? "Start browser sign-in and finish the callback flow in xFrontier."
        : "Browser login becomes available once the OIDC flow is configured end to end.";

  const actionPanelSummary = useLocalCasdoorPanel
    ? "Use your existing operator account or create one here."
    : externalOidcBrowserSupported
      ? "Use the configured identity provider to continue."
      : "This environment shows the configured provider, but interactive actions stay disabled until the flow is complete.";

  return (
    <section className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-6xl items-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid w-full gap-4 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="relative overflow-hidden border border-[var(--ui-border)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--fx-primary)_5%,transparent),transparent_20%),linear-gradient(135deg,hsl(var(--card))_0%,color-mix(in_srgb,hsl(var(--card))_92%,hsl(var(--muted))_8%)_100%)] p-6 sm:p-8">
          <div className="absolute inset-y-0 right-0 hidden w-px bg-[var(--ui-border)] lg:block" aria-hidden="true" />
          <div className="relative max-w-2xl space-y-6">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 border border-[var(--ui-border)] bg-[hsl(var(--card))] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--fx-muted)]">
                <span className="inline-block h-2 w-2 bg-[var(--fx-primary)]" />
                Identity gateway
              </div>
              <div className="space-y-3">
                <h1 className="max-w-3xl text-balance text-[clamp(2rem,4.4vw,4rem)] font-semibold uppercase leading-[0.94] tracking-[-0.05em] text-[hsl(var(--foreground))]">
                  Sign in to xFrontier.
                </h1>
                <p className="max-w-2xl text-pretty text-[clamp(0.98rem,1.45vw,1.12rem)] leading-7 text-[color-mix(in_srgb,hsl(var(--foreground))_72%,hsl(var(--muted-foreground))_28%)]">
                  {authPageSummary}
                </p>
              </div>
            </div>

            {authQueryError ? (
              <div className="border border-[color-mix(in_srgb,var(--fx-danger)_50%,var(--ui-border)_50%)] bg-[color-mix(in_srgb,var(--fx-danger)_10%,transparent)] p-4 text-sm leading-6 text-[hsl(var(--foreground))]">
                {authQueryError}
              </div>
            ) : null}

            <div className={`border p-4 sm:p-5 ${statusTone}`}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Authentication status</p>
                  <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[hsl(var(--foreground))]">{config.authMode === "shared-token" ? "Shared operator token" : config.providerLabel}</h2>
                  <p className="mt-2 max-w-xl text-sm leading-6 text-[color-mix(in_srgb,hsl(var(--foreground))_74%,hsl(var(--muted-foreground))_26%)]">
                    {browserAuthStatusMessage}
                  </p>
                </div>
                <div className="grid gap-2 text-right text-xs text-[var(--fx-muted)] sm:min-w-[12rem]">
                  <div>
                    <span className="block uppercase tracking-[0.14em]">Audience</span>
                    <span className="mt-1 block truncate text-[hsl(var(--foreground))]">{config.audience || "Not configured"}</span>
                  </div>
                  <div>
                    <span className="block uppercase tracking-[0.14em]">Client</span>
                    <span className="mt-1 block truncate text-[hsl(var(--foreground))]">{config.clientId || "Provider-managed"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="fx-panel flex flex-col justify-between overflow-hidden border p-5 sm:p-6">
          <div className="space-y-6">
            <div className="space-y-3 border-b border-[var(--ui-border)] pb-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Access the console</p>
              <h2 className="text-[clamp(1.5rem,3vw,2.2rem)] font-semibold uppercase tracking-[-0.03em] text-[hsl(var(--foreground))]">
                Continue with your configured sign-in flow.
              </h2>
              <p className="text-sm leading-6 text-[var(--fx-muted)]">
                {actionPanelSummary}
              </p>
            </div>

            {useLocalCasdoorPanel ? (
              <LocalAuthPanel providerLabel={config.providerLabel} />
            ) : externalOidcBrowserSupported ? (
              <div className="grid gap-3">
                <a
                  href="/api/auth/oidc/start?intent=signin"
                  className="fx-btn-primary inline-flex min-h-12 items-center justify-center border border-[color-mix(in_srgb,var(--fx-primary)_70%,black_30%)] px-4 py-3 text-sm font-semibold uppercase tracking-[0.08em]"
                >
                  Sign in with {config.providerLabel}
                </a>
                <a
                  href="/api/auth/oidc/start?intent=signup"
                  className="fx-btn-secondary inline-flex min-h-12 items-center justify-center px-4 py-3 text-sm font-semibold uppercase tracking-[0.08em]"
                >
                  Create account
                </a>
                <p className="text-sm leading-6 text-[var(--fx-muted)]">
                  {browserAuthStatusMessage}
                </p>
              </div>
            ) : (
              <div className="grid gap-3">
                <button
                  type="button"
                  className="fx-btn-primary inline-flex min-h-12 items-center justify-center border border-[color-mix(in_srgb,var(--fx-primary)_70%,black_30%)] px-4 py-3 text-sm font-semibold uppercase tracking-[0.08em] opacity-60"
                  disabled
                >
                  Sign in with {config.providerLabel}
                </button>
                <button
                  type="button"
                  className="fx-btn-secondary inline-flex min-h-12 items-center justify-center px-4 py-3 text-sm font-semibold uppercase tracking-[0.08em] opacity-60"
                  disabled
                >
                  Create account
                </button>
                <p className="text-sm leading-6 text-[var(--fx-muted)]">
                  {browserAuthStatusMessage}
                </p>
              </div>
            )}

            <div className="border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--muted))_46%,transparent)] p-4" id="auth-not-configured">
              <h3 className="text-sm font-semibold uppercase tracking-[0.08em] text-[hsl(var(--foreground))]">Before you continue</h3>
              <p className="mt-3 text-sm leading-6 text-[var(--fx-muted)]">
                {useLocalCasdoorPanel
                  ? "Local sign-in creates the xFrontier operator session directly after your credentials are verified."
                  : externalOidcBrowserSupported
                    ? "Browser sign-in returns through xFrontier so the backend can finish the callback and establish the operator session."
                    : "If you need interactive login here, finish the OIDC callback setup or provision credentials through your existing admin workflow."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
