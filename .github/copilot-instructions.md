# GitHub Copilot Instructions — Lattix xFrontier

This repository participates in the Nexus Obsidian-backed AI memory system. Use the committed, repo-safe context; do not assume access to the private vault from cloud/IDE contexts.

## Use these committed files
- `.ai-memory/repo-profile.md` — repo purpose, build/test commands, architecture, conventions
- `.ai-memory/memory-map.md` — abstract pointers into the vault
- `AGENTS.md` — full agent guidance

## Build / test
- `make test`, `make lint`, `make typecheck`, `make policy-test`
- Frontend: `npm run test`, `npm run lint`, `npm run build` (in `apps/frontend/`)

## Proposing memory
When a durable rule/decision should be remembered, include this block in your response (the local `memory-curate` skill promotes it into the vault):

```memory-update
type:
scope: repo
project: lattix
repo: lattix-xfrontier
confidence:
status: candidate
memory:
evidence:
operational_impact:
```

## Security
Never store or commit credentials, tokens, private keys, or customer/regulated data. Record only that a secret exists and where it is retrieved through approved secret management.
