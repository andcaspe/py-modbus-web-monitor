"""Async helpers to talk Modbus devices."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Sequence, TypeAlias, cast

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from .schemas import ConnectionSettings, ReadTarget, WriteOperation


class ModbusConnectionError(Exception):
    """Raised when a connection cannot be established."""


class ModbusOperationError(Exception):
    """Raised when a read/write operation fails."""


def _is_connected(client: AsyncModbusTcpClient) -> bool:
    connected = getattr(client, "connected", False)
    if connected:
        return True
    protocol = getattr(client, "protocol", None)
    return protocol is not None and getattr(protocol, "transport", None) is not None


ModbusReadResponse: TypeAlias = (
    ReadHoldingRegistersResponse
    | ReadInputRegistersResponse
    | ReadCoilsResponse
    | ReadDiscreteInputsResponse
)


def _extract_values(
    response: ModbusReadResponse, expected: int, target_kind: str
) -> List[int | bool]:
    if response.isError():
        raise ModbusOperationError(str(response))

    data: Sequence[int | bool]
    if hasattr(response, "registers"):
        data = response.registers
    elif hasattr(response, "bits"):
        data = response.bits
    else:  # pragma: no cover - defensive
        raise ModbusOperationError(f"Unexpected response for {target_kind}: {response}")

    # Trim just in case the backend returns more than requested
    return list(data[:expected])


class ModbusTcpSession:
    """Lightweight async session for a single Modbus TCP device."""

    def __init__(self, settings: ConnectionSettings):
        self.settings = settings
        self._client = AsyncModbusTcpClient(
            host=settings.host, port=settings.port, timeout=settings.timeout
        )
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        await self._client.connect()
        if not _is_connected(self._client):
            raise ModbusConnectionError(
                f"Could not connect to {self.settings.host}:{self.settings.port}"
            )

    async def close(self) -> None:
        # pymodbus async client close() is synchronous; don't await.
        self._client.close()

    async def read(
        self, target: ReadTarget, unit_id: int | None = None
    ) -> List[int | bool]:
        """Read a register/coil."""
        device_id = unit_id if unit_id is not None else self.settings.unit_id
        async with self._lock:
            try:
                if target.kind == "holding":
                    response = await self._client.read_holding_registers(
                        target.address, count=target.count, device_id=device_id
                    )
                elif target.kind == "input":
                    response = await self._client.read_input_registers(
                        target.address, count=target.count, device_id=device_id
                    )
                elif target.kind == "coil":
                    response = await self._client.read_coils(
                        target.address, count=target.count, device_id=device_id
                    )
                else:
                    response = await self._client.read_discrete_inputs(
                        target.address, count=target.count, device_id=device_id
                    )
            except ModbusException as exc:
                raise ModbusOperationError(str(exc)) from exc

        typed_response = cast(ModbusReadResponse, response)
        return _extract_values(typed_response, target.count, target.kind)

    async def write(
        self, operation: WriteOperation, unit_id: int | None = None
    ) -> None:
        """Write a register or coil value."""
        device_id = unit_id if unit_id is not None else self.settings.unit_id
        value = operation.value
        async with self._lock:
            try:
                if operation.kind == "holding":
                    if isinstance(value, list):
                        int_values = [int(v) for v in value]
                        response = await self._client.write_registers(
                            operation.address, int_values, device_id=device_id
                        )
                    else:
                        response = await self._client.write_register(
                            operation.address, int(value), device_id=device_id
                        )
                else:
                    # coil
                    if isinstance(value, list):
                        bool_values = [bool(v) for v in value]
                        response = await self._client.write_coils(
                            operation.address, bool_values, device_id=device_id
                        )
                    else:
                        response = await self._client.write_coil(
                            operation.address, bool(value), device_id=device_id
                        )
            except ModbusException as exc:
                raise ModbusOperationError(str(exc)) from exc

        if response.isError():
            raise ModbusOperationError(str(response))


@asynccontextmanager
async def tcp_session(settings: ConnectionSettings) -> AsyncIterator[ModbusTcpSession]:
    """Context manager that yields a connected ModbusTcpSession."""

    session = ModbusTcpSession(settings)
    await session.connect()
    try:
        yield session
    finally:
        await session.close()
