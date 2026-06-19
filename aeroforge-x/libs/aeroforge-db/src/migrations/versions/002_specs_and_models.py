"""aircraft_specs and param_models

Revision ID: 002_specs_models
Revises: 001_initial
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_specs_models"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aircraft_specs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("spec_code", sa.String(50), nullable=False, unique=True),
        sa.Column("aircraft_type", sa.String(50), nullable=False),
        sa.Column("payload_kg", sa.Float(), nullable=False),
        sa.Column("range_km", sa.Float(), nullable=False),
        sa.Column("cruise_speed_kmh", sa.Float(), nullable=False),
        sa.Column("takeoff_distance_m", sa.Float(), nullable=False),
        sa.Column("power_type", sa.String(50), nullable=False),
        sa.Column("budget_cny", sa.Float(), nullable=True),
        sa.Column("material_id", sa.String(36), sa.ForeignKey("materials.id"), nullable=True),
        sa.Column("certification_level_id", sa.String(36), sa.ForeignKey("certification_levels.id"), nullable=True),
        sa.Column("derived_constraints", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "param_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("spec_id", sa.String(36), sa.ForeignKey("aircraft_specs.id"), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("model_file_key", sa.String(500), nullable=True),
        sa.Column("model_file_bucket", sa.String(100), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("param_models")
    op.drop_table("aircraft_specs")