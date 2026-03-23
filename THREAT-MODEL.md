# Threat Model

## Purpose

This document is the canonical security expectations and migration-boundary reference for Lattix xFrontier.

It serves two jobs:

1. describe the **current-state** security posture and failure modes of the repository as it exists today; and
2. constrain implementation toward the **target-state** architecture where `apps/backend` is the sole canonical backend surface and `lattix_frontier/` is fully disconnected from active backend/runtime responsibility.

This file should be updated whenever security-relevant behavior, deployment modes, trust boundaries, or accepted exceptions change.

## Scope

In scope:

- `apps/backend/`
- `apps/workers/`
- `policies/`
- `docker-compose.yml`
- `docker-compose.local.yml`
- `helm/lattix-frontier/`
- top-level deployment and security documentation

Out of scope for this document:

- blue/green rollout mechanics for a future hosted product
- speculative future controls that are not tied to an actual trust boundary or current risk

## Current-state architecture

The repository currently contains **two security models**.

### 1. Backend model (`apps/backend`)

Primary file: `apps/backend/app/main.py`

Characteristics:

- central route inventory and middleware-backed request classification in `apps/backend/app/request_security.py`
- middleware-first auth enforcement with cached request auth context reused by `_enforce_request_authn(...)`
- configurable policy and guardrail evaluation in application code
- regex-based safety signals and policy gates
- local-first runtime assumptions
- graph-definition CRUD, publish, activate, rollback, and execution control plane

Current strengths:

- immutable definition lifecycle with publish and activate pointers
- audit/event hooks for many mutation paths
- explicit graph schema contract
- local-only egress/runtime defaults in several platform settings
- authenticated operator identity headers are already supported by the frontend API client
- backend routes now have explicit access classes with startup validation to catch unclassified endpoints
- security headers are now applied uniformly in `apps/backend`
- secure/local full-stack mode can now fail closed via environment-backed auth defaults
- backend CORS now uses explicit local methods and headers instead of wildcards
- backend A2A replay protection now uses TTL-based expiry with bounded pruning
- runtime/guardrail execution failures now sanitize caller-facing summaries
- backend/shared path authorization checks now use canonical containment under approved roots
- internal-only backend routes now require trusted service-style auth context instead of generic authenticated callers
- memory API and maintenance paths now validate scope-to-bucket alignment before reading or mutating memory state
- memory reads/writes now enforce actor, tenant, collaboration-session, or internal-service authorization depending on scope

Current weaknesses:

- auth still depends on deployment configuration rather than a single immutable runtime profile
- hosted/internal profile exposure rules are not yet codified as tightly as the secure-local profile
- some runtime-originated memory flows still rely on local execution context and need the same ownership contract carried into hosted worker/service boundaries
- policy sources are still split across backend fallback logic and Rego inputs
- worker/service transport expectations outside local-only mode are not fully hardened yet

## Target-state architecture

The target architecture is:

- `apps/backend` is the **only** canonical backend/control-plane surface.
- `apps/workers` remains the worker/runtime surface.
- logic currently living under `lattix_frontier/` is either:
  - migrated into `apps/backend` or `apps/workers`,
  - extracted into a small shared library with no competing backend surface, or
  - deleted.

### Target-state rules

1. No new feature work should deepen `lattix_frontier/` as a parallel backend.
2. Any reusable security primitive from `lattix_frontier/` must be either:
   - ported into `apps/backend`, or
   - extracted as a shared primitive with a clearly documented owner.
3. Deployment docs, runtime wiring, and tests must all point to `apps/backend` as the canonical backend.
4. Security expectations must be described against the target architecture, while current-state exceptions remain explicitly documented.

## Deployment modes

### Local-lightweight

Primary stack: `docker-compose.local.yml`

Intent:

- quick local iteration
- simpler frontend/backend/data-service startup
- convenience over full defense-in-depth

Expected characteristics:

- loopback-bound services where practical
- direct frontend to backend routing
- local-only exceptions explicitly allowed
- not the reference security posture for hosted or service-segmented operation

### Local-secure/full

Primary stack: `docker-compose.yml`

Intent:

- local deployment with the full gateway/policy/sandbox-oriented stack
- default local security posture
- closer approximation of service-level zero trust expectations

Expected characteristics:

- gateway-mediated browser/API flow
- OPA/policy infrastructure present
- sandbox egress mediation present
- stronger service-boundary expectations than local-lightweight mode

### Future hosted

Not the current execution focus, but the target assumptions are:

- TLS-required service boundaries
- no dev tokens/placeholders
- valid network segmentation
- fail-closed authn/authz
- no dependency on local-only convenience exceptions

## Assets

The following assets require explicit protection:

- workflow, agent, and guardrail definitions
- published and active definition revisions
- generated artifacts
- JWT secrets, signing material, and capability tokens
- sandbox policy/configuration
- memory data across run/session/user/tenant/agent/workflow scopes
- OPA policy inputs and authorization decisions
- deployment secrets (`.env`, installer env overlays, Vault-backed config)
- audit/event streams and observability data

## Actor classes

- anonymous user
- authenticated local operator
- authenticated service/orchestrator subject
- worker/runtime service
- builder/editor user
- future hosted operator/administrator

## Trust boundaries

1. Browser/UI → backend API
2. Backend API → persistence services (Postgres, Redis, Neo4j)
3. Backend runtime → worker/A2A execution surface
4. Orchestrator/worker → policy engine (OPA)
5. Runtime → sandbox/tool jail
6. Service → service across local/full stack network boundaries
7. Deployment/configuration layer → running services

## Service-level zero trust expectations

The secure/full stack target is **service-level zero trust**.

That means:

- no service is trusted merely because it is on the same machine, Docker network, or cluster
- every service boundary should be authenticated and authorized
- policy engines and network boundaries are defense-in-depth, not the only control
- diagnostics and health surfaces must be minimized by default
- local-only exceptions must be explicitly named and scoped to deployment mode

## Security invariants

The following must remain true as the system evolves:

1. Auth defaults fail closed in the secure/full stack.
2. Sensitive configuration and security posture details are not anonymously disclosed.
3. Policy decisions deny by default when uncertain.
4. Filesystem authorization uses canonical containment semantics, not prefix matching.
5. Replay protection expires correctly and does not degrade silently under load.
6. Capability claims that are minted are actually enforced.
7. Memory scope labels are not treated as sufficient protection without actual access control enforcement.
8. Backend/runtime error responses do not reveal guardrail rule internals to untrusted callers.
9. Deployment docs and runtime defaults describe the same security posture.

## Known failure modes and current mitigation status

| Area | Current issue | Impact | Current mitigation / compensating control | Planned remediation |
|---|---|---|---|---|
| Backend auth | `apps/backend` now centralizes route classification and request enforcement, but deployment profiles still decide when authenticated-read/mutate routes are mandatory outside secure/local full-stack mode | anonymous or weakly gated access if weaker profiles are misconfigured | central route inventory, middleware enforcement, startup validation, and secure local fail-closed defaults | make secure/hosted profile behavior immutable and consistently selected |
| Security policy disclosure | `/platform/security-policy` should not be public in secure/full mode | attacker reconnaissance | central route classification now marks it authenticated-read and secure local mode requires auth | classify endpoint visibility consistently across hosted/internal profiles |
| Introspection leakage | `/healthz` and runtime readiness/provider endpoints can expose too much detail | service and trust boundary reconnaissance | central route classification plus secure local mode now serves minimal public `/healthz` and authenticated diagnostics endpoints | extend the same contract to all hosted/internal profiles |
| OPA path checks | canonical containment is now enforced in backend loaders and shared fallback policy, but parity must remain consistent across all policy consumers | residual bypass risk if new callers reintroduce prefix checks | canonical containment checks now guard approved roots | keep parity tests and avoid new prefix-based checks |
| Policy drift | Rego policy and Python fallback duplicate rules | inconsistent enforcement | fail-closed behavior exists in some paths | parity tests + single source of truth |
| Static agent allowlists | hardcoded allowed tools in policy/fallback | new agents have no dynamic policy coverage | hardcoded defaults only | move policy inputs to config-backed dynamic model |
| Capability enforcement | capability claims are minted more richly than enforced | over-permission or false confidence | narrow current usage partially reduces blast radius | enforce read/write/tool-budget claims explicitly |
| Replay cache | backend A2A nonce handling now expires and prunes correctly, but other auth surfaces could still drift if reimplemented independently | reduced replay weakening / memory pressure risk | TTL-based expiry + bounded pruning in backend | converge remaining auth surfaces on shared replay primitive |
| Worker transport | worker A2A transport is too lightweight for non-local trust | MITM / weak transport assumptions | local mode is often plaintext and loopback-oriented | explicit HTTPS/TLS policy outside local-only mode |
| Error leakage | caller-facing runtime summaries are now sanitized, but other endpoints still need the same discipline when new failure modes are added | reduced rule-enumeration and recon risk | sanitized runtime/guardrail failure summaries + logs/audit retained | extend sanitization review to future hosted/internal APIs |
| CORS | backend local browser access now uses explicit allowlists | reduced browser attack surface | localhost origin restriction plus explicit method/header allowlists | keep deployment-specific origin config explicit |
| Security headers | header policy still needs expansion beyond the current baseline | weaker browser/API hardening | backend now sets `nosniff`, `DENY`, and restrictive CSP headers by middleware | extend header set for hosted/TLS profiles |
| Memory boundaries | backend memory routes now enforce scope-aware access checks, but hosted/runtime identity propagation is still incomplete | reduced cross-scope or cross-tenant bleed risk in backend API paths; remaining risk in broader service propagation | scope-to-bucket validation, actor/user checks, tenant claim checks, collaboration membership checks, and internal-only maintenance auth | carry the same ownership model into worker/runtime and hosted identity propagation |
| Helm network policies | current template is malformed/broken | false confidence in segmentation | none | repair and validate render/apply path |
| Deployment drift | docs/defaults around secure vs lightweight modes have been inconsistent | wrong operator assumptions | recent cleanup improved this | codify in docs + threat model + tests |
| Legacy backend drift | `lattix_frontier/` still contains active security/runtime logic | dual-surface confusion and security drift | documented intent to converge | Stage 0 migration/disconnection boundary |

## Migration boundary for removing `lattix_frontier/`

The following is the Phase 0 migration matrix.

| Surface | Current role | Phase 0 disposition | Notes |
|---|---|---|---|
| `lattix_frontier/api/middleware/auth.py` | stronger auth pattern | migrate to `apps/backend` or extract shared primitive | do not keep as legacy-only behavior |
| `lattix_frontier/api/middleware/security_headers.py` | stronger response-header hardening | migrate to `apps/backend` or extract shared primitive | should become canonical backend behavior |
| `lattix_frontier/security/jwt_auth.py` | stronger replay/revocation/token validation | extract shared primitive or port into backend auth layer | avoid parallel auth implementations |
| `lattix_frontier/security/opa_client.py` | OPA client + fallback | extract shared primitive after remediation, or retire if backend replaces policy path | fix path semantics before reuse |
| `lattix_frontier/sandbox/` | tool jail / isolation model | extract shared primitive for worker/backend use | security-critical; not a delete-first area |
| `lattix_frontier/guardrails/` | legacy filter-chain guardrails | migrate useful primitives, delete parallel runtime wiring | avoid second guardrail architecture |
| `lattix_frontier/orchestrator/` | legacy orchestration/runtime surface | disconnect then delete or reduce to worker/shared execution primitives | should not remain canonical |
| `lattix_frontier/api/routes/` | legacy API surface | disconnect from deployment path, then delete | target is `apps/backend` only |
| `lattix_frontier/agents/` | legacy A2A/client/server helpers | migrate needed runtime pieces to `apps/workers` or shared package | keep only what workers actually use |
| `lattix_frontier/persistence/` | state helpers | evaluate for extraction or replacement by backend platform services | no duplicate system of record |
| `lattix_frontier/events/` / `observability/` | event integrity / telemetry primitives | extract if still needed, otherwise delete duplicate surface | preserve audit guarantees |
| `lattix_frontier/cli.py` / install helpers | legacy operator entrypoints | update to point at canonical backend/workers or remove | no stale control path |
| `lattix_frontier/config.py` | shared settings and secret validation | extract shared config primitive if still needed | keep one config truth |
| `policies/*.rego` | policy source | retain, but feed from canonical backend/worker inputs | do not duplicate policy logic in two backends |

### Migration rule

Every live `lattix_frontier/` surface must be assigned one of three dispositions before new security work proceeds beyond Phase 0:

- **migrate** — port into `apps/backend` / `apps/workers`
- **extract** — move into a small shared primitive package with one owner
- **delete** — remove after disconnection

No item should remain in an unowned “we’ll figure it out later” state.

## Definition of done for Phase 0

Phase 0 is complete when:

1. `THREAT-MODEL.md` exists and is treated as canonical.
2. Current-state and target-state architectures are both documented.
3. `lattix_frontier/` is explicitly marked as transitional and bounded.
4. The migration matrix covers every still-live security/runtime area in `lattix_frontier/`.
5. New work is guided toward `apps/backend` / `apps/workers`, not legacy backend expansion.
6. Repo docs point readers to this threat model for security expectations and architecture convergence.

## Change management requirements

Any security-relevant change should update this file if it changes:

- trust boundaries
- deployment-mode assumptions
- public vs authenticated endpoint exposure
- token/replay/auth semantics
- sandbox policy/invariants
- memory boundary expectations
- the migration status of any `lattix_frontier/` surface

## Phase 1 completion status

Phase 1 secure-local hardening is complete when the following are true, and they are now true in the canonical backend/runtime surfaces:

1. path checks use canonical containment semantics under approved roots
2. `/platform/security-policy` and sensitive runtime diagnostics are gated in secure/full local mode
3. secure/full backend auth fails closed by default via deployment-backed profile settings
4. public introspection is minimized while authenticated diagnostic detail remains available
5. stronger replay and response-hardening primitives are ported into canonical surfaces

There are no remaining Phase 1 secure-local blocking tasks in the canonical backend/runtime surfaces. Remaining items now belong to Phase 2 and should be treated as the next execution wave rather than as incomplete Phase 1 work.

## Phase 2 focus

Phase 2 is the **hosted-parity and control-convergence** wave.

Its goal is to move from a verified secure-local baseline to a deployment model that remains trustworthy when services are separated, long-lived, and operated beyond a single local machine.

### Phase 2 objectives

1. make auth/profile behavior centrally enforced rather than route-local plus deployment-convention driven
2. harden non-local worker/service transport expectations
3. implement real memory access control instead of scope-label trust
4. converge Python fallback policy behavior and Rego policy behavior onto one verifiable contract
5. repair deployment-layer controls that currently provide incomplete or misleading protection

### Phase 2 implementation status

The first Phase 2 workstream is now partially complete in the canonical backend.

Implemented:

- explicit backend route inventory in `apps/backend/app/request_security.py`
- access classes for `public-minimal`, `authenticated-read`, `authenticated-mutate`, and `internal-only`
- central middleware enforcement in `apps/backend/app/main.py`
- startup validation that fails if new backend routes are added without classification
- shared response hardening helper in `apps/backend/app/security_headers.py`
- regression coverage for shared headers, route inventory completeness, and previously under-protected read surfaces
- internal-only route enforcement that now requires trusted subject or bearer-backed internal auth context
- memory scope-to-bucket validation for backend retrieval, consolidation, and world-graph projection paths
- backend memory authorization checks for session, user, tenant, agent, and workflow scopes
- regression coverage for cross-scope denial and internal maintenance endpoint protection

Still remaining for this workstream:

- define immutable runtime profiles for hosted/non-local operation rather than environment-convention-driven profile selection
- narrow any remaining differences between secure-local, local-lightweight, and future hosted endpoint exposure rules
- move beyond backend-only convergence so workers and service-to-service transport follow the same profile contract

The memory access control workstream is now partially implemented in the canonical backend as well.

Implemented:

- backend memory endpoints reject bucket/scope mismatches instead of trusting caller-supplied scope labels
- `session` and `user` memory access now binds to the authenticated actor identity
- `tenant` memory access now requires an explicit tenant claim that matches the bucket
- `agent` and `workflow` memory access now requires collaboration-session membership for non-internal callers
- internal consolidation and world-graph projection routes now require internal service authentication

Still remaining for this workstream:

- carry the same ownership and authorization model into worker/runtime execution flows beyond backend route handlers
- define how hosted identities and tenant claims are minted/verified so tenant authorization is not based on local header conventions alone
- extend memory authorization parity checks to non-backend consumers and policy sources

### Phase 2 workstreams

#### 1. Identity and profile convergence

- define immutable runtime profiles for `local-lightweight`, `local-secure/full`, and future hosted operation
- reduce route-by-route auth drift by centralizing profile-driven enforcement where practical
- ensure diagnostics, health, runtime-provider, and policy endpoints have one visibility policy per profile
- document the profile contract in deployment docs and examples

#### 2. Service-to-service transport hardening

- define explicit HTTPS/TLS expectations for worker and A2A transport outside local-only mode
- require stronger subject authentication and transport guarantees for non-local trust boundaries
- keep local-only exceptions explicit and isolated to the local deployment profiles

#### 3. Memory access control

- implement actual authorization checks for memory reads/writes across session, user, agent, workflow, and tenant-like scopes
- ensure retrieval, consolidation, and world-graph projection paths respect the same access model
- add regression coverage for cross-scope denial cases

#### 4. Policy source convergence

- reduce drift between backend fallback policy logic and `policies/*.rego`
- add parity tests for security-critical decisions such as path access, egress, capability claims, and runtime/tool budgets
- establish one source of truth for policy inputs and expected deny behavior

#### 5. Deployment control repair

- repair and validate Helm/network-policy artifacts so they provide real segmentation guarantees
- extend browser/API hardening headers for hosted/TLS profiles where appropriate
- keep secure/full and lightweight defaults aligned with docs, tests, and deployment manifests

### Definition of done for Phase 2

Phase 2 is complete when:

1. runtime profile behavior is centrally defined and consistently enforced
2. non-local worker/service transport has explicit hardened expectations and tests
3. memory operations enforce real access control rather than trusting scope names alone
4. backend fallback logic and Rego policy are covered by parity tests for security-critical decisions
5. Helm/network-policy artifacts are valid and verified instead of merely present
6. docs, manifests, and tests all describe the same hosted-vs-local security posture

### Recommended execution order for Phase 2

1. identity and profile convergence
2. policy source convergence for critical allow/deny paths
3. memory access control
4. service-to-service transport hardening
5. deployment control repair and hosted-profile documentation cleanup
