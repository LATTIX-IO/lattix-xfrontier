# Contributing to Lattix xFrontier

Thanks for helping improve Lattix xFrontier.

By contributing to this repository, you agree that your contributions are submitted under the repository's **AGPL-3.0-or-later** license unless explicitly stated otherwise in writing by the project maintainers.

## Ground rules

- Keep changes small, reviewable, and well-tested.
- Do not commit secrets, customer data, or proprietary prompt content.
- Public contributions must target the FOSS tree only.
- Private Lattix agent assets belong outside this repository.

## Local development

### Root platform

- `make bootstrap`
- `make dev`
- `make test`
- `make policy-test`

### Frontend

Work from `apps/frontend/`:

- `npm ci`
- `npm run lint`
- `npm run build`
- `npm test`

### Backend

Work from `apps/backend/` for the legacy FastAPI backend service.

## Public vs private assets

This repository ships public demo assets under `examples/agents/`.

If you need proprietary or internal agent definitions for local testing, point `FRONTIER_AGENT_ASSETS_ROOT` at an external directory instead of adding those assets to git.

## Pull requests

Please include:

- problem statement
- implementation summary
- test evidence
- rollout or compatibility notes

## Reporting security issues

Please do **not** open public issues for vulnerabilities. Follow the process in `SECURITY.md`.
