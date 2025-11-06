Hybrid runtime scaffolding

Layers
- Layer 2 (L2): contracts, event bus, policy, registry, and skills adapters.
- Layer 1 (L1): orchestrator shell that coordinates phases, then delegates to L2 choreographed flows.

Quick start
- Envelope and bus live under `runtime/layer2/`.
- Orchestrator skeleton is under `runtime/layer1/` with two workflow stubs.
- Run a JSON workflow spec via `python3 runtime/run_spec.py TEMPLATES/workflow.example.json`.
- Dynamic registration from registry:
  - `python3 runtime/run_dynamic.py gtm.content` (optionally `--include-tags gtm,brand`)
 - Remote dispatch to services: `python3 runtime/run_remote.py gtm.content` (configure endpoints in `runtime/network/topic_endpoints.example.json`).

Notes
- Python-only, designed to integrate LangChain (for L1 orchestration) and Semantic Kernel (skills) later.
- No external deps required for the scaffolding; adapters are placeholders.

Topic Conventions
- Use dot-separated topics for business domains and sub-domains (e.g., `people.personnel`, `legal.contract`).
- Keep handler logic idempotent; a handler should be safe to invoke twice.
- Produce artifacts under clear payload keys (e.g., `actions`, `blog_post`, `ssp`, `sar`).

Middlewares
- The EventBus supports pre-delivery middlewares. Default: envelope validation.
- File: `runtime/layer2/middleware.py` (attach via `attach_default_middlewares`).

Dynamic L3 Registration
- File: `runtime/layer2/auto_register.py` uses `AGENTS/REGISTRY/agents.registry.json` and `runtime/layer2/topic_map.json` to subscribe agents by tags to topics.
- Replace placeholder handlers with real agent skills/tools as Layer 3 matures.

Reporting Helpers
- `runtime/layer2/reporting.py` exposes `add_tokens` and `add_log` for subscribers to update budgets/telemetry.

Layer 3 (Agents) Runtime
- Per-agent runtime config (optional): `AGENTS/<agent>/agent.runtime.json`
  - Keys: `topics` (list of topic strings), `module` (import path), `function` (callable name; default `handle`).
  - Template: `TEMPLATES/agent.runtime.example.json`.
- Handler template: `TEMPLATES/AGENT_RUNTIME_HANDLER_TEMPLATE.py` — implement `handle(env: Envelope)`.
- Run with L3 handlers:
  - `python3 runtime/run_l3.py gtm.content` (auto-loads agents with agent.runtime.json)
  - Limit to specific agents: `--agents developer-agent,marketing-agent`

Workflow Specs
- Define workflows as JSON with ordered stages: name, topic, payload, budget_ms, expected_keys.
- Templates: `TEMPLATES/workflow.example.json`.
- Examples: `runtime/layer1/workflows/specs/*.json`.

Transports (Local vs Remote)
- Local: default; orchestrator publishes to the in-process EventBus; used for development or co-located agents.
- Remote: pass `dispatch_mode="remote"` (or use `runtime/run_remote.py`) to POST Envelopes to containerized agent services.
- Configure endpoints per topic in `runtime/network/topic_endpoints.example.json`.

Termination Conditions
- The orchestrator currently emits and returns immediately. In real workflows, wait for a termination condition:
  - Presence of expected artifact keys in payload
  - A status field reaching a terminal value
  - Elapsing a budget/timebox
