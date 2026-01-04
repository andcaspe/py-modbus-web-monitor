"""Pydantic schemas for the Modbus web monitor."""

from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

RegisterKind = Literal["holding", "input", "coil", "discrete"]
WriteKind = Literal["holding", "coil"]


class ConnectionSettings(BaseModel):
    """Connection details for a Modbus device."""

    model_config = ConfigDict(extra="forbid")

    protocol: Literal["tcp"] = Field(
        "tcp",
        description="Transport protocol. TCP is supported today; RTU planned later.",
    )
    host: str = Field(..., description="Modbus TCP host or IP address")
    port: int = Field(502, ge=1, le=65535)
    unit_id: int = Field(1, ge=0, le=255, alias="unitId")
    timeout: float = Field(3.0, gt=0, description="Socket timeout in seconds")


class ReadTarget(BaseModel):
    """Single register/coil read configuration."""

    model_config = ConfigDict(extra="forbid")

    kind: RegisterKind
    address: int = Field(..., ge=0, description="Zero-based address")
    count: int = Field(1, ge=1, le=125, description="Number of values to read")
    label: Optional[str] = Field(
        None, description="Friendly label for UI display and plots"
    )


class ReadRequest(BaseModel):
    """HTTP payload to fetch one-shot register values."""

    model_config = ConfigDict(extra="forbid")

    connection: ConnectionSettings
    targets: List[ReadTarget]


class WriteOperation(BaseModel):
    """Represents a write to a register or coil."""

    model_config = ConfigDict(extra="forbid")

    kind: WriteKind
    address: int = Field(..., ge=0)
    value: Union[int, bool, List[int], List[bool]]


class WriteRequest(BaseModel):
    """HTTP payload to perform one or more writes."""

    model_config = ConfigDict(extra="forbid")

    connection: ConnectionSettings
    writes: List[WriteOperation]


class MonitorConfig(BaseModel):
    """Configuration for a websocket monitor session."""

    model_config = ConfigDict(extra="forbid")

    connection: ConnectionSettings
    interval: float = Field(1.0, gt=0.05, le=60.0)
    targets: List[ReadTarget]


class MonitorCommand(BaseModel):
    """Envelope for websocket commands."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["configure", "write", "ping"]
    connection: Optional[ConnectionSettings] = None
    interval: Optional[float] = None
    targets: Optional[List[ReadTarget]] = None
    writes: Optional[List[WriteOperation]] = None

    @model_validator(mode="after")
    def validate_command(self) -> "MonitorCommand":
        if self.type == "configure":
            if not self.targets:
                raise ValueError("configure command requires targets")
            if not self.connection:
                raise ValueError("configure command requires connection details")
        if self.type == "write" and not self.writes:
            raise ValueError("write command requires 'writes'")
        return self


class AnomalyRequest(BaseModel):
    """HTTP payload to compute simple z-score anomalies from logged data."""

    model_config = ConfigDict(extra="forbid")

    connection: ConnectionSettings
    targets: List[ReadTarget]
    window: int = Field(60, ge=3, le=10000)
    min_samples: int = Field(10, ge=3, le=10000)

    @model_validator(mode="after")
    def validate_window(self) -> "AnomalyRequest":
        if self.min_samples > self.window:
            raise ValueError("min_samples must be <= window")
        return self
