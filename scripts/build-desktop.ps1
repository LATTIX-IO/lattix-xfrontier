#requires -version 5
<#
.SYNOPSIS
  Build the Lattix xFrontier desktop installer locally on Windows (unsigned —
  fine for testing the install/first-run UX). Produces an .msi + .exe under
  apps/desktop-tauri/src-tauri/target/<triple>/release/bundle/.

.PREREQUISITES (install once)
  - Rust + Tauri CLI:   winget install Rustlang.Rustup ;  cargo install tauri-cli --version "^2"
  - Python 3.12 + PyInstaller:  pip install pyinstaller -e .
  - Node 20+ (on PATH)
  - Microsoft C++ Build Tools (MSVC) + WebView2 runtime (usually preinstalled on Win11)

.USAGE
  pwsh scripts/build-desktop.ps1
#>
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot/..").Path
$tauri = Join-Path $root "apps/desktop-tauri/src-tauri"
$bin = Join-Path $tauri "bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null

function Need($name) { if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "Missing prerequisite on PATH: $name" } }
Need python; Need node; Need cargo

# Resolve the Rust target triple (Tauri externalBin needs the suffix).
$triple = (& rustc -vV | Select-String "^host:").ToString().Split(":")[1].Trim()
Write-Host "== target triple: $triple =="

# 1) Backend sidecar (PyInstaller) -> bin/frontier-backend-<triple>.exe
Write-Host "== building backend sidecar (PyInstaller) =="
& python -m PyInstaller --noconfirm (Join-Path $root "packaging/frontier-backend.spec")
Copy-Item (Join-Path $root "dist/frontier-backend.exe") (Join-Path $bin "frontier-backend-$triple.exe") -Force

# 2) Frontend standalone + vendored Node
Write-Host "== building frontend (Next.js standalone) =="
Push-Location (Join-Path $root "apps/frontend")
& npm ci
& npm run build
$dest = Join-Path $tauri "resources/frontend"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item ".next/standalone/*" $dest -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $dest ".next/static") | Out-Null
Copy-Item ".next/static/*" (Join-Path $dest ".next/static") -Recurse -Force
if (Test-Path "public") { Copy-Item "public" (Join-Path $dest "public") -Recurse -Force }
Pop-Location
Copy-Item (Get-Command node).Source (Join-Path $bin "node.exe") -Force

# 3) Icons (generate from the placeholder source if not present)
if (-not (Test-Path (Join-Path $tauri "icons/icon.ico"))) {
  Write-Host "== generating icons from icon-source.png =="
  & cargo tauri icon (Join-Path $root "apps/desktop-tauri/icon-source.png")
}

# 4) Build the installer (unsigned; updater is disabled in tauri.conf for test builds)
Write-Host "== cargo tauri build =="
Push-Location $tauri
& cargo tauri build
Pop-Location

$bundle = Join-Path $tauri "target/$triple/release/bundle"
Write-Host "`n== DONE. Installers under: $bundle =="
Get-ChildItem -Recurse $bundle -Include *.msi, *.exe | ForEach-Object { Write-Host "  $($_.FullName)" }
Write-Host "`nSmartScreen will warn on the unsigned installer: click 'More info' -> 'Run anyway'."
