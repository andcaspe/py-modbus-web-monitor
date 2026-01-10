"""FastAPI application and routes."""

from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .data_logger import compute_z_score, get_data_logger, utc_now_iso
from .modbus_client import ModbusConnectionError, ModbusOperationError, tcp_session
from .monitor import run_monitor_session
from .schemas import (
    AnomalyRequest,
    MonitorCommand,
    MonitorConfig,
    ReadRequest,
    WriteRequest,
)

logger = logging.getLogger(__name__)
try:  # pragma: no cover - optional dependency
    from statsmodels.tsa.seasonal import STL
except Exception:  # noqa: BLE001 - best effort import
    STL = None


def _resolve_dist_dir() -> Path | None:
    package_dist = Path(__file__).resolve().parent / "web"
    if (package_dist / "index.html").exists():
        return package_dist

    project_root = Path(__file__).resolve().parents[2]
    dist_dir = project_root / "frontend" / "dist"
    if dist_dir.exists():
        return dist_dir
    return None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Modbus Web Monitor",
        version=__version__,
        description="Monitor Modbus devices with FastAPI + websockets",
    )
    router = APIRouter(prefix="/api")

    @router.post("/modbus/read")
    async def read_modbus(payload: ReadRequest) -> Dict[str, List[dict]]:
        try:
            async with tcp_session(payload.connection) as session:
                readings = []
                for target in payload.targets:
                    values = await session.read(target)
                    readings.append(
                        {
                            "address": target.address,
                            "kind": target.kind,
                            "label": target.label or f"{target.kind}:{target.address}",
                            "values": values,
                        }
                    )
            data_logger = get_data_logger()
            await data_logger.log_readings(
                payload.connection,
                readings,
                source="read",
                timestamp=utc_now_iso(),
            )
            return {"data": readings}
        except (ModbusConnectionError, ModbusOperationError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @router.post("/modbus/write")
    async def write_modbus(payload: WriteRequest) -> Dict[str, str | int]:
        try:
            async with tcp_session(payload.connection) as session:
                for op in payload.writes:
                    await session.write(op)
            return {"status": "ok", "writes": len(payload.writes)}
        except (ModbusConnectionError, ModbusOperationError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    def _autocorr(values: List[float], lag: int) -> float:
        size = len(values) - lag
        if size <= 1:
            return 0.0
        mean = sum(values) / len(values)
        denom = sum((value - mean) ** 2 for value in values)
        if denom == 0:
            return 0.0
        num = sum((values[i] - mean) * (values[i + lag] - mean) for i in range(size))
        return num / denom

    def _estimate_period(values: List[float], max_lag: int) -> int:
        if len(values) < 4:
            return 2
        max_lag = max(1, min(max_lag, len(values) - 2))
        best_lag = 1
        best_corr = float("-inf")
        for lag in range(1, max_lag + 1):
            corr = _autocorr(values, lag)
            if corr > best_corr:
                best_corr = corr
                best_lag = lag
        return max(2, best_lag)

    @router.post("/anomaly/zscore")
    async def anomaly_zscore(payload: AnomalyRequest) -> Dict[str, List[dict]]:
        data_logger = get_data_logger()
        results: List[dict] = []
        for target in payload.targets:
            latest_values: List[float | None] = []
            z_scores: List[float | None] = []
            sample_counts: List[int] = []
            means: List[float | None] = []
            stdevs: List[float | None] = []
            for offset in range(target.count):
                address = target.address + offset
                values = await data_logger.fetch_recent_values(
                    payload.connection,
                    kind=target.kind,
                    address=address,
                    limit=payload.window,
                )
                if not values:
                    latest_values.append(None)
                    z_scores.append(None)
                    sample_counts.append(0)
                    means.append(None)
                    stdevs.append(None)
                    continue
                latest_values.append(values[0])
                sample_counts.append(len(values))
                z_score, mean, stdev = compute_z_score(values, payload.min_samples)
                z_scores.append(z_score)
                means.append(mean)
                stdevs.append(stdev)
            results.append(
                {
                    "address": target.address,
                    "kind": target.kind,
                    "label": target.label or f"{target.kind}:{target.address}",
                    "values": latest_values,
                    "z_scores": z_scores,
                    "sample_counts": sample_counts,
                    "mean": means,
                    "stdev": stdevs,
                }
            )
        return {"data": results}

    @router.post("/anomaly/stl")
    async def anomaly_stl(payload: AnomalyRequest) -> Dict[str, List[dict]]:
        if STL is None:
            raise HTTPException(
                status_code=503,
                detail="STL requires statsmodels. Install modbus-web-monitor[ml].",
            )
        data_logger = get_data_logger()
        results: List[dict] = []
        for target in payload.targets:
            latest_values: List[float | None] = []
            z_scores: List[float | None] = []
            sample_counts: List[int] = []
            means: List[float | None] = []
            stdevs: List[float | None] = []
            for offset in range(target.count):
                address = target.address + offset
                values = await data_logger.fetch_recent_values(
                    payload.connection,
                    kind=target.kind,
                    address=address,
                    limit=payload.window,
                )
                values = list(reversed(values))
                if not values:
                    latest_values.append(None)
                    z_scores.append(None)
                    sample_counts.append(0)
                    means.append(None)
                    stdevs.append(None)
                    continue
                latest_values.append(values[-1])
                sample_counts.append(len(values))
                if len(values) < payload.min_samples:
                    z_scores.append(None)
                    means.append(None)
                    stdevs.append(None)
                    continue
                period = _estimate_period(values, max_lag=min(100, len(values) - 2))
                try:
                    stl = STL(values, period=period, robust=True)
                    result = stl.fit()
                except Exception as exc:  # noqa: BLE001 - return partial results
                    logger.warning(
                        "STL failed for %s:%s: %s", target.kind, address, exc
                    )
                    z_scores.append(None)
                    means.append(None)
                    stdevs.append(None)
                    continue
                residuals = list(result.resid)
                if len(residuals) < 2:
                    z_scores.append(None)
                    means.append(None)
                    stdevs.append(None)
                    continue
                history = residuals[:-1]
                if len(history) < 2:
                    z_scores.append(None)
                    means.append(None)
                    stdevs.append(None)
                    continue
                mean = statistics.mean(history)
                stdev = statistics.stdev(history)
                if stdev == 0:
                    z_score = 0.0
                else:
                    z_score = (residuals[-1] - mean) / stdev
                z_scores.append(z_score)
                means.append(mean)
                stdevs.append(stdev)
            results.append(
                {
                    "address": target.address,
                    "kind": target.kind,
                    "label": target.label or f"{target.kind}:{target.address}",
                    "values": latest_values,
                    "z_scores": z_scores,
                    "sample_counts": sample_counts,
                    "mean": means,
                    "stdev": stdevs,
                }
            )
        return {"data": results}

    app.include_router(router)

    # Permissive CORS for local dev; tighten in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    dist_dir = _resolve_dist_dir()
    if dist_dir:
        app.mount("/app", StaticFiles(directory=dist_dir, html=True), name="frontend")

    return app


app = create_app()


@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)
        command = MonitorCommand.model_validate(data)
        if command.type != "configure":
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "First message must be a 'configure' command",
                }
            )
            await websocket.close()
            return
        assert command.connection is not None
        config = MonitorConfig(
            connection=command.connection,
            interval=command.interval or 1.0,
            targets=command.targets or [],
        )
        logger.info(
            "WebSocket configure: host=%s port=%s unit=%s targets=%d interval=%.3f",
            config.connection.host,
            config.connection.port,
            config.connection.unit_id,
            len(config.targets),
            config.interval,
        )
        await websocket.send_json(
            {
                "type": "status",
                "message": f"Config set for {config.connection.host}:{config.connection.port} (unit {config.connection.unit_id})",
            }
        )
    except Exception as exc:  # noqa: BLE001 - send details to client
        await websocket.send_json(
            {"type": "error", "message": f"Invalid configuration: {exc}"}
        )
        await websocket.close()
        return

    try:
        await run_monitor_session(websocket, config)
    except WebSocketDisconnect:
        return
