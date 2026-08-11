# Lattix xFrontier Quality Score

Quality here means a reviewer can tell what changed, what enforced it, what evidence backs it, and whether the security posture still holds. This document defines the evidence expected on every change. It does not replace `AGENTS.md` — it makes the shared standard measurable for this repo.

## Quality dimensions

| Dimension | Evidence source | Expected signal |
| --- | --- | --- |
| Test correctness | `make test` → `pytest apps/backend/tests tests` (406 tests), `npm test` in `apps/frontend/` (78 tests) | Behavior changes ship with tests; suite green in the canonical order |
| Policy enforcement | `make policy-test` → `python scripts/run_opa.py test policies/` (28 tests) | Every `policies/*.rego` change has a matching test in `policies/tests/` |
| Type safety | `make typecheck` → `mypy frontier_tooling/ frontier_runtime/` | Gated scope stays at zero errors under `strict` |
| Lint and format | `ruff check .`, `ruff format --check .`, `eslint` | No new lint findings; new files land already formatted |
| Runtime security posture | `frontier_runtime/security.py`, `apps/backend/app/request_security.py`, `SECURITY.md`, `THREAT-MODEL.md` | Auth, replay, capability, and policy paths fail closed and are tested |
| Isolation correctness | `frontier_runtime/sandbox.py`, `tests/unit/test_sandbox_policy.py`, `test_tool_jail.py`, `docs/SANDBOXING.md` | Strategy selection is explicit per host platform; no silent downgrade to a weaker tier |
| Contract stability | `packages/contracts/templates/*.schema.json`, `tests/unit/test_docs_contract.py`, `test_version_contract.py`, `test_tooling_contract.py` | Schema/API/CLI changes carry compatibility evidence |
| Deployment integrity | `make helm-validate`, `docker compose config`, `tests/unit/test_helm_security_contract.py`, `test_compose_auth_contract.py`, `test_container_image_contract.py` | Compose and Helm stay renderable and keep their security contract |
| Installer safety | `tests/unit/test_installer.py`, `test_public_installer.py`, `test_install_diagnostics.py`, `docs/INSTALLER.md` | Update/remove paths stay non-destructive; state manifest versioning preserved |
| Observability | `structlog`, OpenTelemetry exporters, `/observability/*`, `/audit/*` | New failure modes get structured logs, spans, or audit events |
| Documentation coverage | `README.md`, `docs/`, `.ai-memory/repo-profile.md` | Behavior, config, and operational changes update docs in the same change set |

## Current measured signals

Baseline taken 2026-08-10 on `feat/cognitive-mvp-foundation` @ `405aa70`. Re-measure before quoting these.

- `pytest` (canonical `testpaths` order): **406 passed**
- `ruff check .`: **clean**
- `mypy frontier_tooling/ frontier_runtime/`: **clean**, 21 files
- OPA: **28/28 pass**
- `vitest run`: **78 passed** across 12 files
- `eslint .` in `apps/frontend/`: **clean**
- Last desloppify scan (2026-03-23): overall **77.5**, objective **84.7**, 355 open items

## Known quality debt

Track these; do not treat a green gate as full coverage.

- **`apps/backend/` is not type-checked.** `make typecheck` and CI cover only `frontier_tooling/` and `frontier_runtime/`. The backend carries 310 `mypy --strict` errors across 4 files. `lattix typecheck` narrows further, to `frontier_tooling` alone.
- **Test-order fragility.** 12 backend memory and A2A-replay tests fail when `tests/unit` runs before `apps/backend/tests`, and pass standalone. Module-level state leaks between files; the passing order is baked into `pyproject.toml` `testpaths` and CI.
- **`ruff format` is not gated.** CI runs `ruff check` only; 5 files currently differ from `ruff format` output.
- **`apps/backend/app/main.py` is 15,839 LOC** — 87 routes, 34 models, one file. Flagged by desloppify at 10,112 LOC; it has grown since.
- **Control-plane persistence fails silently.** `_persist_store_state()` swallows every exception, so a missing or unreachable Postgres loses all definitions on restart with no signal. The A2A nonce path is the one place that correctly returns `503`.
- **`budget_policy.rego` has no test file**; every other policy does.
- **Two isolation strategies are enum-only.** `k8s-gvisor` and `k8s-kata` have no implementing strategy class.

## Review cadence

- Re-measure the signals above before any release or posture claim.
- Re-run `make policy-test` whenever `policies/` changes.
- Re-run `make helm-validate` and compose config validation whenever `helm/`, `docker-compose*.yml`, or `envoy/` changes.
- Re-run the installer test set whenever `install/`, `frontier_tooling/installer.py`, or `frontier_runtime/install.py` changes.
- Re-scan with desloppify when the score is older than a release cycle.
