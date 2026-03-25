$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendRoot = Join-Path $RepoRoot "apps\frontend"

Write-Host "Lattix xFrontier pre-commit checks"

function Get-PythonCommand {
  $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    return (Resolve-Path $venvPython).Path
  }

  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    return "py -3"
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return $python.Source
  }

  throw "Python 3 is required but was not found in PATH."
}

function Get-OpaCommand {
  $localOpa = Join-Path $RepoRoot ".tools\opa\opa.exe"
  if (Test-Path $localOpa) {
    return (Resolve-Path $localOpa).Path
  }

  $opa = Get-Command opa -ErrorAction SilentlyContinue
  if ($opa) {
    return $opa.Source
  }

  return $null
}

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$CommandLine,
    [string]$WorkingDirectory = $RepoRoot
  )

  Write-Host $CommandLine
  Push-Location $WorkingDirectory
  try {
    Invoke-Expression $CommandLine
    if ($LASTEXITCODE -ne 0) {
      exit $LASTEXITCODE
    }
  }
  finally {
    Pop-Location
  }
}

function Invoke-IfAvailable {
  param(
    [Parameter(Mandatory = $true)]
    [string]$CommandName,
    [Parameter(Mandatory = $true)]
    [string]$RunLine,
    [Parameter(Mandatory = $true)]
    [string]$Description,
    [string]$WorkingDirectory = $RepoRoot
  )

  if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
    Write-Host " - $Description"
    Invoke-Step -CommandLine $RunLine -WorkingDirectory $WorkingDirectory
  }
  else {
    Write-Host " - Skipping $Description (missing $CommandName)"
  }
}

$Python = Get-PythonCommand
$Opa = Get-OpaCommand
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "1) Install Python dependencies"
Invoke-Step "$Python -m pip install -e `".[dev]`""

Write-Host "2) Install frontend dependencies"
Invoke-Step "npm ci" -WorkingDirectory $FrontendRoot

Write-Host "3) Python lint"
Invoke-Step "$Python -m ruff check ."

Write-Host "4) Python typecheck"
Invoke-Step "$Python -m mypy frontier_tooling/ frontier_runtime/"

Write-Host "5) Python tests"
Invoke-Step "$Python -m pytest apps/backend/tests tests -v --cov=app --cov=frontier_runtime --cov-report=term-missing"

Write-Host "6) Policy tests"
if ($Opa) {
  Invoke-Step "$Python scripts/run_opa.py test policies/ -v"
}
else {
  Write-Host " - Skipping policy tests (OPA missing; install to .tools\\opa\\opa.exe or add 'opa' to PATH)"
}

Write-Host "7) Frontend lint"
Invoke-Step "npm run lint" -WorkingDirectory $FrontendRoot

Write-Host "8) Frontend tests"
Invoke-Step "npm test" -WorkingDirectory $FrontendRoot

Write-Host "9) Frontend build"
Invoke-Step "npm run build" -WorkingDirectory $FrontendRoot

Write-Host "10) Security checks (optional)"
Invoke-IfAvailable -CommandName "semgrep" -RunLine "semgrep --config=auto --exclude .venv --exclude .next --exclude node_modules --exclude dist ." -Description "SAST via Semgrep"
Invoke-IfAvailable -CommandName "gitleaks" -RunLine "gitleaks detect --source . --no-git --redact" -Description "Secret scanning via Gitleaks"
Invoke-IfAvailable -CommandName "trivy" -RunLine "trivy fs --scanners vuln,misconfig --severity HIGH,CRITICAL --exit-code 1 --skip-dirs .venv,.next,node_modules,dist ." -Description "SCA/config via Trivy"

Write-Host "11) Helm validation (optional)"
Invoke-IfAvailable -CommandName "helm" -RunLine "helm lint ./helm/lattix-frontier; if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }; helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > `$null" -Description "Helm chart validation"

Write-Host "All pre-commit checks passed."
