# Architecture

Lattix xFrontier is organized into four layers: orchestration, guardrails, agent execution, and infrastructure.

- `lattix_frontier/orchestrator/` manages workflow state and execution.
- `lattix_frontier/guardrails/` enforces policy, DLP, capability, and budget checks.
- `lattix_frontier/agents/` provides built-in agents and A2A interfaces.
- `docker-compose.yml`, `helm/`, `envoy/`, and `policies/` define runtime infrastructure and controls.

This repository currently ships a minimal working foundation with extensibility points and TODO markers for the more advanced production integrations.

The distribution path now includes:

- a public bootstrap installer flow
- a local `*.localhost` gateway for developer-friendly access
- Helm values for enterprise ingress and federation metadata
