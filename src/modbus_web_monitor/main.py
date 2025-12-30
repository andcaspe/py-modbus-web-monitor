"""Entry point for running the FastAPI server."""

from __future__ import annotations

import uvicorn

from .api import app


def main() -> None:
    uvicorn.run(
        "modbus_web_monitor.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
