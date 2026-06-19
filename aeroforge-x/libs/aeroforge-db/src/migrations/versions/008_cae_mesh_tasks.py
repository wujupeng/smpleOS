"""CAE mesh tasks table

Revision ID: 008_cae_mesh
Revises: 007_reserved
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_cae_mesh"
down_revision: Union[str, None] = "007_reserved"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cae_mesh_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("mesh_type", sa.String(20), nullable=False),
        sa.Column("target_element_size", sa.Float(), nullable=False, server_default=sa.text("0.01")),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("element_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_path", sa.String(500), nullable=True),
        sa.Column("quality_metrics", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_cae_mesh_tasks_model_id", "cae_mesh_tasks", ["model_id"])
    op.create_index("ix_cae_mesh_tasks_status", "cae_mesh_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cae_mesh_tasks_status")
    op.drop_index("ix_cae_mesh_tasks_model_id")
    op.drop_table("cae_mesh_tasks")