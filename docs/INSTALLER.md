# Installer and Public Distribution

Lattix Frontier now includes a public-facing installer flow intended to be published from a public repository.

## Bootstrap commands

### POSIX shells

`curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh`

### PowerShell

`powershell -ExecutionPolicy Bypass -c "iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 | iex"`

## What the installer does

1. Detects the host platform and recommended sandbox prerequisites.
2. Validates core commands like Docker, offers best-effort prerequisite installation when something is missing, and re-checks after any install attempt.
3. Prompts the user for preferred local and/or enterprise configuration.
4. Checks writable install location, vanity hostname safety, port availability, and enterprise tools (`helm`, `kubectl`) when needed.
5. Prompts for sensitive local values like `A2A_JWT_SECRET`; if left blank, securely auto-generates them.
6. Writes an installer-managed local env file at `.installer/local.env` and generated Helm values.
7. Applies best-effort owner-only file permissions to the local env file before optionally launching Docker Compose.
8. Optionally launches the local stack.
9. Prints the resulting local `http://<name>.localhost` URL and enterprise Helm command.

If a prerequisite is missing and automatic installation is not available, is declined, or fails, the installer exits cleanly with a list of missing tools and the next steps to finish setup.

## Local vanity URL

The Docker Compose stack now includes `local-gateway` powered by Caddy, which routes `LOCAL_STACK_HOST` to the Frontier frontend over plain HTTP for local development and proxies `/api/*` requests to the Frontier orchestrator.

## Local secret handling

For local deployments, the installer now handles secrets such as `A2A_JWT_SECRET` during setup:

- Operators can paste a value explicitly.
- If they leave it blank, the installer generates a strong random secret.
- The secret is stored in `.installer/local.env`, not in `answers.json`.
- The installer applies best-effort owner-only permissions to that env file before launching the local stack.

This keeps required runtime secrets out of the interactive answer manifest and out of the normal repo workflow.

## Public repository strategy

To publish this cleanly as a public installer repository, use a slim distribution layout that contains:

- `install/bootstrap.sh`
- `install/bootstrap.ps1`
- `install/frontier-installer.py`
- packaged installer/runtime assets or a release bundle reference

The current monorepo can remain the source of truth while a public repo publishes installer artifacts and release bundles.

## Enterprise federation metadata

The installer can now collect federation cluster name, region, and peer endpoints, and writes those values into generated Helm overrides for enterprise/self-hosted deployments.
