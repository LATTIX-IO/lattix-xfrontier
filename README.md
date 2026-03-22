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

Local memory is split by tier:

- **Redis** handles short-term, hot working memory and session caching.
- **PostgreSQL + pgvector** handles long-term persistent memory and semantic recall.
- **Consolidation scaffolding** queues durable memory candidates when `FRONTIER_MEMORY_CONSOLIDATION_ENABLED=true`, so selective promotion/summarization can be layered in without exposing internals in the builder.
- **Hybrid retrieval** can blend short-term session memory, long-term semantic memory, and internal world-graph context when `FRONTIER_MEMORY_HYBRID_RETRIEVAL_ENABLED=true`, with hidden relevance ranking, role-aware boosts, and a bounded token budget.
- Task outcomes can be promoted into long-term memory automatically when `FRONTIER_MEMORY_LEARNING_ENABLED=true`, allowing agents to build reusable organizational memory over time.

For internal operations and testing, queued consolidation candidates can be processed through the backend-only endpoint `POST /internal/memory/consolidation/run`. This is intended for platform workflows and operators, not the standard ReactFlow builder experience.
Consolidated memory summaries can also be projected into the internal Neo4j world graph through `POST /internal/memory/world-graph/project`, or automatically during consolidation when graph projection is enabled.

Useful consolidation tuning flags:

- `FRONTIER_MEMORY_CONSOLIDATION_MIN_CANDIDATES` — minimum candidate count before standard memory gets summarized.
- `FRONTIER_MEMORY_TASK_LEARNING_MIN_CANDIDATES` — lower threshold for task-learning consolidation.
- `FRONTIER_MEMORY_CONSOLIDATION_MAX_POINTS` — maximum bullet points retained in a synthesized summary.
- `FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP` — token-overlap threshold used to suppress near-duplicate summaries.
- `FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_HISTORY_LIMIT` — how many recent summaries are checked when looking for duplicates.
- `FRONTIER_MEMORY_HYBRID_RETRIEVAL_ENABLED` — blends short-term, long-term, and world-graph context into hidden agent memory retrieval.
- `FRONTIER_MEMORY_HYBRID_MAX_TOKENS` — caps the approximate token budget for ranked hybrid memory injected into agent execution.
- `FRONTIER_MEMORY_HYBRID_MAX_TOPICS` — caps how many world-graph topics are surfaced alongside ranked hybrid memory.
- `FRONTIER_MEMORY_GRAPH_PROJECTION_ENABLED` — enables internal Neo4j projection for consolidated memory summaries.
- `FRONTIER_MEMORY_GRAPH_MAX_TOPICS` — maximum number of extracted topic nodes linked from each consolidated memory.
- `FRONTIER_MEMORY_GRAPH_TOPIC_MIN_OCCURRENCES` — minimum repeated occurrences before a topic is projected into the world graph.

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

The public repository intentionally excludes proprietary Lattix agent definitions. Private agent assets are no longer expected inside this repository; open-source development should rely on `examples/agents/` or an explicit external `FRONTIER_AGENT_ASSETS_ROOT`.

