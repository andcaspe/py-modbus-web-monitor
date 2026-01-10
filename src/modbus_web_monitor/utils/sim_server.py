"""Simple Modbus TCP simulator for local testing."""

from __future__ import annotations

import argparse
import asyncio
import math
import random
import time
from contextlib import suppress
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Sequence

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer

_SIGNAL_MODES = {"ramp", "sine", "constant"}
_FAULT_MODES = {"drop", "spike", "drift", "stuck", "random"}
_FAULT_KINDS = {"holding", "input", "all"}
_OUTLIER_MODES = {"drop", "spike", "random"}
_PROFILES: dict[str, dict[str, dict[str, Any]]] = {
    "sine_drop": {
        "signal": {
            "holding_signal": "sine",
            "input_signal": "sine",
            "amplitude": 500.0,
            "offset": 600.0,
            "noise": 8.0,
            "phase_step": 0.2,
            "phase_shift": 0.25,
        },
        "fault": {
            "enabled": True,
            "kind": "input",
            "addresses": "0",
            "mode": "drop",
            "every": 20.0,
            "duration": 5.0,
            "magnitude": 400.0,
        },
        "outlier": {
            "kind": "input",
            "addresses": "0",
            "mode": "random",
            "probability": 0.04,
            "magnitude": 250.0,
        },
    },
    "sensor_drift": {
        "signal": {
            "holding_signal": "constant",
            "input_signal": "sine",
            "amplitude": 300.0,
            "offset": 700.0,
            "noise": 6.0,
            "phase_step": 0.1,
            "phase_shift": 0.2,
        },
        "fault": {
            "enabled": True,
            "kind": "input",
            "addresses": "0",
            "mode": "drift",
            "every": 25.0,
            "duration": 8.0,
            "magnitude": 250.0,
        },
        "outlier": {
            "kind": "input",
            "addresses": "0",
            "mode": "spike",
            "probability": 0.03,
            "magnitude": 200.0,
        },
    },
    "compressor": {
        "signal": {
            "holding_signal": "ramp",
            "input_signal": "sine",
            "amplitude": 650.0,
            "offset": 800.0,
            "noise": 12.0,
            "phase_step": 0.15,
            "phase_shift": 0.18,
        },
        "fault": {
            "enabled": True,
            "kind": "input",
            "addresses": "1-3",
            "mode": "spike",
            "every": 30.0,
            "duration": 3.0,
            "magnitude": 500.0,
        },
        "outlier": {
            "kind": "input",
            "addresses": "2",
            "mode": "spike",
            "probability": 0.06,
            "magnitude": 350.0,
        },
    },
}


@dataclass(frozen=True)
class SignalSettings:
    holding_signal: str = "sine"
    input_signal: str = "ramp"
    amplitude: float = 500.0
    offset: float = 600.0
    noise: float = 10.0
    phase_step: float = 0.2
    phase_shift: float = 0.3
    count: int = 16


@dataclass(frozen=True)
class FaultSettings:
    enabled: bool = False
    kind: str = "input"
    addresses: list[int] = field(default_factory=lambda: [0])
    mode: str = "drop"
    every: float = 30.0
    duration: float = 5.0
    magnitude: float = 300.0


@dataclass(frozen=True)
class OutlierSettings:
    enabled: bool = False
    kind: str = "holding"
    addresses: list[int] = field(default_factory=lambda: [0])
    mode: str = "random"
    probability: float = 0.05
    magnitude: float = 300.0


@dataclass
class FaultRuntime:
    next_at: float = 0.0
    active_until: float = 0.0
    fault_start: float = 0.0
    mode: str = "drop"
    stuck_values: dict[tuple[str, int], int] = field(default_factory=dict)


def _clamp_register(value: float) -> int:
    return max(0, min(65535, int(value)))


def _parse_addresses(raw: str | None, max_count: int) -> list[int]:
    if not raw:
        return [0]
    value = raw.strip().lower()
    if value == "all":
        return list(range(max_count))
    addresses: list[int] = []
    for chunk in value.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if start_str and end_str:
                start = int(start_str)
                end = int(end_str)
                if start <= end:
                    addresses.extend(range(start, end + 1))
                else:
                    addresses.extend(range(end, start + 1))
        else:
            addresses.append(int(part))
    filtered = [addr for addr in addresses if 0 <= addr < max_count]
    return sorted(set(filtered)) or [0]


def _normalize_addresses(raw: str | Iterable[int], max_count: int) -> list[int]:
    if isinstance(raw, str):
        return _parse_addresses(raw, max_count)
    addresses: list[int] = []
    for item in raw:
        try:
            address = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= address < max_count:
            addresses.append(address)
    return sorted(set(addresses)) or [0]


def _apply_profile(
    signal_settings: SignalSettings,
    fault_settings: FaultSettings,
    outlier_settings: OutlierSettings,
    profile_name: str,
    count: int,
) -> tuple[SignalSettings, FaultSettings, OutlierSettings]:
    profile = _PROFILES.get(profile_name)
    if not profile:
        return signal_settings, fault_settings, outlier_settings
    signal_overrides: dict[str, Any] = dict(profile.get("signal", {}))
    fault_overrides: dict[str, Any] = dict(profile.get("fault", {}))
    outlier_overrides: dict[str, Any] = dict(profile.get("outlier", {}))
    if "addresses" in fault_overrides:
        fault_overrides = dict(fault_overrides)
        fault_overrides["addresses"] = _normalize_addresses(
            fault_overrides["addresses"], count
        )
    if "addresses" in outlier_overrides:
        outlier_overrides = dict(outlier_overrides)
        outlier_overrides["addresses"] = _normalize_addresses(
            outlier_overrides["addresses"], count
        )
    signal_settings = replace(signal_settings, **signal_overrides)
    fault_settings = replace(fault_settings, **fault_overrides)
    outlier_settings = replace(outlier_settings, **outlier_overrides)
    return signal_settings, fault_settings, outlier_settings


def _signal_values(
    mode: str, tick: int, phase: float, settings: SignalSettings
) -> list[int]:
    count = settings.count
    if mode == "ramp":
        return [((tick + i) * 7) % 1000 for i in range(count)]
    if mode == "constant":
        return [_clamp_register(settings.offset) for _ in range(count)]
    if mode == "sine":
        values: list[int] = []
        for i in range(count):
            value = (
                settings.offset
                + settings.amplitude * math.sin(phase + i * settings.phase_shift)
                + random.uniform(-settings.noise, settings.noise)
            )
            values.append(_clamp_register(value))
        return values
    return [0 for _ in range(count)]


def _apply_faults(
    values: list[int],
    kind: str,
    addresses: list[int],
    mode: str,
    magnitude: float,
    now: float,
    fault_start: float,
    duration: float,
    stuck_values: dict[tuple[str, int], int],
) -> None:
    if not addresses:
        return
    if mode == "drop":
        for address in addresses:
            if 0 <= address < len(values):
                values[address] = _clamp_register(values[address] - magnitude)
        return
    if mode == "spike":
        for address in addresses:
            if 0 <= address < len(values):
                values[address] = _clamp_register(values[address] + magnitude)
        return
    if mode == "drift":
        if duration <= 0:
            offset = magnitude
        else:
            offset = magnitude * min(1.0, max(0.0, (now - fault_start) / duration))
        for address in addresses:
            if 0 <= address < len(values):
                values[address] = _clamp_register(values[address] + offset)
        return
    if mode == "stuck":
        for address in addresses:
            if 0 <= address < len(values):
                key = (kind, address)
                if key not in stuck_values:
                    stuck_values[key] = values[address]
                values[address] = stuck_values[key]
        return


def _apply_outliers(
    values: list[int],
    addresses: list[int],
    mode: str,
    probability: float,
    magnitude: float,
) -> None:
    if not addresses:
        return
    probability = max(0.0, min(1.0, probability))
    for address in addresses:
        if not (0 <= address < len(values)):
            continue
        if random.random() >= probability:
            continue
        direction = mode
        if mode == "random":
            direction = random.choice(sorted(_OUTLIER_MODES - {"random"}))
        if direction == "drop":
            values[address] = _clamp_register(values[address] - magnitude)
        elif direction == "spike":
            values[address] = _clamp_register(values[address] + magnitude)


async def _update_values(
    context: ModbusServerContext,
    period: float,
    signal_settings: SignalSettings,
    fault_settings: FaultSettings,
    outlier_settings: OutlierSettings,
) -> None:
    """Continuously mutate registers/coils so the UI has changing data."""
    tick = 0
    phase = 0.0
    runtime = FaultRuntime(next_at=time.monotonic() + fault_settings.every)
    while True:
        tick += 1
        phase += signal_settings.phase_step

        holding = _signal_values(
            signal_settings.holding_signal, tick, phase, signal_settings
        )
        inputs = _signal_values(
            signal_settings.input_signal, tick, phase, signal_settings
        )
        coils = [((tick + i) % 2) == 0 for i in range(signal_settings.count)]
        discrete = [not c for c in coils]

        now = time.monotonic()
        if (
            fault_settings.enabled
            and fault_settings.duration > 0
            and fault_settings.every > 0
        ):
            if now >= runtime.next_at:
                runtime.fault_start = now
                runtime.active_until = now + fault_settings.duration
                runtime.next_at = now + fault_settings.every
                runtime.stuck_values.clear()
                if fault_settings.mode == "random":
                    runtime.mode = random.choice(sorted(_FAULT_MODES - {"random"}))
                else:
                    runtime.mode = fault_settings.mode
            if now <= runtime.active_until:
                if fault_settings.kind in {"holding", "all"}:
                    _apply_faults(
                        holding,
                        "holding",
                        fault_settings.addresses,
                        runtime.mode,
                        fault_settings.magnitude,
                        now,
                        runtime.fault_start,
                        fault_settings.duration,
                        runtime.stuck_values,
                    )
                if fault_settings.kind in {"input", "all"}:
                    _apply_faults(
                        inputs,
                        "input",
                        fault_settings.addresses,
                        runtime.mode,
                        fault_settings.magnitude,
                        now,
                        runtime.fault_start,
                        fault_settings.duration,
                        runtime.stuck_values,
                    )

        if outlier_settings.enabled:
            if outlier_settings.kind in {"holding", "all"}:
                _apply_outliers(
                    holding,
                    outlier_settings.addresses,
                    outlier_settings.mode,
                    outlier_settings.probability,
                    outlier_settings.magnitude,
                )
            if outlier_settings.kind in {"input", "all"}:
                _apply_outliers(
                    inputs,
                    outlier_settings.addresses,
                    outlier_settings.mode,
                    outlier_settings.probability,
                    outlier_settings.magnitude,
                )

        slave_id = 0x00
        context[slave_id].setValues(3, 0, holding)  # holding registers
        context[slave_id].setValues(4, 0, inputs)  # input registers
        context[slave_id].setValues(1, 0, coils)  # coils
        context[slave_id].setValues(2, 0, discrete)  # discrete inputs

        await asyncio.sleep(period)


async def run_simulated_server(
    host: str = "127.0.0.1",
    port: int = 1502,
    period: float = 1.0,
    signal_settings: SignalSettings | None = None,
    fault_settings: FaultSettings | None = None,
    outlier_settings: OutlierSettings | None = None,
) -> None:
    """Start an async Modbus TCP server with in-memory data."""
    device = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [0] * 200),
        co=ModbusSequentialDataBlock(0, [0] * 200),
        hr=ModbusSequentialDataBlock(0, [0] * 200),
        ir=ModbusSequentialDataBlock(0, [0] * 200),
    )
    context = ModbusServerContext(devices=device, single=True)
    signal_settings = signal_settings or SignalSettings()
    fault_settings = fault_settings or FaultSettings()
    outlier_settings = outlier_settings or OutlierSettings()
    updater = asyncio.create_task(
        _update_values(
            context, period, signal_settings, fault_settings, outlier_settings
        )
    )
    try:
        await StartAsyncTcpServer(
            context=context,
            address=(host, port),
        )
    finally:
        updater.cancel()
        with suppress(asyncio.CancelledError):
            await updater


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a simulated Modbus TCP server.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=1502, help="Bind port (default: 1502)"
    )
    parser.add_argument(
        "--period",
        type=float,
        default=1.0,
        help="Update period in seconds for changing values (default: 1.0)",
    )
    parser.add_argument(
        "--register-count",
        type=int,
        default=16,
        help="How many registers/coils to update each tick (default: 16)",
    )
    parser.add_argument(
        "--fault-profile",
        choices=["none", *_PROFILES.keys()],
        default="none",
        help="Preset fault profile (default: none)",
    )
    parser.add_argument(
        "--outlier-enable",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable point-wise outliers",
    )
    parser.add_argument(
        "--outlier-kind",
        choices=sorted(_FAULT_KINDS),
        default=argparse.SUPPRESS,
        help="Target register kind for outliers (default: holding)",
    )
    parser.add_argument(
        "--outlier-addresses",
        default=argparse.SUPPRESS,
        help="Comma-separated addresses or ranges (e.g. 0,3-5 or all)",
    )
    parser.add_argument(
        "--outlier-mode",
        choices=sorted(_OUTLIER_MODES),
        default=argparse.SUPPRESS,
        help="Outlier mode (default: random)",
    )
    parser.add_argument(
        "--outlier-probability",
        type=float,
        default=argparse.SUPPRESS,
        help="Chance per tick per address (0-1, default: 0.05)",
    )
    parser.add_argument(
        "--outlier-magnitude",
        type=float,
        default=argparse.SUPPRESS,
        help="Magnitude for outlier spikes/drops (default: 300)",
    )
    parser.add_argument(
        "--holding-signal",
        choices=sorted(_SIGNAL_MODES),
        default=argparse.SUPPRESS,
        help="Signal pattern for holding registers (default: ramp)",
    )
    parser.add_argument(
        "--input-signal",
        choices=sorted(_SIGNAL_MODES),
        default=argparse.SUPPRESS,
        help="Signal pattern for input registers (default: sine)",
    )
    parser.add_argument(
        "--signal-amplitude",
        type=float,
        default=argparse.SUPPRESS,
        help="Amplitude for sine signals (default: 500)",
    )
    parser.add_argument(
        "--signal-offset",
        type=float,
        default=argparse.SUPPRESS,
        help="Offset for sine signals (default: 600)",
    )
    parser.add_argument(
        "--signal-noise",
        type=float,
        default=argparse.SUPPRESS,
        help="Uniform noise added to sine signals (default: 10)",
    )
    parser.add_argument(
        "--phase-step",
        type=float,
        default=argparse.SUPPRESS,
        help="Phase increment per tick (default: 0.2)",
    )
    parser.add_argument(
        "--cycle-seconds",
        type=float,
        default=argparse.SUPPRESS,
        help="Seconds per full sine cycle (derives phase-step from --period)",
    )
    parser.add_argument(
        "--phase-shift",
        type=float,
        default=argparse.SUPPRESS,
        help="Phase shift per register index (default: 0.3)",
    )
    parser.add_argument(
        "--fault-enable",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable periodic fault injection",
    )
    parser.add_argument(
        "--fault-kind",
        choices=sorted(_FAULT_KINDS),
        default=argparse.SUPPRESS,
        help="Target register kind for faults (default: input)",
    )
    parser.add_argument(
        "--fault-addresses",
        default=argparse.SUPPRESS,
        help="Comma-separated addresses or ranges (e.g. 0,3-5 or all)",
    )
    parser.add_argument(
        "--fault-mode",
        choices=sorted(_FAULT_MODES),
        default=argparse.SUPPRESS,
        help="Fault mode (default: drop)",
    )
    parser.add_argument(
        "--fault-every",
        type=float,
        default=argparse.SUPPRESS,
        help="Seconds between fault starts (default: 30)",
    )
    parser.add_argument(
        "--fault-duration",
        type=float,
        default=argparse.SUPPRESS,
        help="Seconds each fault stays active (default: 5)",
    )
    parser.add_argument(
        "--fault-magnitude",
        type=float,
        default=argparse.SUPPRESS,
        help="Magnitude for drop/spike/drift faults (default: 300)",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str] | None = None) -> None:
    options = parse_args(argv)
    count = max(1, min(200, options.register_count))
    signal_settings = SignalSettings(count=count)
    fault_settings = FaultSettings()
    outlier_settings = OutlierSettings()

    profile_name = getattr(options, "fault_profile", "none")
    if profile_name != "none":
        signal_settings, fault_settings, outlier_settings = _apply_profile(
            signal_settings, fault_settings, outlier_settings, profile_name, count
        )

    if hasattr(options, "holding_signal"):
        signal_settings = replace(
            signal_settings, holding_signal=options.holding_signal
        )
    if hasattr(options, "input_signal"):
        signal_settings = replace(signal_settings, input_signal=options.input_signal)
    if hasattr(options, "signal_amplitude"):
        signal_settings = replace(signal_settings, amplitude=options.signal_amplitude)
    if hasattr(options, "signal_offset"):
        signal_settings = replace(signal_settings, offset=options.signal_offset)
    if hasattr(options, "signal_noise"):
        signal_settings = replace(signal_settings, noise=options.signal_noise)
    if hasattr(options, "phase_step"):
        signal_settings = replace(signal_settings, phase_step=options.phase_step)
    if hasattr(options, "phase_shift"):
        signal_settings = replace(signal_settings, phase_shift=options.phase_shift)
    if hasattr(options, "cycle_seconds") and not hasattr(options, "phase_step"):
        cycle_seconds = max(0.1, options.cycle_seconds)
        period_seconds = max(0.01, options.period)
        signal_settings = replace(
            signal_settings, phase_step=(math.tau * period_seconds) / cycle_seconds
        )
    signal_settings = replace(signal_settings, count=count)

    fault_overrides_used = False
    if hasattr(options, "fault_kind"):
        fault_settings = replace(fault_settings, kind=options.fault_kind)
        fault_overrides_used = True
    if hasattr(options, "fault_addresses"):
        fault_settings = replace(
            fault_settings, addresses=_parse_addresses(options.fault_addresses, count)
        )
        fault_overrides_used = True
    if hasattr(options, "fault_mode"):
        fault_settings = replace(fault_settings, mode=options.fault_mode)
        fault_overrides_used = True
    if hasattr(options, "fault_every"):
        fault_settings = replace(fault_settings, every=max(0.1, options.fault_every))
        fault_overrides_used = True
    if hasattr(options, "fault_duration"):
        fault_settings = replace(
            fault_settings, duration=max(0.1, options.fault_duration)
        )
        fault_overrides_used = True
    if hasattr(options, "fault_magnitude"):
        fault_settings = replace(fault_settings, magnitude=options.fault_magnitude)
        fault_overrides_used = True
    if hasattr(options, "fault_enable") or (
        profile_name == "none" and fault_overrides_used
    ):
        fault_settings = replace(fault_settings, enabled=True)

    outlier_overrides_used = False
    if hasattr(options, "outlier_kind"):
        outlier_settings = replace(outlier_settings, kind=options.outlier_kind)
        outlier_overrides_used = True
    if hasattr(options, "outlier_addresses"):
        outlier_settings = replace(
            outlier_settings,
            addresses=_parse_addresses(options.outlier_addresses, count),
        )
        outlier_overrides_used = True
    if hasattr(options, "outlier_mode"):
        outlier_settings = replace(outlier_settings, mode=options.outlier_mode)
        outlier_overrides_used = True
    if hasattr(options, "outlier_probability"):
        outlier_settings = replace(
            outlier_settings,
            probability=max(0.0, min(1.0, options.outlier_probability)),
        )
        outlier_overrides_used = True
    if hasattr(options, "outlier_magnitude"):
        outlier_settings = replace(
            outlier_settings, magnitude=options.outlier_magnitude
        )
        outlier_overrides_used = True
    if hasattr(options, "outlier_enable") or outlier_overrides_used:
        outlier_settings = replace(outlier_settings, enabled=True)

    asyncio.run(
        run_simulated_server(
            options.host,
            options.port,
            options.period,
            signal_settings=signal_settings,
            fault_settings=fault_settings,
            outlier_settings=outlier_settings,
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
