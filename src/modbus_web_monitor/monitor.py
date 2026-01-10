"""Websocket monitoring loop."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import WebSocket

from .data_logger import reset_data_logger
from .modbus_client import (
    ModbusConnectionError,
    ModbusOperationError,
    ModbusTcpSession,
    tcp_session,
)
from .schemas import MonitorCommand, MonitorConfig, ReadTarget, WriteOperation


async def _poll_registers(
    websocket: WebSocket,
    session: ModbusTcpSession,
    config: MonitorConfig,
    stop_event: asyncio.Event,
    data_logger,
) -> None:
    """Poll configured registers and stream updates."""
    await websocket.send_json(
        {
            "type": "status",
            "message": f"Monitoring {len(config.targets)} target(s) every {config.interval}s",
        }
    )
    while not stop_event.is_set():
        payload: List[Dict[str, Any]] = []
        try:
            for target in config.targets:
                values = await session.read(target)
                payload.append(
                    {
                        "address": target.address,
                        "kind": target.kind,
                        "label": target.label or f"{target.kind}:{target.address}",
                        "values": values,
                    }
                )
        except ModbusOperationError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
        else:
            timestamp = datetime.now(timezone.utc).isoformat()
            await data_logger.log_readings(
                config.connection,
                payload,
                source="monitor",
                timestamp=timestamp,
            )
            await websocket.send_json(
                {
                    "type": "update",
                    "timestamp": timestamp,
                    "data": payload,
                }
            )

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=config.interval)
        except asyncio.TimeoutError:
            continue


async def _handle_commands(
    websocket: WebSocket,
    session: ModbusTcpSession,
    stop_event: asyncio.Event,
) -> None:
    """Handle write/ping commands from the websocket client."""
    async for raw in websocket.iter_text():
        try:
            data = json.loads(raw)
            command = MonitorCommand.model_validate(data)
        except Exception as exc:  # noqa: BLE001 - keep websocket alive
            await websocket.send_json({"type": "error", "message": f"Invalid payload: {exc}"})
            continue

        if command.type == "ping":
            await websocket.send_json({"type": "pong"})
            continue

        if command.type == "configure":
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Reconfiguration is not supported on an open socket. Reconnect instead.",
                }
            )
            continue

        if command.type == "write":
            await _perform_writes(websocket, session, command.writes or [])
            continue

    stop_event.set()


async def _perform_writes(
    websocket: WebSocket, session: ModbusTcpSession, writes: List[WriteOperation]
) -> None:
    for op in writes:
        try:
            await session.write(op)
        except ModbusOperationError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
            return
    await websocket.send_json({"type": "ack", "message": "write complete"})


async def run_monitor_session(websocket: WebSocket, config: MonitorConfig) -> None:
    """Spin up the Modbus session and coordinate polling + commands."""
    try:
        data_logger = reset_data_logger()
        async with tcp_session(config.connection) as session:
            stop_event = asyncio.Event()
            poll_task = asyncio.create_task(
                _poll_registers(websocket, session, config, stop_event, data_logger)
            )
            command_task = asyncio.create_task(
                _handle_commands(websocket, session, stop_event)
            )
            done, pending = await asyncio.wait(
                {poll_task, command_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )
            stop_event.set()
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
    except ModbusConnectionError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001 - report unexpected errors
        await websocket.send_json({"type": "error", "message": f"Server error: {exc}"})
