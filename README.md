# Lattix Frontier Monorepo

Centralized monorepo for all AI agents and their configurations.

This repo organizes each agent under `AGENTS/` with:
- `url-manifest-*.json` — reference links and knowledge sources
- `system-prompt.md` — agent’s system prompt (to be added)
- `agent.config.json` — agent metadata and defaults (to be added)

Getting started
- Review `AGENTS/AGENTS.md` for conventions and folder layout.
- See `TEMPLATES/` for schemas and examples.
- Optional: generate the registry via `python3 scripts/build_registry.py`.

Docs
- Architecture: see `docs/Lattix Frontier - Architecture.docx`.
- Monorepo scaffolding notes: `docs/ARCHITECTURE.md`.
- Security: `docs/SECURITY.md` (A2A & MCP)

Modeling Business Workflows (Hybrid: Orchestrate + Choreograph)
- Choose a workflow domain and topic
  - Examples: `gtm.content` (GTM content), `security.compliance` (SSP/SAR), `people.personnel` (personnel actions), `legal.contract` (contract review), `ops.project` (project initiation), `sales.pipeline` (new sales process)
- Define stages for Layer 1 (orchestration)
  - Use `runtime/layer1/orchestrator.py` to emit an Envelope with budgets and context
  - Keep L1 focused on phase control, budgets, and handoffs; avoid business logic
- Define agents/services for Layer 2 (choreography)
  - Subscribe to a topic via `runtime/layer2/event_bus.py` and react to Envelopes
  - Implement domain logic; produce artifacts on the Envelope payload; ensure idempotency
- Contracts and guardrails
  - Use `TEMPLATES/envelope.schema.json` and `runtime/layer2/contracts.py` for the message shape
  - Guardrails: respect time/token budgets; avoid tight coupling; prefer message contracts over direct calls
  - Traceability: propagate `correlation_id`; add tags and errors as needed
- Registry-driven selection
  - Use `runtime/layer2/registry.py` to discover agents by `id` or `tags` from `AGENTS/REGISTRY/agents.registry.json`
  - Example: choose `gtm` or `security` tagged agents to participate dynamically

Examples
- Demo subscribers: `runtime/examples/demo_subscribers.py`
- Run a demo workflow:
  - `python3 runtime/run_demo.py gtm` — brand/marketing/blog react to `gtm.content`
  - `python3 runtime/run_demo.py security` — compliance mapper/ssp/sar react to `security.compliance`

Guardrails for Agent Choreography
- Idempotent handlers: safe to receive duplicate envelopes
- Schema discipline: validate/produce well-formed `payload` with clear keys
- Budgets: honor `time_limit_ms` and token limits when calling models/tools
- Separation of concerns: L1 orchestrates phases; L2 agents do domain work; avoid cross-calling bypassing the bus

Deploying Agents as Microservices (L3)
- Scaffold a service for an agent: `python3 scripts/scaffold_agent_service.py <agent-id>` (outputs under `services/<agent-id>/`).
- Each service exposes `/v1/envelope` to accept Envelopes via HTTP and validates A2A JWTs.
- Container build: `docker build -t <agent-id>:dev services/<agent-id>`.
- Kubernetes templates: see `services/AGENT_SERVICE_TEMPLATE/k8s/*.yaml` and adjust names/images.
- A2A security: set `A2A_JWT_*` env vars; see `runtime/security/jwt.py` and `runtime/network/a2a.py`.
- MCP: use the same auth patterns (JWT/mTLS) via a gateway when connecting tools or other services.
