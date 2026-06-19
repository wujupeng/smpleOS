"""TimescaleDB hypertables for flight telemetry and structural health

Revision ID: 012_timeseries
Revises: 011_process_twin
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_timeseries"
down_revision: Union[str, None] = "011_process_twin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flight_telemetry",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aircraft_id", sa.String(36), nullable=False),
        sa.Column("altitude_m", sa.Float(), nullable=True),
        sa.Column("speed_kmh", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("vertical_speed_ms", sa.Float(), nullable=True),
        sa.Column("g_force", sa.Float(), nullable=True),
        sa.Column("engine_rpm", sa.Float(), nullable=True),
        sa.Column("fuel_flow_kgh", sa.Float(), nullable=True),
        sa.Column("outside_temp_c", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    op.execute(
        "SELECT create_hypertable('flight_telemetry', 'time', "
        "if_not_exists => TRUE);"
    )

    op.create_index(
        "ix_flight_telemetry_aircraft_time",
        "flight_telemetry",
        ["aircraft_id", "time"],
    )

    op.create_table(
        "structural_health_metrics",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aircraft_id", sa.String(36), nullable=False),
        sa.Column("sensor_id", sa.String(100), nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("strain_microepsilon", sa.Float(), nullable=True),
        sa.Column("stress_mpa", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("vibration_hz", sa.Float(), nullable=True),
        sa.Column("fatigue_cycles", sa.Integer(), nullable=True),
        sa.Column("health_index", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )

    op.execute(
        "SELECT create_hypertable('structural_health_metrics', 'time', "
        "if_not_exists => TRUE);"
    )

    op.create_index(
        "ix_structural_health_aircraft_sensor_time",
        "structural_health_metrics",
        ["aircraft_id", "sensor_id", "time"],
    )


def downgrade() -> None:
    op.drop_index("ix_structural_health_aircraft_sensor_time")
    op.drop_table("structural_health_metrics")
    op.drop_index("ix_flight_telemetry_aircraft_time")
    op.drop_table("flight_telemetry")