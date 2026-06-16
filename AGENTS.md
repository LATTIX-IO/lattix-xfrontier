# AGENTS.md — Lattix xFrontier

Guidance for AI coding agents (Codex, Claude Code, Copilot, Cowork) working in this repo. More specific files closer to the working directory take precedence.

## What this repo is
Lattix xFrontier — a secure, local-first multi-agent orchestration platform (AGPL-3.0-or-later). Four layers: LangGraph orchestration → Microsoft Agent Framework guardrails → MAF ChatAgents + A2A execution → infra (Vault, OPA, Envoy, NATS, Biscuit, Presidio). Backend `apps/backend/`, workers `apps/workers/`, frontend `apps/frontend/`, runtime `frontier_runtime/`, contracts `packages/contracts/`.

## Build / test / quality (run before handoff)
- `make test` — all tests
- `make lint` — lint + format
- `make typecheck` — type check
- `make policy-test` — OPA policy tests (when policy files change)
- `make local-up` / `make local-down` — lightweight local-first stack
- `make stack-up` / `make stack-down` — full platform stack
- `make bootstrap` — first-time setup · `make health` — API health
- Frontend (`apps/frontend/`): `npm run test` (vitest), `npm run lint`, `npm run build`
- Python 3.12+, hatchling. Issues tracked in Linear (`FRONT-*`).

## AI Memory System (Nexus)
This repo participates in the **Nexus Obsidian-backed memory system**. Durable, cross-tool memory lives in an external Obsidian vault (`50-Memory/`), not in this repo.

**Read first (committed, repo-safe):**
- `.ai-memory/repo-profile.md` — this repo's canonical profile
- `.ai-memory/memory-map.md` — pointers into the vault
- Global/identity memory + the vault path are in a **gitignored local** file (`CLAUDE.local.md` / `.ai-memory/local/`). If absent, you are in a clean/CI checkout — use only the committed context above.

**Write policy:**
- Do **not** edit canonical vault memory during normal work.
- To propose a durable memory (new repo rule, decision, pattern), append a `memory-candidate` block to the vault's `50-Memory/Inbox/<source>-inbox.md` if you have local filesystem access to the vault; otherwise emit the block in your response for the `memory-curate` skill to promote. Schema:

```memory-candidate
mem_type: repo_rule        # preference|fact|decision|pattern|repo_rule|project_state
scope: repo
project: lattix
repo: lattix-xfrontier
source: codex|claude|copilot
confidence: high|medium|low
status: candidate
memory: <durable statement>
evidence: <where it came from>
operational_impact: <what changes>
update_rule: <stale vs supersede>
```

**Security (hard limit):** never store credentials, tokens, private keys, customer/regulated data in memory or in committed files. Record only that a secret exists and where it is retrieved via approved secret management.

## Done criteria
1. Run the relevant `make` target(s) above; tests/lint/typecheck green.
2. Record durable new repo rules/decisions as `memory-candidate` blocks.
3. Mark uncertain/time-sensitive info `confidence: low`, and cite any memory id you relied on.
