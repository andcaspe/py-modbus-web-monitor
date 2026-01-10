#!/usr/bin/env bash
set -euo pipefail

# Bootstrap venv, install backend, build frontend, and run uvicorn serving the built UI.
# Usage: PORT=8000 VENV=.venv ./scripts/run_local.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PORT="${PORT:-8000}"

if [ ! -d "$VENV" ]; then
  echo "Creating virtualenv at $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install -U pip
pip install -e "$ROOT"

echo "Installing frontend dependencies..."
pushd "$ROOT/frontend" >/dev/null
npm install
echo "Building frontend..."
npm run build
popd >/dev/null

echo "Starting uvicorn on 127.0.0.1:${PORT}"
exec uvicorn py_modbus_web_monitor.api:app --host 127.0.0.1 --port "$PORT"
