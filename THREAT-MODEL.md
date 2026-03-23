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

- route-local auth enforcement via `_enforce_request_authn(...)`
- configurable policy and guardrail evaluation in application code
- regex-based safety signals and policy gates
- local-first runtime assumptions
- graph-definition CRUD, publish, activate, rollback, and execution control plane

Current strengths:

- immutable definition lifecycle with publish and activate pointers
- audit/event hooks for many mutation paths
- explicit graph schema contract
- local-only egress/runtime defaults in several platform settings

Current weaknesses:

- auth is not globally fail-closed by default
- some sensitive introspection endpoints remain too readable
- CORS is broader than necessary
- security headers are not uniformly applied in this app
- replay/nonce handling is weaker than the orchestrator implementation
- backend errors can leak internal guardrail/runtime details

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
| Backend auth | `apps/backend` auth is route-local and not fail-closed by default | anonymous or weakly gated access | some routes already use `_enforce_request_authn(...)` | centralize auth model and default to secure/full fail-closed |
| Security policy disclosure | `/platform/security-policy` is too readable | attacker reconnaissance | none adequate | require auth and classify endpoint visibility |
| Introspection leakage | `/healthz` and runtime readiness/provider endpoints expose too much detail | service and trust boundary reconnaissance | partial route separation only | minimal public health, detailed authenticated/internal diagnostics |
| OPA path checks | prefix/path semantics are weak in fallback and policy | possible authorization bypass | sandbox artifact staging has stronger containment checks | align all filesystem checks on canonical containment |
| Policy drift | Rego policy and Python fallback duplicate rules | inconsistent enforcement | fail-closed behavior exists in some paths | parity tests + single source of truth |
| Static agent allowlists | hardcoded allowed tools in policy/fallback | new agents have no dynamic policy coverage | hardcoded defaults only | move policy inputs to config-backed dynamic model |
| Capability enforcement | capability claims are minted more richly than enforced | over-permission or false confidence | narrow current usage partially reduces blast radius | enforce read/write/tool-budget claims explicitly |
| Replay cache | backend nonce/replay handling lacks TTL semantics | replay weakening and memory pressure | orchestrator JWT code is stronger elsewhere | reuse stronger TTL-based replay semantics |
| Worker transport | worker A2A transport is too lightweight for non-local trust | MITM / weak transport assumptions | local mode is often plaintext and loopback-oriented | explicit HTTPS/TLS policy outside local-only mode |
| Error leakage | backend runtime/guardrail errors expose internals | rule enumeration and recon | logs/audit exist but caller responses still leak details | sanitize caller-facing errors |
| CORS | backend allows wildcard methods/headers | broader browser attack surface than needed | localhost origin restriction helps | explicit allowlists |
| Security headers | backend app lacks the stronger header middleware pattern | weaker browser/API hardening | stronger middleware already exists in legacy package | port/reuse in `apps/backend` |
| Memory boundaries | scopes are labels more than strongly enforced boundaries | cross-scope or cross-tenant data bleed risk | some policy vocabulary exists | implement real memory access control |
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

## Immediate next remediation wave

After Phase 0, the next concrete execution order is:

1. fix OPA/path containment semantics
2. gate `/platform/security-policy`
3. default secure/full backend auth to fail closed
4. minimize public introspection leakage
5. port/extract stronger auth/security-header/replay primitives from `lattix_frontier` into canonical surfaces
