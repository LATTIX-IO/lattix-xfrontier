$ErrorActionPreference = 'Stop'

$TempRoot = if ([string]::IsNullOrWhiteSpace($env:TEMP)) { '.\tmp' } else { $env:TEMP }
$BootstrapDir = Join-Path $TempRoot 'frontier-install'
$InstallerUrl = 'https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/frontier-installer.py'

function Test-PythonCommand {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.CommandInfo]$Command,

        [switch]$UseLauncher
    )

    try {
        if ($UseLauncher) {
            & $Command.Source -3 -c "import sys" *> $null
        }
        else {
            & $Command.Source -c "import sys" *> $null
        }
        $commandExitCode = $LASTEXITCODE
        return $commandExitCode -eq 0
    }
    catch {
        return $false
    }
}

function Stop-Bootstrap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [int]$ExitCode = 1
    )

    $global:LASTEXITCODE = $ExitCode
    throw $Message
}

Write-Host '==> Lattix xFrontier bootstrap'
Write-Host '==> Preparing installer workspace'
New-Item -ItemType Directory -Force -Path $BootstrapDir | Out-Null

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $Python -and -not (Test-PythonCommand -Command $Python -UseLauncher)) {
    $Python = $null
}
if ($null -eq $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $Python -and -not (Test-PythonCommand -Command $Python)) {
        $Python = $null
    }
}
if ($null -eq $Python) {
    throw "Python 3 is required but was not found as a working 'py' or 'python' command. Install Python 3 from https://python.org/downloads/windows/ (or the Microsoft Store), reopen PowerShell, and retry. If Windows is only exposing the Store alias, disable the python.exe/python3.exe App execution aliases after installation."
}

$InstallerPath = Join-Path $BootstrapDir 'frontier-installer.py'
Write-Host '==> Downloading installer'
Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath

Write-Host '==> Launching interactive installer'
if ($Python.Name -eq 'py.exe' -or $Python.Name -eq 'py') {
    & $Python.Source -3 $InstallerPath
} else {
    & $Python.Source $InstallerPath
}
$installerExitCode = $LASTEXITCODE
if ($installerExitCode -ne 0) {
    Stop-Bootstrap -Message "Installer failed with exit code $installerExitCode. The current terminal session was left open so you can inspect the error and retry." -ExitCode $installerExitCode
}
