# Modbus Web Monitor

FastAPI + WebSocket backend with a React UI for reading and writing Modbus devices over TCP. The backend ships as an installable Python package so it can be embedded or packaged later (e.g., `.deb`). RTU support can be added on top of the existing abstractions.

## Features
- Async FastAPI server with WebSocket streaming
- One-shot REST endpoints for read/write
- React UI with live table + trend chart (Recharts)
- Supports coils, discrete inputs, input registers, and holding registers
- Simple write form (single or multiple values) over the same WebSocket

## Quickstart
### Backend (FastAPI)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn modbus_web_monitor.api:app --reload  # http://localhost:8000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev  # http://localhost:5173 (talks to backend at http://localhost:8000 by default)
```

To build the UI and let FastAPI serve it from `/app`:
```bash
cd frontend
npm run build
cd ..
uvicorn modbus_web_monitor.api:app --reload
```
The backend will serve `frontend/dist` automatically if it exists.

### Simulated Modbus server (for testing)
Run a local Modbus TCP device with changing registers/coils:
```bash
pip install -e .
modbus-sim-server --port 1502 --period 0.5  # defaults: host=0.0.0.0, port=1502, period=1s
```
Holding/input registers vary over time; coils/discrete inputs flip each tick.

### One-command setup/run (dev)
```bash
./scripts/run_local.sh   # PORT=8000 VENV=.venv override as needed
```
The script creates a venv, installs the backend, builds the frontend, and runs uvicorn serving the built UI.

## WebSocket protocol (`/ws/monitor`)
- **First message (required)**:
```json
{
  "type": "configure",
  "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
  "interval": 1.0,
  "targets": [
    {"kind": "holding", "address": 0, "count": 1, "label": "Reg 0"}
  ]
}
```
- **Updates**:
```json
{
  "type": "update",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": [
    {"address": 0, "kind": "holding", "label": "Reg 0", "values": [123]}
  ]
}
```
- **Writes** (can be sent any time after configure):
```json
{"type": "write", "writes": [{"kind": "holding", "address": 10, "value": 42}]}
```
For coils, values are coerced from booleans/0/1; multiple values are supported with lists.

## REST endpoints
- `POST /api/modbus/read`  
  ```json
  {
    "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
    "targets": [{"kind": "coil", "address": 0, "count": 4}]
  }
  ```
  Returns `{"data": [{"address": 0, "kind": "coil", "label": "...", "values": [true, false, ...]}]}`

- `POST /api/modbus/write`  
  ```json
  {
    "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
    "writes": [{"kind": "holding", "address": 15, "value": [1, 2, 3]}]
  }
  ```

## Packaging
- Install/editable: `pip install -e .`
- Build wheel/sdist: `python -m build` (requires `build` or use `hatch build`)
- CLI entrypoint: `modbus-web-monitor` runs `uvicorn modbus_web_monitor.api:app`
- Bundle the built UI into the Python package: `scripts/sync_web_assets.sh`
To include the UI in a wheel/sdist, run `scripts/sync_web_assets.sh` before `python -m build`.

### Debian package (bundled deps)
Build a `.deb` that includes a venv + the compiled frontend UI:
```bash
scripts/build_deb.sh
sudo dpkg -i build/deb/modbus-web-monitor_0.1.0_amd64.deb
modbus-web-monitor
```
Optional overrides:
- `DEB_MAINTAINER="Name <email>"` (control file)
- `DEB_VERSION=0.1.0+local1` (package version)
- `BUILD_DIR=build/deb` (output dir)

Runtime overrides:
- `modbus-web-monitor --host 0.0.0.0 --port 8000`
- Or set `MODBUS_WEB_MONITOR_HOST` / `MODBUS_WEB_MONITOR_PORT`

## Roadmap ideas
- Add Modbus RTU transport
- Persist/read monitor presets
- Authentication + role-based write access
