#!/usr/bin/env sh
set -eu

BOOTSTRAP_DIR="${TMPDIR:-/tmp}/frontier-install"
INSTALLER_URL="https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/frontier-installer.py"
LOCAL_INSTALLER="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/frontier-installer.py"

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

if [ -f "$LOCAL_INSTALLER" ]; then
  echo "==> Using local checkout installer"
  INSTALLER_PATH="$LOCAL_INSTALLER"
elif command -v curl >/dev/null 2>&1; then
  echo "==> Downloading installer"
  curl -fsSL "$INSTALLER_URL" -o "$BOOTSTRAP_DIR/frontier-installer.py"
  INSTALLER_PATH="$BOOTSTRAP_DIR/frontier-installer.py"
else
  echo "curl is required to download the installer."
  exit 1
fi

echo "==> Launching interactive installer"
if [ -z "${FRONTIER_INSTALLER_OUTPUT:-}" ] && [ -t 0 ] && [ -t 1 ]; then
  export FRONTIER_INSTALLER_OUTPUT=tui
fi
if "$PYTHON_BIN" "$INSTALLER_PATH"; then
  :
else
  installer_exit_code=$?
  echo "Installer failed with exit code $installer_exit_code. The current shell was left intact so you can inspect the error and retry." >&2
  exit "$installer_exit_code"
fi
