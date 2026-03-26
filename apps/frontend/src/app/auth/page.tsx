import type { Metadata } from "next";

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

function getAuthUiConfig(): AuthUiConfig {
  const authMode = (process.env.FRONTIER_AUTH_MODE ?? "").trim().toLowerCase();
  const provider = (process.env.FRONTIER_AUTH_OIDC_PROVIDER ?? "").trim().toLowerCase();
  const issuer = (process.env.FRONTIER_AUTH_OIDC_ISSUER ?? "").trim();
  const authorizationUrl = (process.env.FRONTIER_AUTH_OIDC_AUTHORIZATION_URL ?? "").trim();
  const signinUrl = (process.env.FRONTIER_AUTH_OIDC_SIGNIN_URL ?? authorizationUrl).trim();
  const signupUrl = (process.env.FRONTIER_AUTH_OIDC_SIGNUP_URL ?? authorizationUrl).trim();
  const scopes = (process.env.FRONTIER_AUTH_OIDC_SCOPES ?? "")
    .split(/\s+/)
    .map((scope) => scope.trim())
    .filter(Boolean);
  const audience = (process.env.FRONTIER_AUTH_OIDC_AUDIENCE ?? "").trim();
  const clientId = (process.env.FRONTIER_AUTH_OIDC_CLIENT_ID ?? "").trim();

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
    if (!issuerUrl) {
      validationError = "OIDC issuer must be a valid absolute http(s) URL.";
    } else if (!oidcRedirectMatchesIssuer(signinUrl, issuer)) {
      validationError = "Sign-in URL must belong to the configured OIDC issuer origin.";
    } else if (!oidcRedirectMatchesIssuer(signupUrl, issuer)) {
      validationError = "Sign-up URL must belong to the configured OIDC issuer origin.";
    }
  }

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
    isConfigured: normalizedMode === "oidc" && Boolean(signinUrl && signupUrl && issuer) && !validationError,
    validationError,
  };
}

export const metadata: Metadata = {
  title: "Sign in | Lattix xFrontier",
  description: "Authenticate with your configured IAM provider to access Lattix xFrontier.",
};

export default function AuthPage() {
  const config = getAuthUiConfig();

  const statusTone = config.isConfigured
    ? "border-[color-mix(in_srgb,var(--fx-success)_45%,var(--ui-border)_55%)] bg-[color-mix(in_srgb,var(--fx-success)_10%,transparent)]"
    : "border-[color-mix(in_srgb,var(--fx-warning)_50%,var(--ui-border)_50%)] bg-[color-mix(in_srgb,var(--fx-warning)_12%,transparent)]";

  return (
    <section className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-6xl items-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="relative overflow-hidden rounded-[2rem] border border-[var(--ui-border)] bg-[radial-gradient(circle_at_top_left,color-mix(in_srgb,var(--fx-primary)_16%,transparent),transparent_36%),linear-gradient(135deg,hsl(var(--card))_0%,color-mix(in_srgb,hsl(var(--card))_86%,hsl(var(--muted))_14%)_100%)] p-8 shadow-[0_24px_90px_rgba(0,0,0,0.18)] sm:p-10">
          <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-[linear-gradient(180deg,transparent,rgba(255,255,255,0.04),transparent)] lg:block" aria-hidden="true" />
          <div className="relative max-w-2xl space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--card))_70%,transparent)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--fx-muted)]">
                <span className="inline-block h-2 w-2 rounded-full bg-[var(--fx-primary)]" />
                Identity gateway
              </div>
              <div className="space-y-3">
                <h1 className="max-w-3xl text-balance font-sans text-[clamp(2.2rem,5vw,4.8rem)] font-semibold leading-[0.94] tracking-[-0.05em] text-[hsl(var(--foreground))]">
                  One frontier, whichever IAM your team already trusts.
                </h1>
                <p className="max-w-2xl text-pretty text-[clamp(0.98rem,1.45vw,1.12rem)] leading-7 text-[color-mix(in_srgb,hsl(var(--foreground))_72%,hsl(var(--muted-foreground))_28%)]">
                  Sign in or create an account through the identity provider configured for this workspace. The same entry point supports a Casdoor preset or another standards-compliant OIDC solution without rewriting the console.
                </p>
              </div>
            </div>

            <div className={`rounded-[1.5rem] border p-4 sm:p-5 ${statusTone}`}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Active identity plane</p>
                  <h2 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-[hsl(var(--foreground))]">{config.authMode === "shared-token" ? "Shared operator token" : config.providerLabel}</h2>
                  <p className="mt-2 max-w-xl text-sm leading-6 text-[color-mix(in_srgb,hsl(var(--foreground))_74%,hsl(var(--muted-foreground))_26%)]">
                    {config.authMode === "shared-token"
                      ? "This environment is using the shared-token fallback instead of interactive IAM login. Ask your platform operator for a bearer token or switch the install to OIDC for a proper sign-in experience."
                      : config.isConfigured
                        ? `Configured against ${config.issuer}. Users can authenticate through the provider and the backend will validate issuer, audience, and JWKS before granting console access.`
                        : config.validationError
                          ? config.validationError
                          : "OIDC is selected, but the IAM endpoints are incomplete. Finish the issuer and sign-in/sign-up URLs in your install environment to activate this portal."}
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

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                {
                  title: "Operator login",
                  body: "Use the provider-hosted sign-in flow instead of passing actor headers around like it’s 2024 and we’ve learned nothing.",
                },
                {
                  title: "Flexible federation",
                  body: "Swap between Casdoor and another OIDC-compatible IAM without changing the console’s auth entry point.",
                },
                {
                  title: "Verified control plane",
                  body: "Backend access stays tied to validated bearer claims, signed internal A2A traffic, and replay protection.",
                },
              ].map((item) => (
                <article key={item.title} className="rounded-[1.25rem] border border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--card))_88%,transparent)] p-4">
                  <h3 className="text-sm font-semibold tracking-[-0.02em] text-[hsl(var(--foreground))]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--fx-muted)]">{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </div>

        <div className="fx-panel flex flex-col justify-between overflow-hidden rounded-[2rem] border p-6 shadow-[0_24px_90px_rgba(0,0,0,0.14)] sm:p-8">
          <div className="space-y-6">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--fx-muted)]">Access the console</p>
              <h2 className="text-[clamp(1.6rem,3vw,2.4rem)] font-semibold tracking-[-0.04em] text-[hsl(var(--foreground))]">
                Sign in or start your account in one place.
              </h2>
              <p className="text-sm leading-6 text-[var(--fx-muted)]">
                The page stays provider-agnostic: both actions point at the configured IAM surface, whether that’s Casdoor or another OIDC-compliant identity service.
              </p>
            </div>

            <div className="grid gap-3">
              <a
                href={config.isConfigured ? config.signinUrl : "#auth-not-configured"}
                className="fx-btn-primary inline-flex min-h-12 items-center justify-center px-4 py-3 text-sm font-semibold no-underline transition hover:translate-y-[-1px]"
                aria-disabled={!config.isConfigured}
              >
                Sign in with {config.providerLabel}
              </a>
              <a
                href={config.isConfigured ? config.signupUrl : "#auth-not-configured"}
                className="fx-btn-secondary inline-flex min-h-12 items-center justify-center px-4 py-3 text-sm font-semibold no-underline transition hover:translate-y-[-1px]"
                aria-disabled={!config.isConfigured}
              >
                Create account
              </a>
            </div>

            <div className="rounded-[1.25rem] border border-dashed border-[var(--ui-border)] bg-[color-mix(in_srgb,hsl(var(--muted))_58%,transparent)] p-4" id="auth-not-configured">
              <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">What happens next</h3>
              <ol className="mt-3 space-y-2 pl-5 text-sm leading-6 text-[var(--fx-muted)]">
                <li>Authenticate with your configured identity provider.</li>
                <li>Return to xFrontier with a verified bearer token or provider session.</li>
                <li>Let the backend enforce issuer, audience, JWKS, and admin policy from one consistent identity plane.</li>
              </ol>
            </div>
          </div>

          <div className="mt-8 space-y-4 border-t border-[var(--ui-border)] pt-5">
            <div className="flex flex-wrap gap-2">
              {(config.scopes.length ? config.scopes : ["openid", "profile", "email"]).map((scope) => (
                <span key={scope} className="fx-pill px-3 py-1 text-[11px] text-[hsl(var(--foreground))]">
                  {scope}
                </span>
              ))}
            </div>
            <p className="max-w-[24rem] text-pretty text-sm text-[var(--fx-muted)]">
              Need a different provider? Update the install-time OIDC values and this page will keep pointing to the right IAM surface.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
