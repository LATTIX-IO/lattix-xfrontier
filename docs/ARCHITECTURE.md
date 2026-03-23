# Architecture

Lattix xFrontier currently contains a transitional dual-surface architecture while the repository converges on the target state documented in `THREAT-MODEL.md`.

## Current state

The repository is still organized around four layers: orchestration, guardrails, agent execution, and infrastructure.

- `lattix_frontier/orchestrator/` manages workflow state and execution.
- `lattix_frontier/guardrails/` enforces policy, DLP, capability, and budget checks.
- `lattix_frontier/agents/` provides built-in agents and A2A interfaces.
- `docker-compose.yml`, `helm/`, `envoy/`, and `policies/` define runtime infrastructure and controls.

## Target state

The target architecture is:

- `apps/backend/` as the only canonical backend/control-plane surface
- `apps/workers/` as the worker/runtime surface
- `lattix_frontier/` reduced to migrated, extracted, or deleted primitives rather than an active parallel backend

That means new backend/control-plane features should land in `apps/backend/` or `apps/workers/`, and reusable logic from `lattix_frontier/` should only move forward by migration or extraction.

This repository currently ships a minimal working foundation with extensibility points and TODO markers for the more advanced production integrations.

The distribution path now includes:

- a public bootstrap installer flow
- a local `*.localhost` gateway for developer-friendly access
- Helm values for enterprise ingress and federation metadata
