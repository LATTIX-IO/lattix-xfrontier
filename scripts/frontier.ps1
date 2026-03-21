param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    if ($Args.Length -eq 1) {
        & $Args[0]
    }
    else {
        & $Args[0] $Args[1..($Args.Length - 1)]
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $($Args -join ' ')"
    }
}

function Get-PythonCommand {
    $venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return (Resolve-Path $venvPython).Path
    }
    return "python"
}

function Get-OpaCommand {
    $repoRoot = Get-RepoRoot
    $localOpa = Join-Path $repoRoot ".tools\opa\opa.exe"
    if (Test-Path $localOpa) {
        return (Resolve-Path $localOpa).Path
    }
    $pathOpa = Get-Command opa -ErrorAction SilentlyContinue
    if ($pathOpa) {
        return $pathOpa.Source
    }
    throw "OPA was not found. Install it to .tools\opa\opa.exe or add 'opa' to PATH."
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-InstallerEnvPath {
    $repoRoot = Get-RepoRoot
    $installerDir = Join-Path $repoRoot ".installer"
    if (-not (Test-Path $installerDir)) {
        New-Item -ItemType Directory -Path $installerDir | Out-Null
    }
    return (Join-Path $installerDir "local.env")
}

function Get-EnvMapFromFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $map = [ordered]@{}
    if (-not (Test-Path $Path)) {
        return $map
    }

    foreach ($line in Get-Content -Path $Path) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) {
            continue
        }

        $parts = $line -split '=', 2
        if ($parts.Length -eq 2) {
            $map[$parts[0]] = $parts[1]
        }
    }

    return $map
}

function New-RandomSecret {
    $bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48)
    return [Convert]::ToBase64String($bytes).TrimEnd('=')
}

function Ensure-ComposeEnvFile {
    $repoRoot = Get-RepoRoot
    $envExamplePath = Join-Path $repoRoot ".env.example"
    $envPath = Join-Path $repoRoot ".env"
    $installerEnvPath = Get-InstallerEnvPath

    $envMap = [ordered]@{}
    foreach ($sourcePath in @($envExamplePath, $envPath, $installerEnvPath)) {
        $sourceMap = Get-EnvMapFromFile -Path $sourcePath
        foreach ($key in $sourceMap.Keys) {
            $envMap[$key] = $sourceMap[$key]
        }
    }

    if (-not $envMap.Contains("A2A_JWT_SECRET") -or [string]::IsNullOrWhiteSpace($envMap["A2A_JWT_SECRET"])) {
        $envMap["A2A_JWT_SECRET"] = New-RandomSecret
        Write-Host "Generated local A2A_JWT_SECRET and stored it in .installer\local.env"
    }

    if (-not $envMap.Contains("A2A_JWT_ALG") -or [string]::IsNullOrWhiteSpace($envMap["A2A_JWT_ALG"])) {
        $envMap["A2A_JWT_ALG"] = "HS256"
    }
    if (-not $envMap.Contains("A2A_JWT_ISS") -or [string]::IsNullOrWhiteSpace($envMap["A2A_JWT_ISS"])) {
        $envMap["A2A_JWT_ISS"] = "lattix-frontier"
    }
    if (-not $envMap.Contains("A2A_JWT_AUD") -or [string]::IsNullOrWhiteSpace($envMap["A2A_JWT_AUD"])) {
        $envMap["A2A_JWT_AUD"] = "agents"
    }
    if (-not $envMap.Contains("A2A_TRUSTED_SUBJECTS") -or [string]::IsNullOrWhiteSpace($envMap["A2A_TRUSTED_SUBJECTS"])) {
        $envMap["A2A_TRUSTED_SUBJECTS"] = "orchestrator,research,code,review,coordinator"
    }
    if (-not $envMap.Contains("NEXT_PUBLIC_API_BASE_URL") -or [string]::IsNullOrWhiteSpace($envMap["NEXT_PUBLIC_API_BASE_URL"]) -or $envMap["NEXT_PUBLIC_API_BASE_URL"] -eq "http://localhost:8000") {
        $envMap["NEXT_PUBLIC_API_BASE_URL"] = "/api"
    }

    $lines = foreach ($key in $envMap.Keys) {
        "$key=$($envMap[$key])"
    }
    Set-Content -Path $installerEnvPath -Value ($lines -join "`n") -Encoding utf8
    return $installerEnvPath
}

function Get-ComposeCommandPrefix {
    $installerEnvPath = Get-InstallerEnvPath
    if (Test-Path $installerEnvPath) {
        return @("docker", "compose", "--env-file", $installerEnvPath)
    }
    return @("docker", "compose")
}

function Assert-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Test-DockerReady {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $false
    }

    & docker info *> $null
    return $LASTEXITCODE -eq 0
}

function Get-DockerDesktopExecutable {
    $candidates = @(
        "C:\Program Files\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Start-DockerDesktop {
    $dockerDesktop = Get-DockerDesktopExecutable
    if (-not $dockerDesktop) {
        throw "Docker Desktop is not running, and the Docker Desktop executable could not be found automatically."
    }

    Write-Host "Docker Desktop is installed but not running. Launching it now..."
    Start-Process -FilePath $dockerDesktop | Out-Null
}

function Wait-ForDockerReady {
    param(
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-DockerReady) {
            return
        }

        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    throw "Docker Desktop started but the Docker daemon did not become ready within $TimeoutSeconds seconds."
}

function Assert-DockerReady {
    Assert-CommandAvailable -Name "docker"
    if (Test-DockerReady) {
        return
    }

    if ($IsWindows) {
        Start-DockerDesktop
        Wait-ForDockerReady
        return
    }

    throw "Docker is not running or not reachable. Start Docker, wait for it to initialize, then retry."
}

function Show-Help {
    Write-Host "Lattix Frontier Windows helper"
    Write-Host ""
    Write-Host "Usage: .\scripts\frontier.ps1 <command>"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  bootstrap   Install editable package + dev dependencies"
    Write-Host "  dev         Start docker compose stack"
    Write-Host "  up          Start docker compose stack"
    Write-Host "  down        Stop docker compose stack"
    Write-Host "  start-docker Launch Docker Desktop and wait for readiness"
    Write-Host "  test        Run pytest"
    Write-Host "  lint        Run ruff check/format"
    Write-Host "  typecheck   Run mypy"
    Write-Host "  install-opa Install repo-local OPA binary"
    Write-Host "  policy-test Run opa tests"
    Write-Host "  health      Query http://localhost:8000/health"
    Write-Host "  ps          Show docker compose status"
    Write-Host "  logs        Show docker compose logs"
    Write-Host "  smoke       Alias for health"
    Write-Host ""
    Write-Host "Tip: You can also use the installed CLI directly with 'lattix dev'."
}

$python = Get-PythonCommand

switch ($Command.ToLowerInvariant()) {
    "bootstrap" {
        Invoke-ExternalCommand @($python, "-m", "pip", "install", "-e", ".[dev]")
    }
    "dev" {
        Assert-DockerReady
        $composeEnvFile = Ensure-ComposeEnvFile
        Invoke-ExternalCommand @("docker", "compose", "--env-file", $composeEnvFile, "up", "-d")
        $composeEnvMap = Get-EnvMapFromFile -Path $composeEnvFile
        $localStackHost = $composeEnvMap["LOCAL_STACK_HOST"]
        if ([string]::IsNullOrWhiteSpace($localStackHost)) {
            $localStackHost = "frontier.localhost"
        }
        Write-Host "Stack running. UI: http://$localStackHost ; API health: http://localhost:8000/health"
    }
    "up" {
        Assert-DockerReady
        $composeEnvFile = Ensure-ComposeEnvFile
        Invoke-ExternalCommand @("docker", "compose", "--env-file", $composeEnvFile, "up", "-d")
    }
    "down" {
        Assert-DockerReady
        $composePrefix = Get-ComposeCommandPrefix
        Invoke-ExternalCommand ($composePrefix + @("down", "-v"))
    }
    "start-docker" {
        Assert-DockerReady
        Write-Host "Docker Desktop is ready."
    }
    "test" {
        Invoke-ExternalCommand @($python, "-m", "pytest", "tests/", "-v", "--cov=lattix_frontier", "--cov-report=term-missing")
    }
    "lint" {
        Invoke-ExternalCommand @($python, "-m", "ruff", "check", ".", "--fix")
        Invoke-ExternalCommand @($python, "-m", "ruff", "format", ".")
    }
    "typecheck" {
        Invoke-ExternalCommand @($python, "-m", "mypy", "lattix_frontier/")
    }
    "install-opa" {
        $repoRoot = Get-RepoRoot
        $opaDir = Join-Path $repoRoot ".tools\opa"
        if (-not (Test-Path $opaDir)) {
            New-Item -ItemType Directory -Force -Path $opaDir | Out-Null
        }
        $opaPath = Join-Path $opaDir "opa.exe"
        Invoke-WebRequest -Uri "https://openpolicyagent.org/downloads/v0.68.0/opa_windows_amd64.exe" -OutFile $opaPath
        Invoke-ExternalCommand @($opaPath, "version")
    }
    "policy-test" {
        $opa = Get-OpaCommand
        Invoke-ExternalCommand @($opa, "test", "policies/", "-v")
    }
    "health" {
        Invoke-ExternalCommand @($python, "-c", "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())")
    }
    "ps" {
        Assert-DockerReady
        $composePrefix = Get-ComposeCommandPrefix
        Invoke-ExternalCommand ($composePrefix + @("ps"))
    }
    "logs" {
        Assert-DockerReady
        $composePrefix = Get-ComposeCommandPrefix
        Invoke-ExternalCommand ($composePrefix + @("logs", "--tail=200"))
    }
    "smoke" {
        Invoke-ExternalCommand @($python, "-c", "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health', timeout=5).read().decode())")
    }
    "help" {
        Show-Help
    }
    default {
        throw "Unknown command '$Command'. Run .\scripts\frontier.ps1 help"
    }
}