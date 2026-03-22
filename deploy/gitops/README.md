# lattix-frontier-gitops

GitOps control plane for deploying and promoting Lattix xFrontier Microsoft AI Foundry configuration.

## Scope

- Environment overlays and release manifests.
- CI/CD workflows for validate, plan, apply, evaluate, promote, rollback.
- Drift detection and export reconciliation jobs.
- Policy/eval gates for deployment safety.

## Structure

- `environments/dev/`: dev overlays and deployment values.
- `environments/stage/`: stage overlays and pre-prod controls.
- `environments/prod/`: production overlays and strict approvals.
- `pipelines/`: reusable pipeline templates and workflow definitions.
- `scripts/`: deployment helpers and reconciliation scripts.
- `releases/`: release bundles/changelogs per environment.

## Pipeline Expectations

1. Validate against `lattix-frontier-contracts`.
2. Plan and diff against target environment.
3. Apply infra/config changes.
4. Run evaluations and guardrail checks.
5. Promote with approvals.
6. Support rollback from Git history.

## Foundry Connection Setup

Environment overlays:

- `environments/dev/foundry.project.yaml`
- `environments/stage/foundry.project.yaml`
- `environments/prod/foundry.project.yaml`

Required GitHub Actions secrets per environment:

- `FOUNDRY_PROJECT_ENDPOINT_DEV`
- `FOUNDRY_API_KEY_DEV`
- `FOUNDRY_PROJECT_REGION_DEV`
- `FOUNDRY_PROJECT_ENDPOINT_STAGE`
- `FOUNDRY_API_KEY_STAGE`
- `FOUNDRY_PROJECT_REGION_STAGE`
- `FOUNDRY_PROJECT_ENDPOINT_PROD`
- `FOUNDRY_API_KEY_PROD`
- `FOUNDRY_PROJECT_REGION_PROD`

Populate secrets with GitHub CLI:

```powershell
gh secret set FOUNDRY_PROJECT_ENDPOINT_DEV --body "https://<endpoint>/api/projects/<project>"
gh secret set FOUNDRY_API_KEY_DEV --body "<api-key>"
gh secret set FOUNDRY_PROJECT_REGION_DEV --body "eastus2"
```

Repeat for `STAGE` and `PROD`.

## Smoke Test

GitHub Actions workflow: `.github/workflows/foundry-smoke.yml`

Run manually:

```powershell
gh workflow run foundry-smoke.yml -f environment=dev
gh run watch
```

Local smoke test fallback:

```powershell
$env:FOUNDRY_PROJECT_ENDPOINT_DEV="https://<endpoint>/api/projects/<project>"
$env:FOUNDRY_API_KEY_DEV="<api-key>"
$env:FOUNDRY_PROJECT_REGION_DEV="eastus2"
./scripts/validate_required_secrets.ps1 -Environment dev
./scripts/smoke_foundry.ps1 -Environment dev
```
