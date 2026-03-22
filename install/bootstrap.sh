#!/usr/bin/env sh
set -eu

BOOTSTRAP_DIR="${TMPDIR:-/tmp}/frontier-install"
INSTALLER_URL="${INSTALLER_URL:-https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/frontier-installer.py}"

echo "==> Lattix xFrontier bootstrap"
echo "==> Preparing installer workspace"
mkdir -p "$BOOTSTRAP_DIR"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 is required but was not found in PATH."
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  echo "==> Downloading installer"
  curl -fsSL "$INSTALLER_URL" -o "$BOOTSTRAP_DIR/frontier-installer.py"
else
  echo "curl is required to download the installer."
  exit 1
fi

echo "==> Launching interactive installer"
exec "$PYTHON_BIN" "$BOOTSTRAP_DIR/frontier-installer.py"
