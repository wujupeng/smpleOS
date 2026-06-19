"""CAE analysis tasks tables (CFD, FEA, flutter, thermal, multiphysics)

Revision ID: 009_cae_analysis
Revises: 008_cae_mesh
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_cae_analysis"
down_revision: Union[str, None] = "008_cae_mesh"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cae_cfd_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_task_id", sa.String(36), nullable=True),
        sa.Column("analysis_type", sa.String(20), nullable=False, server_default="steady"),
        sa.Column("solver_type", sa.String(30), nullable=False, server_default="simpleFoam"),
        sa.Column("turbulence_model", sa.String(30), nullable=False, server_default="kOmegaSST"),
        sa.Column("flight_conditions", sa.JSON(), nullable=True),
        sa.Column("openfoam_params", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cae_fea_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_task_id", sa.String(36), nullable=True),
        sa.Column("problem_type", sa.String(30), nullable=False, server_default="linear_elasticity"),
        sa.Column("fenics_params", sa.JSON(), nullable=True),
        sa.Column("boundary_conditions", sa.JSON(), nullable=True),
        sa.Column("loads", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cae_flutter_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_task_id", sa.String(36), nullable=True),
        sa.Column("n_modes", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("speed_range", sa.JSON(), nullable=True),
        sa.Column("p_k_method", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cae_thermal_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_task_id", sa.String(36), nullable=True),
        sa.Column("analysis_type", sa.String(20), nullable=False, server_default="steady_state"),
        sa.Column("thermal_params", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cae_multiphysics_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_task_id", sa.String(36), nullable=True),
        sa.Column("coupling_type", sa.String(20), nullable=False, server_default="weak"),
        sa.Column("coupling_iterations", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("physics_config", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    for table in ("cae_cfd_tasks", "cae_fea_tasks", "cae_flutter_tasks",
                   "cae_thermal_tasks", "cae_multiphysics_tasks"):
        op.create_index(f"ix_{table}_model_id", table, ["model_id"])
        op.create_index(f"ix_{table}_status", table, ["status"])


def downgrade() -> None:
    for table in ("cae_multiphysics_tasks", "cae_thermal_tasks", "cae_flutter_tasks",
                   "cae_fea_tasks", "cae_cfd_tasks"):
        op.drop_index(f"ix_{table}_status")
        op.drop_index(f"ix_{table}_model_id")
        op.drop_table(table)