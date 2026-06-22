# Lattix xFrontier

Lattix xFrontier is a secure, local-first multi-agent orchestration platform licensed under the GNU Affero General Public License v3.0-or-later (AGPLv3+). It pairs a **zero trust security core** with a **cortical-column ("Thousand Brains") cognitive model** so that agentic work is both contained by default and reasoned about by many independent models rather than a single prompt loop.

This README leads with the methodology, then a quick start (Kubernetes + desktop install on macOS, Windows, and Linux), and only then dives into the architecture and implementation.

> Lattix xFrontier is an independent project created by Lattix. It is not affiliated with, endorsed by, sponsored by, or otherwise associated with OpenAI or with any OpenAI initiative, branding, or program that uses the term "Frontier." The Lattix xFrontier name, ideas, and product direction were developed independently by Lattix.

---

## Methodology

xFrontier is built on two convictions: that an agent platform must **trust nothing implicitly**, and that reliable machine reasoning comes from **many independent models reaching consensus**, not from one large context window.

### Zero trust core

Zero trust in xFrontier is not a slogan layered on at the edge — it is a design style that recurs at every major boundary. Identity, scope, or capability is checked *before* work proceeds, and the default posture is fail-closed.

- **Route-level access classification.** Every backend route is assigned one of `public-minimal`, `authenticated-read`, `authenticated-mutate`, or `internal-only`, and the inventory is validated at startup so no endpoint can appear without an access class.
- **Authenticated operator sessions.** Protected UI does not render its data surfaces until an operator session is resolved and authenticated. Secure-local installs default to OIDC-backed auth and disable unsigned header-only actor trust.
- **Signed agent-to-agent transport.** Cross-service traffic carries bearer JWTs, signed runtime headers, subject identity, and nonce-based replay protection instead of relying on local-network trust. HTTPS is required in the `hosted` profile.
- **Scope-checked memory.** Memory is partitioned by scope (`run`, `session`, `user`, `tenant`, `agent`, `workflow`, `global`). The scope label is never trusted by itself; the backend normalizes it, validates the bucket prefix, and authorizes by actor identity, tenant claim, or collaboration membership.
- **Deny-by-default isolation.** Tool execution runs through a sandbox with explicit allowlists for executables, read/write paths, network, and destination hosts. Sensitive subpaths (`.git`, `.ssh`, `.gnupg`, `.aws`, `.azure`, `.kube`) are re-protected even inside a writable parent.
- **Middleware-enforced tenant consistency.** The event bus only delivers envelopes that survive middleware checks; a message can be dropped before any agent handler sees it if the runtime context is inconsistent with policy.

See [`THREAT-MODEL.md`](THREAT-MODEL.md) for the canonical trust-boundary reference.

### Cortical column ("Thousand Brains") cognitive model

xFrontier's reasoning model is inspired by the **Thousand Brains theory of intelligence**: intelligence emerges from many cortical columns, each building its own model of the world from its own evidence, voting toward a shared conclusion. Translated into the platform, this means agents become *coordination shells* and the actual reasoning is distributed across **cognitive columns** that are fused by **explicit consensus**.

- **Columns** are independent reasoning units. Each maintains its own belief state, evidence references, and confidence — and the platform deliberately keeps them independent so failures are not correlated.
- **Assemblies** are task-specific coalitions of columns with a defined inference mode, consensus policy, and stopping condition.
- **Consensus** fuses column beliefs with weighted support, tracks dissent, and emits a **commitment**: a decision plus confidence, supporting/dissenting columns, blockers, and next actions.

The target state is a distributed cognitive system that maintains multiple independent models of a task, reasons over state, evidence, prediction, and evaluation, and adapts over time under bounded, inspectable cognition — *not* a better prompt-orchestration tool. See [`docs/COLOUMN_LAYER_IMPLEMENTATION_PLAN.md`](docs/COLOUMN_LAYER_IMPLEMENTATION_PLAN.md) for the full target spec.

**What ships today** is an additive, bounded **cognitive MVP** — the first slice of that columnar architecture. It adds four graph-native node types without replacing the existing agent runtime:

- `frontier/goal` — explicit goal framing
- `frontier/evidence` — evidence capture and missing-evidence detection
- `frontier/assembly` — bounded weighted-support assembly fusion
- `frontier/commitment` — commitment generation with confidence, blockers, dissent, and next actions

Legacy graphs continue to validate and run, and `frontier/agent` semantics are unchanged. Advanced columns (Evaluation, Uncertainty, State, Decomposition, Prediction, Adaptation) are planned but not yet part of the shipped slice.

---

## Quick start

Pick the path that matches how you want to run xFrontier. All three converge on the same control plane and secure defaults.

### A. Kubernetes (Helm)

The Helm chart is pinned to the `hosted` runtime profile and deploys the control-plane workloads (`lattix-api`, `lattix-orchestrator`, `lattix-envoy`, `lattix-opa`, `lattix-vault`, `lattix-nats`, `lattix-postgres`, `lattix-jaeger`).

```bash
# Replace the placeholder A2A_JWT_SECRET in the values file before applying.
helm install lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml
```

The chart wires `A2A_JWT_SECRET` into the API/orchestrator paths so hosted clusters enforce the same signed runtime-header contract as the backend profile tests. `values-dev.yaml` is available for non-production clusters.

### B. Desktop app (macOS · Windows · Linux)

The Tauri desktop shell is a thin, auditable wrapper that spawns a single packaged backend supervisor, which brings up every local service (Postgres + pgvector, Neo4j world models, NATS, Ollama, the confined agents, the FastAPI backend, and the Next.js frontend) — **with no Docker** — then opens a webview once `/healthz` is green.

Download the signed installer for your OS from the project releases and run it:

| OS | Installer |
| --- | --- |
| **Windows** | `.msi` or `.exe` (NSIS) — Authenticode-signed |
| **macOS** | `.dmg` / `.app` — Developer ID signed + notarized |
| **Linux** | `.deb` or `.AppImage` |

First launch performs a one-time fetch of vendored runtime binaries, then drops you into a working multi-agent console. Updates arrive as a one-click **Update & Restart** banner. To build the desktop app from source, see [`apps/desktop-tauri/README.md`](apps/desktop-tauri/README.md).

### C. Local stack (bootstrap installer)

For a full local-first stack on your own machine, run the public bootstrap installer. It pulls vetted `main` content, installs the `lattix` CLI, updates your user `PATH`, and auto-starts the secure stack.

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh
```

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -c "iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 -UseBasicParsing | iex"
```

Then start, open, and check the stack:

```bash
lattix up        # auto-starts the secure full stack
lattix health    # API health check
```

Open `http://xfrontier.local` (or your configured `LOCAL_STACK_HOST`); the installer also prints clickable `http://127.0.0.1` and LAN URLs after `lattix up`. The bootstrap requires a working Python 3 runtime (`py -3` or `python`) on `PATH` — on Windows the Microsoft Store placeholder alias is not sufficient by itself.

Common follow-ups:

```bash
lattix update    # refresh the install without deleting workflows, agents, or settings
lattix remove    # tear down local stacks + installer-managed env (leaves your checkout and .env)
```

`lattix update` keeps `.installer/` env files and Docker data volumes in place, reapplies the package, and restarts the active stack. Re-running the published bootstrap over an existing install follows the same non-destructive posture: it preserves `.installer/` and `.env`, keeps Docker volumes intact, and reuses prior secure-local passwords, bootstrap identities, and OIDC settings as interactive defaults.

> **Profiles.** Set `FRONTIER_RUNTIME_PROFILE` to pin security posture explicitly: `local-secure` (fail-closed local/full-stack) or `hosted` (authenticated operator access + signed A2A headers). For lighter local-only iteration, `make local-up` exposes the frontend at `http://localhost:3000` and the backend at `http://localhost:8000` without the gateway `/api` path. The intended default is the **secure full platform stack** (`make up` / `make stack-up`).

---

## Architecture

xFrontier separates authoring, coordination, execution, memory, and review into explicit layers — it is intentionally *not* a monolith with one undifferentiated memory or agent runtime. The canonical backend surface is `apps/backend/` (control plane) and `apps/workers/` (runtime/worker surface).

### Security + reasoning layers

```text
┌──────────────────────────────────────────────────────────┐
│  LAYER 1: ORCHESTRATION (LangGraph)                       │
│  StateGraph, checkpointing, durable execution             │
├──────────────────────────────────────────────────────────┤
│  LAYER 2: GUARDRAILS (Microsoft Agent Framework filters)  │
│  Prompt render, function invocation, DLP, policy gates    │
├──────────────────────────────────────────────────────────┤
│  LAYER 3: AGENT EXECUTION (MAF ChatAgents + A2A)          │
│  Role-based agents, handoffs, tool invocation via MCP     │
├──────────────────────────────────────────────────────────┤
│  LAYER 4: INFRASTRUCTURE (Docker/K8s + security stack)    │
│  Vault, OPA, Envoy, NATS, Biscuit tokens, Presidio        │
└──────────────────────────────────────────────────────────┘
```

### Cooperating planes

The running system is organized into five cooperating planes:

1. **User interface plane** — the Next.js builder, run console, settings, collaboration, and artifacts (`apps/frontend/`).
2. **Control plane** — the FastAPI backend (`apps/backend/app/main.py`); the canonical API surface owning route classification, auth, definitions, run management, memory APIs, and observability.
3. **Runtime/orchestration plane** — shared runtime primitives (`frontier_runtime/`) and worker runtime (`apps/workers/runtime/`) managing staged execution, approvals, discovery, envelopes, middleware, A2A dispatch, and sandbox planning.
4. **Execution plane** — agents and tools execute through bounded runtime contracts; A2A work flows through envelopes and event topics, with tool execution mediated by the sandbox.
5. **State and memory plane** — short-term, durable, and long-term memory plus consolidation queues and world-graph projection, split across Redis, PostgreSQL/pgvector, Neo4j, and local persisted state.

For the full narrative — control plane, memory tiers, isolation strategies, the multi-agent ecosystem, and the frontend connection pattern — see [`docs/SYSTEM-ARCHITECTURE.md`](docs/SYSTEM-ARCHITECTURE.md).

---

## Implementation

### Memory system

Memory is tiered, scoped, and selectively promotable:

- **Redis** handles short-term, hot working memory and session caching.
- **PostgreSQL + pgvector** handles long-term persistent memory and semantic recall.
- **Consolidation scaffolding** queues durable memory candidates when `FRONTIER_MEMORY_CONSOLIDATION_ENABLED=true`.
- **Hybrid retrieval** blends short-term session memory, long-term semantic memory, and world-graph context when `FRONTIER_MEMORY_HYBRID_RETRIEVAL_ENABLED=true`, with hidden relevance ranking, role-aware boosts, and a bounded token budget.
- **Task learning** promotes task outcomes into long-term memory when `FRONTIER_MEMORY_LEARNING_ENABLED=true`.

Internal operators can process queued consolidation candidates via `POST /internal/memory/consolidation/run` and project consolidated summaries into the Neo4j world graph via `POST /internal/memory/world-graph/project`. Useful tuning flags:

- `FRONTIER_MEMORY_CONSOLIDATION_MIN_CANDIDATES` — minimum candidates before standard memory is summarized.
- `FRONTIER_MEMORY_TASK_LEARNING_MIN_CANDIDATES` — lower threshold for task-learning consolidation.
- `FRONTIER_MEMORY_CONSOLIDATION_MAX_POINTS` — maximum bullet points retained in a synthesized summary.
- `FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_MIN_OVERLAP` — token-overlap threshold to suppress near-duplicate summaries.
- `FRONTIER_MEMORY_CONSOLIDATION_DUPLICATE_HISTORY_LIMIT` — how many recent summaries are checked for duplicates.
- `FRONTIER_MEMORY_HYBRID_MAX_TOKENS` — caps the token budget for ranked hybrid memory injected into execution.
- `FRONTIER_MEMORY_HYBRID_MAX_TOPICS` — caps world-graph topics surfaced alongside ranked hybrid memory.
- `FRONTIER_MEMORY_GRAPH_PROJECTION_ENABLED` — enables internal Neo4j projection for consolidated summaries.
- `FRONTIER_MEMORY_GRAPH_MAX_TOPICS` — maximum topic nodes linked from each consolidated memory.
- `FRONTIER_MEMORY_GRAPH_TOPIC_MIN_OCCURRENCES` — minimum repeated occurrences before a topic is projected.

### Execution isolation

`SandboxManager` (`frontier_runtime/sandbox.py`) selects the strongest available isolation backend and materializes it from a single declarative policy, so the rest of the runtime never needs to know which backend is in use:

1. **Kernel sandbox** on Linux/macOS via `bubblewrap` or `sandbox-exec`.
2. **Hardened Docker** — read-only root, dropped capabilities, seccomp, resource caps, explicit mounts, optional network disablement.
3. **Kubernetes runtime isolation** — pod metadata for gVisor or Kata runtime classes in hosted deployments.

### Repository layout

- `frontier_tooling/` — canonical repo CLI and installer entrypoints
- `frontier_runtime/` — shared runtime/security/config primitives used by backend and worker surfaces
- `apps/frontend/` — Next.js builder and operator UI
- `apps/backend/` — FastAPI orchestration/control-plane service
- `apps/workers/` — worker and runtime helpers
- `apps/desktop-tauri/` — Tauri v2 desktop shell
- `packages/contracts/` — public schemas and contracts
- `packages/data/` — public data and seed assets
- `deploy/infra/`, `deploy/gitops/` — public-safe deployment references
- `examples/agents/` — public demo agent assets used by default in local-first development
- `docker-compose.yml` / `docker-compose.local.yml` — local-first stack definitions
- `helm/lattix-frontier/` — Kubernetes deployment chart
- `policies/` — baseline OPA policies and tests
- `docs/reference/lattix-frontier-docs/` — imported legacy documentation tree

By default, local-first development seeds safe public demo agents from `examples/agents/`. Layer in private agent definitions by setting `FRONTIER_AGENT_ASSETS_ROOT` to an external directory.

### CLI

After installation, the `lattix` command supports:

```text
lattix up | down | update | remove
lattix local-up | local-down
lattix health
lattix agent list | agent scaffold --name <agent-name>
lattix workflow list | workflow run <workflow-name> --task "..."
lattix policy test | policy lint
lattix sandbox backend
lattix install run | install bootstrap-url
lattix demo <domain>
```

### Testing

```text
make lint
make typecheck
make policy-test
make helm-validate
make test
```

Windows PowerShell equivalents use `.\scripts\frontier.ps1 <target>` (e.g. `.\scripts\frontier.ps1 test`). Policy tests use a repo-local OPA binary at `.tools/opa/opa(.exe)` when present, otherwise `opa` on `PATH`; install the pinned binary on Windows with `.\scripts\frontier.ps1 install-opa`.

Focused validation for the cognitive MVP:

```text
.venv/Scripts/python.exe -m pytest apps/backend/tests/test_cognitive_graph.py tests/unit/test_cognitive_runtime.py tests/e2e/test_full_pipeline.py -q

cd apps/frontend
npm test -- --run src/lib/frontier-node-schema.spec.ts src/components/run-conversation-console.spec.tsx
```

### License

This repository is licensed under **AGPL-3.0-or-later**.

- You may use, modify, and redistribute the software under the terms of the AGPL.
- If you run a modified version for users over a network, you must make the corresponding source available to those users.
- AGPL does **not** prohibit commercial use; it requires reciprocity and source availability for covered modifications.

See [`LICENSE`](LICENSE) for the full text. The public repository intentionally excludes proprietary Lattix agent definitions; open-source development should rely on `examples/agents/` or an explicit external `FRONTIER_AGENT_ASSETS_ROOT`.

### Documentation

- [`THREAT-MODEL.md`](THREAT-MODEL.md)
- [`docs/SYSTEM-ARCHITECTURE.md`](docs/SYSTEM-ARCHITECTURE.md)
- [`docs/COLOUMN_LAYER_IMPLEMENTATION_PLAN.md`](docs/COLOUMN_LAYER_IMPLEMENTATION_PLAN.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/AGENT_DEVELOPMENT.md`](docs/AGENT_DEVELOPMENT.md)
- [`docs/API.md`](docs/API.md)
- [`docs/SANDBOXING.md`](docs/SANDBOXING.md)
- [`docs/INSTALLER.md`](docs/INSTALLER.md)
- [`docs/FOSS_RELEASE.md`](docs/FOSS_RELEASE.md)
