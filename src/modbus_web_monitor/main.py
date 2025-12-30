"""Entry point for running the FastAPI server."""

from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Modbus Web Monitor API server.")
    parser.add_argument(
        "--host",
        default=os.getenv("MODBUS_WEB_MONITOR_HOST", "127.0.0.1"),
        help="Bind host (default: 127.0.0.1 or MODBUS_WEB_MONITOR_HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MODBUS_WEB_MONITOR_PORT", "8000")),
        help="Bind port (default: 8000 or MODBUS_WEB_MONITOR_PORT).",
    )
    args = parser.parse_args()

    uvicorn.run(
        "modbus_web_monitor.api:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
