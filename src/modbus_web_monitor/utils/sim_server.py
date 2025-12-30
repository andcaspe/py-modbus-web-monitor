"""Simple Modbus TCP simulator for local testing."""

from __future__ import annotations

import argparse
import asyncio
import math
import random
from contextlib import suppress
from typing import Iterable

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer


async def _update_values(context: ModbusServerContext, period: float) -> None:
    """Continuously mutate registers/coils so the UI has changing data."""
    tick = 0
    phase = 0.0
    while True:
        tick += 1
        phase += 0.2
        holding = [((tick + i) * 7) % 1000 for i in range(16)]
        inputs = [
            max(0, min(65535, int(1000 * (0.5 + 0.5 * math.sin(phase + i * 0.3)) + random.randint(-10, 10))))
            for i in range(16)
        ]
        coils = [((tick + i) % 2) == 0 for i in range(16)]
        discrete = [not c for c in coils]

        slave_id = 0x00
        context[slave_id].setValues(3, 0, holding)  # holding registers
        context[slave_id].setValues(4, 0, inputs)  # input registers
        context[slave_id].setValues(1, 0, coils)  # coils
        context[slave_id].setValues(2, 0, discrete)  # discrete inputs

        await asyncio.sleep(period)


async def run_simulated_server(host: str = "127.0.0.1", port: int = 1502, period: float = 1.0) -> None:
    """Start an async Modbus TCP server with in-memory data."""
    device = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [0] * 200),
        co=ModbusSequentialDataBlock(0, [0] * 200),
        hr=ModbusSequentialDataBlock(0, [0] * 200),
        ir=ModbusSequentialDataBlock(0, [0] * 200),
    )
    context = ModbusServerContext(devices=device, single=True)
    updater = asyncio.create_task(_update_values(context, period))
    try:
        await StartAsyncTcpServer(
            context=context,
            address=(host, port),
        )
    finally:
        updater.cancel()
        with suppress(asyncio.CancelledError):
            await updater


def parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simulated Modbus TCP server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=1502, help="Bind port (default: 1502)")
    parser.add_argument(
        "--period",
        type=float,
        default=1.0,
        help="Update period in seconds for changing values (default: 1.0)",
    )
    return parser.parse_args(args)


def main(argv: Iterable[str] | None = None) -> None:
    options = parse_args(argv)
    asyncio.run(run_simulated_server(options.host, options.port, options.period))


if __name__ == "__main__":  # pragma: no cover
    main()
