# Modbus Web Monitor

FastAPI + WebSocket backend with a React UI for reading and writing Modbus devices over TCP. The backend ships as an installable Python package so it can be embedded or packaged later (e.g., `.deb`). RTU support can be added on top of the existing abstractions.

## Features
- Async FastAPI server with WebSocket streaming
- One-shot REST endpoints for read/write
- React UI with live table + trend chart (Recharts)
- Supports coils, discrete inputs, input registers, and holding registers
- Simple write form (single or multiple values) over the same WebSocket

## Docs
- [Quickstart](docs/quickstart.md)
- [Simulated Modbus server](docs/simulated-server.md)
- [Docker](docs/docker.md)
- [Testing and CI](docs/testing.md)
- [API reference](docs/api.md)
- [Data logging](docs/logging.md)
- [Notebooks](docs/notebooks.md)
- [Packaging](docs/packaging.md)
- [Roadmap](docs/roadmap.md)
