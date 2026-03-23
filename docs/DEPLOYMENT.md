# Deployment

## Local with Docker Compose

Prerequisites:

- Docker
- Python 3.12+

Steps:

1. Copy `.env.example` to `.env`.
2. Run `make bootstrap`.
3. Run `make dev`.
4. Open `http://frontier.localhost` (or your configured `LOCAL_STACK_HOST`) for the gateway-routed frontend and `http://localhost:8000/health` for backend health.
5. Validate with `lattix health` and `make test`.

The intended default local deployment path uses the root `docker-compose.yml`. It includes the added security and platform infrastructure needed for the primary local deployment experience.

This default secure stack exposes:

- frontend via local gateway: `http://frontier.localhost`
- backend: `http://localhost:8000`
- postgres: `localhost:5432`
- vault: `localhost:8200`
- opa: `localhost:8181`
- nats: `localhost:4222`
- jaeger: `localhost:16686`

The gateway-routed frontend uses `/api` and benefits from the fuller local security posture.

## Lightweight local stack (optional)

If you want a simpler local-only stack for faster iteration, use:

`make local-up`

That lightweight stack uses `docker-compose.local.yml`, exposes the frontend at `http://localhost:3000`, the backend at `http://localhost:8000`, and uses `FRONTIER_LOCAL_API_BASE_URL` rather than the gateway-based `/api` path.

For explicit full-stack startup, `make stack-up` remains available and is equivalent to the default secure path.

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
