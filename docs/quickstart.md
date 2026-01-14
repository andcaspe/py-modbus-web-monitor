# Quickstart

## Backend (FastAPI)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn py_modbus_web_monitor.api:app --reload  # http://localhost:8000
```

## Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev  # http://localhost:5173 (talks to backend at http://localhost:8000 by default)
```

To build the UI and let FastAPI serve it from `/`:
```bash
cd frontend
npm run build
cd ..
uvicorn py_modbus_web_monitor.api:app --reload
```
Open `http://localhost:8000/` (the legacy `/app` path still works).
The backend will serve `frontend/dist` automatically if it exists.

## One-command setup/run (dev)
```bash
./scripts/run_local.sh   # PORT=8000 VENV=.venv override as needed
```
The script creates a venv, installs the backend, builds the frontend, and runs uvicorn serving the built UI.

## UI defaults
The UI connects to `127.0.0.1:502` by default. You can override the defaults when building the frontend with:
- `VITE_DEFAULT_MODBUS_HOST`
- `VITE_DEFAULT_MODBUS_PORT`

For Docker Compose, these are set automatically to `sim:1502`.
