# Architecture

Lattix xFrontier now uses the canonical repository shape described in `THREAT-MODEL.md`: `apps/backend/` is the control-plane surface, `apps/workers/` is the worker/runtime surface, and the old `lattix_frontier/` package has already been removed from the working tree.

## Current state

The repository is organized around four layers: orchestration, guardrails, agent execution, and infrastructure.

- `apps/backend/` manages workflow state, execution control, publication, rollback, and authenticated operator-facing APIs.
- `apps/workers/` provides worker runtime helpers, A2A transport, service templates, and sandbox-facing execution boundaries.
- `frontier_runtime/` and `frontier_tooling/` hold shared runtime and CLI/installer primitives.
- `docker-compose.yml`, `docker-compose.local.yml`, `helm/`, `envoy/`, and `policies/` define runtime infrastructure and controls.

## Historical migration note

Some docs still refer to migration history from the removed `lattix_frontier/` package. Treat that material as historical context, not as evidence of a second live backend.

## Target state

The target architecture is:

- `apps/backend/` as the only canonical backend/control-plane surface
- `apps/workers/` as the worker/runtime surface
- shared primitives extracted into `frontier_runtime/` / `frontier_tooling/` or deleted if no longer needed

That means new backend/control-plane features should land in `apps/backend/` or `apps/workers/`, and future cleanup should remove stale legacy assumptions from docs, tooling, and release guidance rather than reviving a deleted package.

The distribution path now includes:

- a public bootstrap installer flow
- a local `*.localhost` gateway for developer-friendly access
- Helm values for enterprise ingress and federation metadata
