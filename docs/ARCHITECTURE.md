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

## Cortical column zero-trust runtime

The cortical assembly runtime is part of the canonical backend/runtime architecture, not a separate trusted control plane. It treats every column, message, runtime step, and graph projection as untrusted until the backend admits it through identity, tenant, capability, policy, replay, and persistence controls.

### Zero-trust column assumptions

- A column is not trusted because it is in the same process, container, Docker network, or cluster namespace.
- Column messages are data-bearing security events. They must carry tenant, assembly, source column, target column, nonce, timestamp, and trusted subject metadata before they can mutate causal state.
- Column kinds are least-privilege roles. Goal columns read input and emit goal beliefs, evidence columns retrieve, evaluation columns score or veto, synthesis columns propose commitments, and uncertainty columns emit blockers. Unknown kinds deny by default.
- Assembly definitions are admitted before execution. Admission bounds columns, iterations, messages, allowed column kinds, required goal/evidence/evaluation/synthesis participation, tenant, provider, model, and tool policy.
- Commitment is a gated outcome, not a direct runtime shortcut. Evidence and evaluation participation, unresolved blockers, confidence thresholds, high-risk human approval, and the audited decision trail are checked before a ready commitment is accepted.
- Causal graph projection is a derived view. Persisted causal state remains the source of truth, projection is tenant-checked and size-bounded, and projection failure must not corrupt persisted state.

### Tenant isolation model

Tenant identity flows through signed runtime bearer claims, authenticated backend request context, and admitted cognitive message metadata. The runtime rejects cross-tenant assembly replay, tenant-mismatched cognitive messages, and causal graph projection requests made with the wrong tenant context. Memory, causal state, and projection helpers must not rely on caller-supplied scope names alone; they use the authenticated actor, tenant claim, collaboration membership, or internal-service identity appropriate to the operation.

### Signed message flow

1. A runtime sender builds a cognitive `AgentEvent` or `Envelope` from a `ColumnMessage`.
2. The sender signs the request with the shared A2A runtime signature headers: `X-Frontier-Subject`, `X-Frontier-Nonce`, `X-Frontier-Timestamp`, `X-Correlation-ID`, and `X-Frontier-Signature`.
3. Backend middleware verifies the profile-specific auth requirements, signed runtime headers, timestamp freshness, and nonce replay status.
4. The cognitive admission handler validates the message shape, tenant/assembly ownership, known source and target columns, and semantic replay marker.
5. Accepted messages can be recorded as replay markers and emitted into audit/observability paths. Replayed or conflicting messages fail closed before causal state mutation.

### Policy gate flow

Every cortical execution step runs through the shared column runtime gate before model calls, retrieval, tool calls, memory writes, or commitment publication. The gate evaluates authenticated context, tenant ownership, column capability, assembly admission policy, runtime provider/model allowlists, tool/retrieval/network allowlists, budget counters, and audit emission. Denials use stable reason codes where exposed through backend audit events.

### Deployment profile contract

Runtime profile behavior is part of the architecture contract:

- `local-lightweight` keeps quick local development usable and allows public minimal health plus unauthenticated local workflows where explicitly supported.
- `local-secure` requires authenticated operator access and signed/internal service identity for protected surfaces, while reporting unsafe secure-profile settings as degraded.
- `hosted` requires authenticated operator access, A2A runtime headers, signed messages, replay protection, egress allowlists, and MCP local-server policy unless remote MCP usage is explicitly confirmed. Unsafe hosted settings are blocked or reported unhealthy.

### Rollback and monitoring

For behavior-changing cortical runtime releases, rollback should restore the previous application image/configuration, keep persisted causal state intact, and verify replay markers still prevent duplicate message and commitment mutation. Operators should monitor authenticated health details, `secure_profile` status, structured audit events for cognition admission/policy/commitment/projection decisions, runtime security counters, projection failure status, and redaction markers on persisted/audited payloads.
