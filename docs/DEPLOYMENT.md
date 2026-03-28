# Deployment

## Local with Docker Compose

Prerequisites:

- Docker
- Python 3.12+

Steps:

1. Run `curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh`, or on Windows run `powershell -ExecutionPolicy Bypass -c "iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 -UseBasicParsing | iex"`.
2. Follow the interactive installer prompts.
3. The installer auto-runs `lattix up` for the secure stack once installation completes.
4. Open `http://xfrontier.local` (or your configured `LOCAL_STACK_HOST`) for the gateway-routed frontend and use the local gateway or host-only admin bindings for health checks.
5. Validate with `lattix health` and `make test`.

For source-checkout testing, the bootstrap scripts also work directly as `pwsh -File .\install\bootstrap.ps1` and `sh ./install/bootstrap.sh`. When run that way, they use the checkout's bundled installer instead of redownloading `main`, so local branch testing actually exercises the checkout you launched.

The intended default local deployment path uses the root `docker-compose.yml`. It includes the added security and platform infrastructure needed for the primary local deployment experience.

This default secure stack exposes the minimum host-facing surfaces by default:

- frontend via local gateway: `http://xfrontier.local`
- local gateway admin/health endpoint: host-only bind via `LOCAL_GATEWAY_BIND_HOST` (defaults to `127.0.0.1`)
- Jaeger UI: `http://127.0.0.1:16686`

Core control-plane services such as the backend, Postgres, Redis, Neo4j, OPA, NATS, and Vault now stay on the Compose network unless you explicitly add host bindings for debugging.

The gateway-routed frontend uses `/api` and benefits from the fuller local security posture.

## Lightweight local stack (optional)

If you want a simpler local-only stack for faster iteration, use:

`make local-up`

That lightweight stack uses `docker-compose.local.yml`, exposes the frontend at `http://localhost:3000`, the backend at `http://localhost:8000`, and uses `FRONTIER_LOCAL_API_BASE_URL` rather than the gateway-based `/api` path.

Secure local defaults now assume:

- `FRONTIER_RUNTIME_PROFILE=local-secure`
- authenticated operator access
- signed internal A2A messages with replay protection
- generated database credentials instead of checked-in defaults
- no header-only actor trust or direct lightweight localhost shortcuts

For explicit full-stack startup, `make stack-up` remains available and is equivalent to the default secure path.

To tear the local install back down and remove installer-managed state before a fresh test run, use:

`lattix remove`

Equivalent repo-local helpers:

- `make remove`
- `./scripts/frontier.ps1 remove`

For interactive setup, you can run:

`lattix install run`

## Kubernetes with Helm

Install with:

`helm install lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml`

The chart defaults Kubernetes workloads to `FRONTIER_RUNTIME_PROFILE=hosted` and `FRONTIER_REQUIRE_A2A_RUNTIME_HEADERS=true` so the API and orchestrator follow the same hosted contract already enforced in backend profile regressions. The chart currently deploys the control-plane services included under `helm/lattix-frontier/templates/`; agent-specific workloads should be deployed separately until dedicated agent templates are added.

For production, use external Vault and Postgres where appropriate, configure ingress TLS, and replace placeholder secrets, especially the shared `A2A_JWT_SECRET` value rendered by the chart.
The root Compose stack no longer uses Vault dev mode; it now mounts `docker/vault/vault.hcl`, which removes the dev-root-token behavior but still requires proper Vault initialization, unseal, and auth setup for real deployments.
The chart now includes federation-related values so enterprise operators can preconfigure multi-region peer metadata even before the collaboration fabric is fully implemented.

Validation paths:

- local: `make helm-validate` or `./scripts/frontier.ps1 helm-validate` when Helm is installed
- CI: `.github/workflows/ci.yml` now lints and renders the chart on every push/PR

## Agent development

Scaffold a new agent with:

`lattix agent scaffold --name example-agent`

Then implement the agent logic, add tests, and package the resulting container for Compose or Helm deployment.

If the agent needs tool execution, route those calls through the sandbox subsystem instead of executing directly on the host or inside the agent container.
