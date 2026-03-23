# Security

See `THREAT-MODEL.md` for the canonical current-state vs target-state security expectations, trust boundaries, deployment-mode assumptions, the historical migration record for the removed `lattix_frontier/` package, and known failure modes.

## Capability tokens

The current implementation mints signed capability envelopes, supports attenuation, and verifies scope and expiry before agent execution.

Lifecycle:

1. Orchestrator mints a token.
2. Token is attached to an envelope.
3. Guardrails verify scope and expiry.
4. Agent server requires a token on `/v1/envelope`.

## OPA policies

Policies live in `policies/` and are tested through `policies/tests/`.

## Vault

Local development uses a dev token. Kubernetes is designed to migrate to Kubernetes auth and per-service-account roles.

## DLP pipeline

Tier 1 uses regex and lightweight classification now. The code includes TODO markers for deeper Presidio and GLiNER integration.

## Network isolation

Envoy is the intended egress boundary. Helm templates include a strict default-deny baseline with explicit allow rules.

For local tool execution, the sandbox subsystem now uses a dedicated internal Docker network and a dual-homed `sandbox-egress-gateway` service so jailed containers do not get direct outbound internet access.

## Audit integrity

Every recorded event can be chained through SHA-256 and verified with `scripts/verify_event_chain.py` against the repo's configured event-chain artifact.

## Human gates

Confidential and restricted workflows can require human approval before completion.

## Tool jail

All new secure tool execution should go through the worker/runtime sandbox boundary in `apps/workers/`, with egress mediation enforced by the secure Compose topology and platform policies described in `THREAT-MODEL.md`.
