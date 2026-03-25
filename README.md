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
- `deploy/infra/` — public-safe infrastructure references
- `deploy/gitops/` — public-safe GitOps references
- `examples/agents/` — public demo agent assets used by default in local-first development
- `docs/reference/lattix-frontier-docs/` — imported legacy documentation tree for migration/reference

## Architecture

The target-state architecture is now centered on `apps/backend/` as the only canonical backend/control-plane surface and `apps/workers/` as the runtime/worker surface. The old `lattix_frontier/` package is no longer present in the working tree; remaining cleanup is about removing stale legacy assumptions and keeping docs/tooling aligned with the canonical surfaces.

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

1. Run the public bootstrap installer.
2. Follow the prompts for local auth, secrets, and hostname.
3. If you skip auto-launch, start the secure default stack with `lattix up`.

```text
curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh
```

On Windows PowerShell, use either the installed CLI or the PowerShell helper:

```text
powershell -ExecutionPolicy Bypass -c "iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 -UseBasicParsing | iex"

lattix up
.\scripts\frontier.ps1 up
```

For source-checkout testing, you can still run `pwsh -File .\install\bootstrap.ps1` on Windows or `sh ./install/bootstrap.sh` on POSIX shells.

To remove the local install during testing and start fresh, use:

```text
lattix remove
make remove
.\scripts\frontier.ps1 remove
```

That tears down the local Docker stacks, removes named volumes and networks for those stacks, and deletes installer-managed env files under `.installer/`. It intentionally leaves your repository checkout and `.env` in place.

For the default secure/full browser experience, open `http://frontier.localhost` (or your configured `LOCAL_STACK_HOST`). That path proxies `/api/*` through the local gateway to the backend at `http://localhost:8000`.

If you intentionally want the lighter local-only stack, use `make local-up`. That path exposes the frontend directly at `http://localhost:3000` and talks to the backend at `http://localhost:8000` without the gateway-based `/api` path.

The intended default is the **secure full platform stack** via `make up` / `make stack-up`. The lighter `docker-compose.local.yml` stack is still available for quicker local-only iteration through `make local-up`.

Supported runtime profiles are now explicit:

- `local-secure` — fail-closed secure local/full-stack profile used by `docker-compose.yml`
- `hosted` — non-local profile that requires authenticated operator access and signed A2A runtime headers

Set `FRONTIER_RUNTIME_PROFILE` when you need to pin the backend/runtime security posture explicitly. Legacy flags like `FRONTIER_SECURE_LOCAL_MODE` and `FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS` still exist for compatibility, but the named profile is the canonical contract.

Secure local installs now default to OIDC-backed operator authentication and disable unsigned header-only actor trust. The installer ships with a Casdoor preset by default, but can also emit generic OIDC settings for another IAM provider when you want to connect Frontier to an external identity plane.
The frontend includes a generic `/auth` portal that points users to the configured provider-hosted sign-in and sign-up URLs, so the same console entry flow works with Casdoor or another OIDC-compliant IAM.
The secure local stack now also routes Casdoor at `http://casdoor.localhost`, and the installer seeds a default bootstrap admin identity (`frontier-admin` / `admin@<hostname>.localhost`) into both the admin and builder actor allowlists so the first authenticated operator lands with the right keys.

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

- `lattix remove`
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

- `frontier_tooling/` — canonical repo CLI and installer entrypoints
- `frontier_runtime/` — shared runtime/security/config primitives used by canonical backend and worker surfaces
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

- `lattix up`
- `lattix down`
- `lattix remove`
- `lattix local-up`
- `lattix local-down`
- `lattix health`
- `lattix agent list`
- `lattix agent scaffold --name <agent-name>`
- `lattix workflow list`
- `lattix workflow run <workflow-name> --task "..."`
- `lattix policy test`
- `lattix policy lint`
- `lattix sandbox backend`
- `lattix install run`
- `lattix install bootstrap-url`
- `lattix demo <domain>`

## Testing

```text
make lint
make typecheck
make policy-test
make helm-validate
make test
```

Windows PowerShell equivalents:

```text
.\scripts\frontier.ps1 lint
.\scripts\frontier.ps1 typecheck
.\scripts\frontier.ps1 policy-test
.\scripts\frontier.ps1 helm-validate
.\scripts\frontier.ps1 test
```

## Deployment

Default local deployment uses the secure full Compose stack in `docker-compose.yml`:

```text
lattix up
```

This path includes the added security-oriented infrastructure such as the local gateway, sandbox egress boundary, policy services, and supporting runtime components.
It also keeps most internal services off the host network by default, generates local database credentials during installer setup, and expects signed internal A2A traffic instead of header-only trust.

`make stack-up` is kept as an explicit alias for the same secure full stack.

To tear down the installed local app and delete installer-managed env files so you can test a clean reinstall, use:

```text
lattix remove
```

Equivalent repo-local helpers remain available:

```text
make remove
.\scripts\frontier.ps1 remove
```

If you want the lighter stack for quick local iteration, use:

```text
make local-up
```

That stack uses `docker-compose.local.yml`, exposes the frontend at `http://localhost:3000`, the backend at `http://localhost:8000`, and uses `FRONTIER_LOCAL_API_BASE_URL` rather than the gateway-based `/api` path.

If you need the heavier full platform stack for gateway/sandbox/policy-infra work, use:

```text
make stack-up
```

Kubernetes deployment uses Helm:

```text
helm install lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml
```

The Helm chart is now pinned to the `hosted` runtime profile by default. It deploys the control-plane workloads shown in the chart (`lattix-api`, `lattix-orchestrator`, `lattix-envoy`, `lattix-opa`, `lattix-vault`, `lattix-nats`, `lattix-postgres`, `lattix-jaeger`) and wires `A2A_JWT_SECRET` into the API/orchestrator paths so hosted clusters require the same signed runtime-header contract as the backend profile tests. Replace the placeholder secret before applying the chart.

## Documentation

- `THREAT-MODEL.md`
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

