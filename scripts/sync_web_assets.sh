#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"
PACKAGE_WEB="$ROOT/src/modbus_web_monitor/web"

if ! command -v npm >/dev/null; then
  echo "npm not found. Install nodejs + npm." >&2
  exit 1
fi

npm --prefix "$FRONTEND" ci
npm --prefix "$FRONTEND" run build

rm -rf "$PACKAGE_WEB"
mkdir -p "$PACKAGE_WEB"
cp -a "$FRONTEND/dist/." "$PACKAGE_WEB/"

echo "Synced web assets to $PACKAGE_WEB"
