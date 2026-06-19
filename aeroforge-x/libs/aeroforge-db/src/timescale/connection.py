from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class TimescaleSettings(BaseSettings):
    timescale_url: str = "postgresql+asyncpg://aeroforge:aeroforge_dev@localhost:5432/aeroforge_timeseries"
    pool_size: int = 5
    max_overflow: int = 10

    model_config = {"env_prefix": "TS_"}


_settings = TimescaleSettings()
_engine = create_async_engine(
    _settings.timescale_url,
    pool_size=_settings.pool_size,
    max_overflow=_settings.max_overflow,
    echo=False,
)
_async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_timescale() -> None:
    async with _engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS flight_telemetry ("
            "  time TIMESTAMPTZ NOT NULL,"
            "  aircraft_sn TEXT NOT NULL,"
            "  sensor_id TEXT NOT NULL,"
            "  metric_name TEXT NOT NULL,"
            "  metric_value DOUBLE PRECISION,"
            "  metadata JSONB DEFAULT '{}'::jsonb"
            ")"
        ))
        try:
            await conn.execute(text(
                "SELECT create_hypertable('flight_telemetry', 'time', "
                "chunk_time_interval => INTERVAL '1 day', migrate_data => true)"
            ))
        except Exception:
            pass

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ft_aircraft_time "
            "ON flight_telemetry (aircraft_sn, time DESC)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ft_sensor_time "
            "ON flight_telemetry (sensor_id, time DESC)"
        ))

        try:
            await conn.execute(text(
                "SELECT add_compression_policy('flight_telemetry', INTERVAL '7 days')"
            ))
        except Exception:
            pass

        try:
            await conn.execute(text(
                "SELECT add_retention_policy('flight_telemetry', INTERVAL '1 year')"
            ))
        except Exception:
            pass

        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS structural_health_metrics ("
            "  time TIMESTAMPTZ NOT NULL,"
            "  aircraft_sn TEXT NOT NULL,"
            "  component_id TEXT NOT NULL,"
            "  metric_name TEXT NOT NULL,"
            "  metric_value DOUBLE PRECISION,"
            "  threshold_value DOUBLE PRECISION,"
            "  status TEXT DEFAULT 'normal',"
            "  metadata JSONB DEFAULT '{}'::jsonb"
            ")"
        ))
        try:
            await conn.execute(text(
                "SELECT create_hypertable('structural_health_metrics', 'time', "
                "chunk_time_interval => INTERVAL '1 day', migrate_data => true)"
            ))
        except Exception:
            pass

        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_shm_aircraft_time "
            "ON structural_health_metrics (aircraft_sn, time DESC)"
        ))

        try:
            await conn.execute(text(
                "SELECT add_compression_policy('structural_health_metrics', INTERVAL '30 days')"
            ))
        except Exception:
            pass

        try:
            await conn.execute(text(
                "SELECT add_retention_policy('structural_health_metrics', INTERVAL '5 years')"
            ))
        except Exception:
            pass

    logger.info("TimescaleDB initialized: flight_telemetry + structural_health_metrics")


async def write_telemetry(
    table: str,
    records: list[dict[str, Any]],
) -> int:
    if not records:
        return 0

    async with get_session() as session:
        if table == "flight_telemetry":
            for rec in records:
                await session.execute(text(
                    "INSERT INTO flight_telemetry (time, aircraft_sn, sensor_id, metric_name, metric_value, metadata) "
                    "VALUES (:time, :aircraft_sn, :sensor_id, :metric_name, :metric_value, :metadata)"
                ), {
                    "time": rec.get("time", datetime.now(timezone.utc)),
                    "aircraft_sn": rec.get("aircraft_sn", ""),
                    "sensor_id": rec.get("sensor_id", ""),
                    "metric_name": rec.get("metric_name", ""),
                    "metric_value": rec.get("metric_value", 0.0),
                    "metadata": rec.get("metadata", {}),
                })
        elif table == "structural_health_metrics":
            for rec in records:
                await session.execute(text(
                    "INSERT INTO structural_health_metrics "
                    "(time, aircraft_sn, component_id, metric_name, metric_value, threshold_value, status, metadata) "
                    "VALUES (:time, :aircraft_sn, :component_id, :metric_name, :metric_value, :threshold_value, :status, :metadata)"
                ), {
                    "time": rec.get("time", datetime.now(timezone.utc)),
                    "aircraft_sn": rec.get("aircraft_sn", ""),
                    "component_id": rec.get("component_id", ""),
                    "metric_name": rec.get("metric_name", ""),
                    "metric_value": rec.get("metric_value", 0.0),
                    "threshold_value": rec.get("threshold_value", 0.0),
                    "status": rec.get("status", "normal"),
                    "metadata": rec.get("metadata", {}),
                })

    logger.info("Wrote %d records to %s", len(records), table)
    return len(records)


async def query_telemetry(
    table: str,
    aircraft_sn: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    metric_name: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    async with get_session() as session:
        if table == "flight_telemetry":
            query = "SELECT time, aircraft_sn, sensor_id, metric_name, metric_value, metadata FROM flight_telemetry WHERE aircraft_sn = :sn"
            params: dict[str, Any] = {"sn": aircraft_sn}
            if start_time:
                query += " AND time >= :start"
                params["start"] = start_time
            if end_time:
                query += " AND time <= :end"
                params["end"] = end_time
            if metric_name:
                query += " AND metric_name = :metric"
                params["metric"] = metric_name
            query += " ORDER BY time DESC LIMIT :lim"
            params["lim"] = limit

            result = await session.execute(text(query), params)
            rows = result.fetchall()
            return [
                {
                    "time": str(row[0]),
                    "aircraft_sn": row[1],
                    "sensor_id": row[2],
                    "metric_name": row[3],
                    "metric_value": row[4],
                    "metadata": row[5],
                }
                for row in rows
            ]

        elif table == "structural_health_metrics":
            query = (
                "SELECT time, aircraft_sn, component_id, metric_name, metric_value, threshold_value, status, metadata "
                "FROM structural_health_metrics WHERE aircraft_sn = :sn"
            )
            params = {"sn": aircraft_sn}
            if start_time:
                query += " AND time >= :start"
                params["start"] = start_time
            if end_time:
                query += " AND time <= :end"
                params["end"] = end_time
            if metric_name:
                query += " AND metric_name = :metric"
                params["metric"] = metric_name
            query += " ORDER BY time DESC LIMIT :lim"
            params["lim"] = limit

            result = await session.execute(text(query), params)
            rows = result.fetchall()
            return [
                {
                    "time": str(row[0]),
                    "aircraft_sn": row[1],
                    "component_id": row[2],
                    "metric_name": row[3],
                    "metric_value": row[4],
                    "threshold_value": row[5],
                    "status": row[6],
                    "metadata": row[7],
                }
                for row in rows
            ]

    return []


async def aggregate_telemetry(
    table: str,
    aircraft_sn: str,
    metric_name: str,
    start_time: datetime,
    end_time: datetime,
    aggregation: str = "avg",
) -> dict[str, Any]:
    if aggregation not in ("avg", "max", "min", "count"):
        aggregation = "avg"

    async with get_session() as session:
        if table == "flight_telemetry":
            query = (
                f"SELECT {aggregation}(metric_value) as agg_val, "
                f"min(metric_value) as min_val, max(metric_value) as max_val, "
                f"count(*) as count_val "
                f"FROM flight_telemetry "
                f"WHERE aircraft_sn = :sn AND metric_name = :metric "
                f"AND time >= :start AND time <= :end"
            )
            result = await session.execute(text(query), {
                "sn": aircraft_sn,
                "metric": metric_name,
                "start": start_time,
                "end": end_time,
            })
            row = result.fetchone()
            if row:
                return {
                    "aircraft_sn": aircraft_sn,
                    "metric_name": metric_name,
                    "aggregation": aggregation,
                    "value": float(row[0]) if row[0] is not None else None,
                    "min": float(row[1]) if row[1] is not None else None,
                    "max": float(row[2]) if row[2] is not None else None,
                    "count": int(row[3]),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                }

    return {
        "aircraft_sn": aircraft_sn,
        "metric_name": metric_name,
        "aggregation": aggregation,
        "value": None,
        "count": 0,
    }


async def close_timescale() -> None:
    await _engine.dispose()
