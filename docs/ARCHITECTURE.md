# Architecture Notes

Primary reference: `docs/Lattix Frontier - Architecture.docx`.

This monorepo scaffolding aligns to the following principles:
- Single source of truth for agent configs and prompts
- Explicit, versioned schemas for manifests and agent configs
- Generated registry for orchestration and discovery

Key directories
- `AGENTS/` — all agents, one folder per agent
- `AGENTS/REGISTRY/` — generated agent catalog
- `TEMPLATES/` — schemas and authoring templates
- `scripts/` — automation utilities (e.g., registry builder)
- `runtime/` — hybrid runtime scaffolding (L1 orchestrator + L2 contracts/bus/policy)

Future enhancements (optional)
- CI to validate JSON against schemas
- Prompt QA harness for regression testing
- Model/provider profiles and environment overrides
 - Integrate LangChain (L1 orchestration) and Semantic Kernel (L2 skills)
