# Deployment

## Local with Docker Compose

Prerequisites:

- Docker
- Python 3.12+

Steps:

1. Copy `.env.example` to `.env`.
2. Run `make bootstrap`.
3. Run `make dev`.
4. Validate with `lattix health` and `make test`.

The local stack now also includes `sandbox-egress-gateway`, which creates the internal Docker egress boundary used by the tool jail.
It also includes `local-gateway`, which routes `LOCAL_STACK_HOST` (for example `frontier.localhost`) to the local Frontier frontend over plain HTTP and proxies `/api/*` to the orchestrator.

For interactive setup, you can run:

`lattix install run`

## Kubernetes with Helm

Install with:

`helm install lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml`

For production, use external Vault and Postgres where appropriate, configure ingress TLS, and replace placeholder secrets.
The chart now includes federation-related values so enterprise operators can preconfigure multi-region peer metadata even before the collaboration fabric is fully implemented.

## Agent development

Scaffold a new agent with:

`lattix agent scaffold --name example-agent`

Then implement the agent logic, add tests, and package the resulting container for Compose or Helm deployment.

If the agent needs tool execution, route those calls through the sandbox subsystem instead of executing directly on the host or inside the agent container.
