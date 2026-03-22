# Lattix xFrontier

Lattix xFrontier is a secure, local-first multi-agent orchestration platform licensed under the GNU Affero General Public License v3.0-or-later (AGPLv3+). The public repository contains the open-source core, while optional private agent assets and environment overlays can still live outside the public tree.

Lattix xFrontier is an independent project created by Lattix. It is not affiliated with, endorsed by, sponsored by, or otherwise associated with OpenAI or with any OpenAI initiative, branding, or program that uses the term "Frontier." The Lattix xFrontier name, ideas, and product direction were developed independently by Lattix.

## License

This repository is licensed under **AGPL-3.0-or-later**.

- You may use, modify, and redistribute the software under the terms of the AGPL.
- If you run a modified version for users over a network, you must make the corresponding source available to those users.
- AGPL does **not** prohibit commercial use; it requires reciprocity and source availability for covered modifications.

See `LICENSE` for the full text.

## Repository layout

The FOSS-ready layout is now organized around first-class app, package, deploy, and example directories:

- `apps/frontend/` — Next.js builder and operator UI
- `apps/backend/` — FastAPI orchestration/backend service
- `apps/workers/` — worker and runtime helpers
- `packages/contracts/` — public schemas and contracts
- `packages/data/` — public data and seed assets
- `lattix_frontier/` — root orchestration/control-plane package
- `deploy/infra/` — public-safe infrastructure references
- `deploy/gitops/` — public-safe GitOps references
- `examples/agents/` — public demo agent assets used by default in local-first development
- `docs/reference/lattix-frontier-docs/` — imported legacy documentation tree for migration/reference

Legacy `lattix-frontier-*` directories are retained temporarily as compatibility mirrors while the repository completes its transition away from submodule-shaped paths.

## Architecture

Lattix xFrontier is built around four layers:

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

By default, local-first development seeds safe public demo agents from `examples/agents/`. Optional private or proprietary agent definitions can be layered in by setting `FRONTIER_AGENT_ASSETS_ROOT` to an external directory.

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

The public repository currently exposes:

- `lattix_frontier/` — root orchestration, agents, security, guardrails, events, API, observability
- `apps/` — public application surfaces
- `packages/` — public reusable contracts and data assets
- `deploy/` — public-safe deployment references
- `examples/` — public sample assets for demos and onboarding
- `docker-compose.yml` / `docker-compose.local.yml` — local-first stack definitions
- `helm/lattix-frontier/` — Kubernetes deployment chart
- `policies/` — baseline OPA policies and tests
- `tests/` — unit, integration, and e2e tests for the root platform

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
- `docs/FOSS_RELEASE.md`

## Notes

The public repository intentionally excludes proprietary Lattix agent definitions. The old `lattix-frontier-agents` subrepo remains private; AGPL applies to the public code in this repository, while open-source development should rely on `examples/agents/` or an explicit external `FRONTIER_AGENT_ASSETS_ROOT`.

