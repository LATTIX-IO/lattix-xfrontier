# Agents Conventions

Scope: applies to all content under `AGENTS/`.

Folder layout (per agent)
- `agent.config.json` — agent metadata, defaults, pointers
- `system-prompt.md` — agent system prompt in plain Markdown
- `url-manifest-*.json` — curated external references for grounding
- `README.md` — brief purpose, ownership, usage notes

Naming
- Folder names use kebab-case (e.g., `developer-agent`).
- `agent.config.json` is the canonical per-agent config file.
- Keep URL manifests named `url-manifest-<agent>.json`.

System prompts
- Store as Markdown in `system-prompt.md` using ChatGPT-style system prompt format.
- Keep role/voice, scope, guardrails, Do/Don’t lists at top.

Configuration
- Prefer JSON for machine-readability; validate against `TEMPLATES/agent.config.schema.json`.
- Reference the URL manifest via a relative path.

Registry
- The repo-level registry is materialized at `AGENTS/REGISTRY/agents.registry.json`.
- Generate it via `python3 scripts/build_registry.py`.
- Bulk update owners/tags/model defaults via `python3 scripts/bulk_update_agents.py`.

Versioning & status
- Set `status` in `agent.config.json` to `draft`, `active`, or `deprecated`.
- Use semantic `version` for meaningful config changes.

Reviews
- Include `owners` (GitHub handles/emails) in `agent.config.json`.
- Keep `last_verified` in URL manifests up to date.
