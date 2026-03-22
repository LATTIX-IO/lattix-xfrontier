$ErrorActionPreference = 'Stop'

$BootstrapDir = Join-Path ($env:TEMP ?? '.\tmp') 'frontier-install'
$InstallerUrl = if ($env:INSTALLER_URL) { $env:INSTALLER_URL } else { 'https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/frontier-installer.py' }

Write-Host '==> Lattix xFrontier bootstrap'
Write-Host '==> Preparing installer workspace'
New-Item -ItemType Directory -Force -Path $BootstrapDir | Out-Null

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $Python) {
    $Python = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $Python) {
    throw 'Python 3 is required but was not found in PATH.'
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
