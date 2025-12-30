#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_NAME="modbus-web-monitor"
BUILD_DIR="${BUILD_DIR:-$ROOT/build/deb}"
ARCH="$(dpkg --print-architecture)"

VERSION="${DEB_VERSION:-$(python3 - <<'PY'
from pathlib import Path
import tomllib

pyproject = tomllib.loads(Path("pyproject.toml").read_text())
print(pyproject["project"]["version"])
PY
)}"

STAGING="$BUILD_DIR/${PKG_NAME}_${VERSION}_${ARCH}"

if ! command -v dpkg-deb >/dev/null; then
  echo "dpkg-deb not found. Install dpkg-dev." >&2
  exit 1
fi

if ! command -v npm >/dev/null; then
  echo "npm not found. Install nodejs + npm." >&2
  exit 1
fi

if ! command -v python3 >/dev/null; then
  echo "python3 not found." >&2
  exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING/DEBIAN" "$STAGING/opt/$PKG_NAME" "$STAGING/usr/bin"

"$ROOT/scripts/sync_web_assets.sh"

VENV="$STAGING/opt/$PKG_NAME/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install "$ROOT"

cat > "$STAGING/usr/bin/modbus-web-monitor" <<'EOF_WRAPPER'
#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/modbus-web-monitor"
exec "$ROOT/venv/bin/modbus-web-monitor" "$@"
EOF_WRAPPER
chmod 0755 "$STAGING/usr/bin/modbus-web-monitor"

cat > "$STAGING/DEBIAN/control" <<EOF_CONTROL
Package: $PKG_NAME
Version: $VERSION
Section: web
Priority: optional
Architecture: $ARCH
Depends: python3
Maintainer: ${DEB_MAINTAINER:-Your Name <you@example.com>}
Description: FastAPI + WebSocket Modbus monitor with a React UI.
 One-command launcher: modbus-web-monitor
EOF_CONTROL

mkdir -p "$BUILD_DIR"
dpkg-deb --build "$STAGING" "$BUILD_DIR"

echo "Built: $BUILD_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
