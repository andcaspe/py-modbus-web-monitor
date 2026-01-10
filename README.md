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
modbus-sim-server --port 1502 --period 0.5  # defaults: host=127.0.0.1, port=1502, period=1s
```
Holding/input registers vary over time; coils/discrete inputs flip each tick.

Optional fault injection + sine wave signals:
```bash
modbus-sim-server \
  --holding-signal sine \
  --input-signal sine \
  --fault-enable \
  --fault-mode drop \
  --fault-kind input \
  --fault-addresses 0 \
  --fault-every 20 \
  --fault-duration 5 \
  --fault-magnitude 400
```

Set a target cycle length for sine waves (e.g., 2 seconds per full cycle):
```bash
modbus-sim-server --input-signal sine --holding-signal sine --period 0.1 --cycle-seconds 2
```

Or use a preset fault profile:
```bash
modbus-sim-server --fault-profile sine_drop
```
Available profiles: `sine_drop`, `sensor_drift`, `compressor`.
Each profile also ships default outlier settings you can enable with `--outlier-enable`.

Example: profile + outliers enabled:
```bash
modbus-sim-server --fault-profile sine_drop --outlier-enable
```

Point-wise outliers (single-tick spikes/drops):
```bash
modbus-sim-server \
  --holding-signal sine \
  --input-signal sine \
  --outlier-enable \
  --outlier-kind holding \
  --outlier-addresses 0-3 \
  --outlier-probability 0.1 \
  --outlier-mode random \
  --outlier-magnitude 350
```

### One-command setup/run (dev)
```bash
./scripts/run_local.sh   # PORT=8000 VENV=.venv override as needed
```
The script creates a venv, installs the backend, builds the frontend, and runs uvicorn serving the built UI.

### Docker (one command)
Build and run the web app:
```bash
docker compose up --build
```
Open `http://localhost:8000/app`.

Optional simulated Modbus device (profile-based):
```bash
docker compose --profile sim up --build
```
In the UI, set host to `sim` and port to `1502`.

## Testing & CI/CD
The project includes a suite of integration tests that verify the REST API and WebSocket functionality using a simulated Modbus server.

### Running Tests Locally
1.  **Install development dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```
2.  **Run the test suite**:
    ```bash
    python tests/run_all.py
    ```
    This will execute all tests and generate Allure results in `outputs/allure-results`.

3.  **View Allure Report (optional)**:
    If you have the [Allure CLI](https://allurereport.org/docs/install/) installed:
    ```bash
    allure serve outputs/allure-results
    ```

### Continuous Integration
On every push to `main` or `master`, GitHub Actions automatically:
- Runs the integration tests across Python 3.10, 3.11, and 3.12.
- Generates a unified Allure report.
- Deploys the report to GitHub Pages.

**Live Test Report**: [https://andcaspe.github.io/py-modbus-web-monitor/](https://andcaspe.github.io/py-modbus-web-monitor/)

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

- `POST /api/anomaly/zscore`
  Computes z-scores from logged readings (no live Modbus read).
  ```json
  {
    "connection": {"protocol": "tcp", "host": "127.0.0.1", "port": 502, "unitId": 1},
    "targets": [{"kind": "holding", "address": 0, "count": 1}],
    "window": 60,
    "min_samples": 10
  }
  ```
  Returns the latest value, z-score, and sample counts per target value.

- `POST /api/anomaly/stl`
  Uses STL decomposition to compute z-scores from residuals.
  Requires `statsmodels` (`pip install -e ".[ml]"`).
  Same payload as `/api/anomaly/zscore`.

## Data logging (SQLite)
By default, holding/input readings are logged to a per monitor session file named like
`outputs/modbus_readings_YYYY-MM-DD_HH-mm-ss.sqlite` (local time).

Environment overrides:
- `MODBUS_WEB_MONITOR_LOG_ENABLED=false` to disable logging
- `MODBUS_WEB_MONITOR_LOG_KINDS=holding,input` (or `all`)

## Notebooks
`notebooks/modbus_readings_analysis.ipynb` loads the latest SQLite log from
`outputs/` (or a specific path you set in the notebook), plots the series, and
adds basic anomaly detection.

Suggested dependencies:
- `pandas`
- `matplotlib`
- `jupyter`
- Optional: `statsmodels` (`pip install -e ".[ml]"`)

Install via extras:
- `pip install -e ".[notebooks]"`

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
- `modbus-web-monitor --host 127.0.0.1 --port 8000`
- Or set `MODBUS_WEB_MONITOR_HOST` / `MODBUS_WEB_MONITOR_PORT`

## Roadmap ideas
- Add Modbus RTU transport
- Persist/read monitor presets
- Authentication + role-based write access
