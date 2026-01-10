"""SQLite logging and basic anomaly scoring for Modbus readings."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import statistics
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .schemas import ConnectionSettings

logger = logging.getLogger(__name__)

_ALLOWED_KINDS = {"holding", "input", "coil", "discrete"}
_DEFAULT_KINDS = {"holding", "input"}
_DEFAULT_DB_NAME = "modbus_readings_{date}.sqlite"
_DATE_FORMAT = "%Y-%m-%d_%H-%M-%S"


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _parse_kinds(raw: str | None) -> set[str]:
    if not raw:
        return set(_DEFAULT_KINDS)
    value = raw.strip().lower()
    if not value:
        return set(_DEFAULT_KINDS)
    if value == "all":
        return set(_ALLOWED_KINDS)
    kinds = {chunk.strip().lower() for chunk in value.split(",") if chunk.strip()}
    resolved = {kind for kind in kinds if kind in _ALLOWED_KINDS}
    return resolved or set(_DEFAULT_KINDS)


def _resolve_db_path() -> Path:
    date_stamp = datetime.now().strftime(_DATE_FORMAT)
    filename = _DEFAULT_DB_NAME.format(date=date_stamp)
    return Path.cwd() / "outputs" / filename


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_z_score(
    values: Sequence[float], min_samples: int
) -> tuple[float | None, float | None, float | None]:
    if len(values) < min_samples:
        return None, None, None
    if len(values) < 3:
        return None, None, None
    history = values[1:]
    if len(history) < 2:
        return None, None, None
    mean = statistics.mean(history)
    stdev = statistics.stdev(history)
    if stdev == 0:
        return 0.0, mean, stdev
    return (values[0] - mean) / stdev, mean, stdev


@dataclass(frozen=True)
class LoggedReading:
    timestamp: str
    source: str
    host: str
    port: int
    unit_id: int
    kind: str
    address: int
    value: float
    label: str | None


class SQLiteDataLogger:
    def __init__(self, db_path: Path, kinds: Iterable[str], enabled: bool) -> None:
        self.db_path = db_path
        self.kinds = {kind for kind in kinds if kind in _ALLOWED_KINDS}
        self.enabled = enabled
        self._initialized = False
        self._init_lock = threading.Lock()

    async def log_readings(
        self,
        connection: ConnectionSettings,
        readings: Sequence[dict],
        *,
        source: str,
        timestamp: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        if not readings:
            return
        timestamp = timestamp or utc_now_iso()
        records: list[LoggedReading] = []
        for reading in readings:
            kind = reading.get("kind")
            if kind not in self.kinds:
                continue
            base_address = int(reading.get("address", 0))
            label = reading.get("label")
            values = reading.get("values") or []
            for offset, value in enumerate(values):
                records.append(
                    LoggedReading(
                        timestamp=timestamp,
                        source=source,
                        host=connection.host,
                        port=connection.port,
                        unit_id=connection.unit_id,
                        kind=kind,
                        address=base_address + offset,
                        value=float(value),
                        label=label,
                    )
                )
        if not records:
            return
        try:
            await asyncio.to_thread(self._write_records, records)
        except Exception as exc:  # noqa: BLE001 - logging should never break flow
            logger.warning("Data logger failed: %s", exc)

    async def fetch_recent_values(
        self,
        connection: ConnectionSettings,
        *,
        kind: str,
        address: int,
        limit: int,
    ) -> list[float]:
        if not self.enabled:
            return []
        try:
            return await asyncio.to_thread(
                self._fetch_recent_values_sync,
                connection,
                kind,
                address,
                limit,
            )
        except Exception as exc:  # noqa: BLE001 - treat logging issues as non-fatal
            logger.warning("Data logger query failed: %s", exc)
            return []

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        source TEXT NOT NULL,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        unit_id INTEGER NOT NULL,
                        kind TEXT NOT NULL,
                        address INTEGER NOT NULL,
                        value REAL NOT NULL,
                        label TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_readings_series
                    ON readings (host, port, unit_id, kind, address, timestamp)
                    """
                )
                conn.commit()
            finally:
                conn.close()
            self._initialized = True

    def _write_records(self, records: Sequence[LoggedReading]) -> None:
        self._ensure_initialized()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO readings (
                    timestamp, source, host, port, unit_id, kind, address, value, label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.timestamp,
                        record.source,
                        record.host,
                        record.port,
                        record.unit_id,
                        record.kind,
                        record.address,
                        record.value,
                        record.label,
                    )
                    for record in records
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def _fetch_recent_values_sync(
        self,
        connection: ConnectionSettings,
        kind: str,
        address: int,
        limit: int,
    ) -> list[float]:
        self._ensure_initialized()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT value
                FROM readings
                WHERE host = ? AND port = ? AND unit_id = ? AND kind = ? AND address = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (
                    connection.host,
                    connection.port,
                    connection.unit_id,
                    kind,
                    address,
                    limit,
                ),
            )
            rows = cursor.fetchall()
            return [float(row[0]) for row in rows]
        finally:
            conn.close()


_DATA_LOGGER: SQLiteDataLogger | None = None


def _build_data_logger() -> SQLiteDataLogger:
    enabled = _parse_bool(os.getenv("MODBUS_WEB_MONITOR_LOG_ENABLED"), True)
    kinds = _parse_kinds(os.getenv("MODBUS_WEB_MONITOR_LOG_KINDS"))
    db_path = _resolve_db_path()
    return SQLiteDataLogger(db_path=db_path, kinds=kinds, enabled=enabled)


def get_data_logger() -> SQLiteDataLogger:
    global _DATA_LOGGER
    if _DATA_LOGGER is None:
        _DATA_LOGGER = _build_data_logger()
    return _DATA_LOGGER


def reset_data_logger() -> SQLiteDataLogger:
    global _DATA_LOGGER
    _DATA_LOGGER = _build_data_logger()
    return _DATA_LOGGER
