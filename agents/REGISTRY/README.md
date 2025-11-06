# Agents Registry

This directory stores a generated registry of all agents:

- `agents.registry.json` — machine-readable catalog produced by `scripts/build-registry.js`.

Generation
- Run: `python3 scripts/build_registry.py`
- The script scans `AGENTS/*/` for `agent.config.json` or `url-manifest-*.json` and builds entries.

Notes
- Prefer maintaining `agent.config.json` per agent; the script will enrich entries from it when present.
- The registry is safe to regenerate; do not hand-edit.
