# Frontier MVP Frontend

Dual-mode Next.js frontend for local-first orchestration operations and workflow building.

## Modes

- **User Mode** (Ops/day-to-day): inbox, run conversation, artifacts, targets, guardrails.
- **Builder Mode** (Power-user): workflow studio, agent studio, node library, guardrails builder, releases.

## Local development

```bash
npm install
npm run dev
```

App runs on `http://localhost:3000`.

## Backend integration

Set backend API base URL using environment variable:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

If the backend is unavailable, the UI falls back to local mock data so workflows remain explorable in local-first mode.

## API coverage (frontend client)

The client layer (`src/lib/api.ts`) is wired for:

- `GET /workflows/published`
- `POST /workflow-runs`
- `GET /workflow-runs`
- `GET /workflow-runs/{id}`
- `GET /workflow-runs/{id}/events`
- `POST /artifacts/{id}/versions`
- `POST /approvals`
- `GET /inbox`

Builder mode endpoints:

- `GET/POST workflow-definitions` + publish
- `GET/POST agent-definitions` + publish
- `GET node-definitions`
- `GET/POST guardrail-rulesets` + publish
