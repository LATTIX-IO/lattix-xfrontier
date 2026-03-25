# Installer and Public Distribution

Lattix xFrontier now includes a public-facing installer flow intended to be published from a public repository.

## Bootstrap commands

### Public raw bootstrap URLs

#### POSIX shells

`curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh`

#### PowerShell

`powershell -ExecutionPolicy Bypass -c "iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 -UseBasicParsing | iex"`

### From a local source checkout

#### PowerShell

`pwsh -File .\install\bootstrap.ps1`

#### POSIX shells

`sh ./install/bootstrap.sh`

The PowerShell variant includes `-UseBasicParsing` so it works cleanly in Windows PowerShell 5.1 without the legacy web-parsing prompt.

A future vanity URL such as `https://install.lattix.io/xfrontier.sh` can safely redirect or proxy to the same bootstrap script.

## What the installer does

1. Detects the host platform and recommended sandbox prerequisites.
2. Validates core commands like Docker, offers best-effort prerequisite installation when something is missing, and re-checks after any install attempt.
3. Prompts the user for preferred local and/or enterprise configuration.
4. Checks writable install location, vanity hostname safety, port availability, and enterprise tools (`helm`, `kubectl`) when needed.
5. Prompts for secure local authentication mode and sensitive values like `A2A_JWT_SECRET`; if left blank, required local secrets are securely auto-generated.
6. Writes the installer-managed env file for the secure local stack at `.installer/local-secure.env`, plus generated Helm values.
7. Applies best-effort owner-only file permissions to the local env file before optionally launching Docker Compose.
8. Optionally launches the local stack.
9. Prints the resulting local `http://<name>.localhost` URL and enterprise Helm command.

If a prerequisite is missing and automatic installation is not available, is declined, or fails, the installer exits cleanly with a list of missing tools and the next steps to finish setup.

## Removing a local install

For repeated install-testing, the canonical removal path is:

`lattix remove`

Equivalent repo-local helpers:

- `make remove`
- `./scripts/frontier.ps1 remove`

The remove flow:

1. Stops the secure and lightweight Docker Compose stacks when installer-managed env files are present.
2. Removes the Compose volumes and orphaned containers for those stacks.
3. Deletes installer-managed env files under `.installer/`.

It intentionally does **not** delete the repository checkout or your top-level `.env` file.

## Local vanity URL

The Docker Compose stack now includes `local-gateway` powered by Caddy, which routes `LOCAL_STACK_HOST` to the Frontier frontend over plain HTTP for local development, proxies `/api/*` requests to the canonical backend service, and exposes the bundled Casdoor surface at `http://casdoor.localhost`.

## Local secret handling

For local deployments, the installer now handles secrets such as `A2A_JWT_SECRET` during setup:

- Operators can paste a value explicitly.
- If they leave it blank, the installer generates a strong random secret.
- In explicit shared-token mode, the installer also generates `FRONTIER_API_BEARER_TOKEN`, `POSTGRES_PASSWORD`, and `NEO4J_PASSWORD` for the local stack.
- The generated secret is written into the installer-managed secure env file (`.installer/local-secure.env`) rather than into `answers.json`.
- The installer applies best-effort owner-only permissions to the generated env file before launching the local stack.

This keeps required runtime secrets out of the interactive answer manifest and out of the normal repo workflow.

## Local authentication options

The installer now supports two secure-local operator authentication modes:

- **OIDC** (default) — the installer writes issuer, audience, JWKS, client, and endpoint metadata for an operator identity provider. Casdoor is the default preset, but operators can instead point the install at an external OIDC-compliant IAM solution.
- **Shared bearer token** (fallback) — generates `FRONTIER_API_BEARER_TOKEN` for backend/API use when an operator does not want to wire up OIDC yet. The installer no longer injects this token into browser-visible `NEXT_PUBLIC_*` frontend configuration.

OIDC setup is intentionally flexible:

- **Casdoor preset** — uses Casdoor-oriented defaults and naming for a turnkey local IAM option.
- **External OIDC** — accepts arbitrary issuer, audience, JWKS, authorization URL, token URL, sign-in URL, sign-up URL, client ID, and scopes so the same Frontier install can sit behind another IAM solution.

That keeps operator login flexible while still allowing agents, workflows, and internal services to trust a single verified operator identity plane.

The frontend now includes a generic auth portal at `/auth`. It reads the installer-emitted OIDC environment values and presents provider-hosted **Sign in** and **Create account** actions that can point at Casdoor or another IAM solution without changing the UI flow.

The installer also emits a bootstrap admin identity contract for secure-local installs:

- `FRONTIER_BOOTSTRAP_ADMIN_USERNAME`
- `FRONTIER_BOOTSTRAP_ADMIN_EMAIL`
- `FRONTIER_BOOTSTRAP_ADMIN_SUBJECT`
- `FRONTIER_ADMIN_ACTORS`
- `FRONTIER_BUILDER_ACTORS`

By default, the install-created operator resolves to `frontier-admin` / `admin@<hostname>.localhost`, and those identifiers are treated as both **admin** and **builder-capable** when the authenticated claims match.

In both modes, the generated secure-local profile sets:

- `FRONTIER_RUNTIME_PROFILE=local-secure`
- `FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS=true`
- `FRONTIER_ALLOW_HEADER_ACTOR_AUTH=false`

That means secure local installs fail closed by default, rather than trusting unsigned identity headers.

## Secure defaults for Casdoor and external OIDC

When the installer is configured for Casdoor or another OIDC provider, it keeps the same platform security baseline:

- signed internal A2A messages stay enabled
- replay protection stays enabled
- operator requests must present verified bearer tokens
- header-only actor spoofing remains disabled
- generated local database credentials are still unique per install

The backend already validates OIDC bearer tokens generically through issuer, audience, and JWKS settings, so the installer-generated contract works for Casdoor and for other standards-compliant IAM providers.
For local secure deployments, the default Casdoor endpoints intentionally use `http://casdoor.localhost` so they match the Docker Compose + Caddy topology exactly. Non-local OIDC providers are still expected to use HTTPS.

## Public repository strategy

To publish this cleanly as a public installer repository, use a slim distribution layout that contains:

- `install/bootstrap.sh`
- `install/bootstrap.ps1`
- `install/frontier-installer.py`
- packaged installer/runtime assets or a release bundle reference

The current monorepo can remain the source of truth while a public repo publishes installer artifacts and release bundles.

## Enterprise federation metadata

The installer can now collect federation cluster name, region, and peer endpoints, and writes those values into generated Helm overrides for enterprise/self-hosted deployments.
