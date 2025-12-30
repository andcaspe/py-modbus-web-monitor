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

## Roadmap ideas
- Add Modbus RTU transport
- Persist/read monitor presets
- Authentication + role-based write access
