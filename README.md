# Lattix Frontier

Lattix Frontier is a secure, multi-agent orchestration platform built around four layers:

```text
┌──────────────────────────────────────────────────────────┐
│  LAYER 1: ORCHESTRATION (LangGraph)                      │
│  StateGraph, checkpointing, durable execution            │
├──────────────────────────────────────────────────────────┤
│  LAYER 2: GUARDRAILS (Microsoft Agent Framework filters) │
│  Prompt render, function invocation, DLP, policy gates   │
├──────────────────────────────────────────────────────────┤
│  LAYER 3: AGENT EXECUTION (MAF ChatAgents + A2A)         │
│  Role-based agents, handoffs, tool invocation via MCP    │
├──────────────────────────────────────────────────────────┤
│  LAYER 4: INFRASTRUCTURE (Docker/K8s + security stack)   │
│  Vault, OPA, Envoy, NATS, Biscuit tokens, Presidio       │
└──────────────────────────────────────────────────────────┘
```

## Quick start

1. Copy `.env.example` to `.env` and adjust values as needed.
2. Bootstrap the Python environment.
3. Start the local-first stack.

```text
make bootstrap
make dev
```

On Windows PowerShell, use either the installed CLI or the PowerShell helper:

```text
lattix dev
.\scripts\frontier.ps1 dev
```

For the local browser experience, open `http://frontier.localhost` (or your configured `LOCAL_STACK_HOST`). The local gateway is intentionally HTTP-only for local development, serves the frontend there, and proxies `/api/*` to the orchestrator.

Useful follow-ups:

- `lattix health`
- `lattix agent list`
- `lattix sandbox backend`
- `lattix install run`
- `lattix workflow list`
- `make test`
- `make policy-test`

Policy tests use a repo-local OPA binary when present at `.tools/opa/opa(.exe)`, and otherwise fall back to `opa` on `PATH`. On Windows you can install the pinned local binary with:

```text
.\scripts\frontier.ps1 install-opa
```

## What exists now

This root package adds a release-oriented control plane alongside the existing monorepo subprojects:

- `lattix_frontier/` — root orchestration, agents, security, guardrails, events, API, observability
- `docker-compose.yml` — full local-first stack for orchestrator + built-in agents + infra
- `helm/lattix-frontier/` — Kubernetes deployment chart
- `policies/` — baseline OPA policies and tests
- `tests/` — unit, integration, and e2e tests for the new root platform

## CLI

After installation, the `lattix` command supports:

- `lattix dev`
- `lattix health`
- `lattix agent list`
- `lattix agent scaffold --name <agent-name>`
- `lattix workflow list`
- `lattix workflow run <workflow-name> --task "..."`
- `lattix policy test`
- `lattix policy lint`
- `lattix sandbox backend`
- `lattix sandbox plan --tool-id python -- python -c "print('hello')"`
- `lattix install run`
- `lattix install bootstrap-url`
- `lattix demo <domain>`

## Testing

```text
make lint
make typecheck
make policy-test
make test
```

Windows PowerShell equivalents:

```text
.\scripts\frontier.ps1 lint
.\scripts\frontier.ps1 typecheck
.\scripts\frontier.ps1 policy-test
.\scripts\frontier.ps1 test
```

## Deployment

Local deployment uses Docker Compose:

```text
make dev
```

Kubernetes deployment uses Helm:

```text
helm install lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml
```

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/DEPLOYMENT.md`
- `docs/AGENT_DEVELOPMENT.md`
- `docs/API.md`
- `docs/SANDBOXING.md`
- `docs/INSTALLER.md`

## Notes

The monorepo also still contains existing frontend, backend, workers, and agent repositories. The root `lattix_frontier` package is designed to coexist with those subprojects while providing the cross-cutting orchestration and platform runtime required for the full Frontier release.

