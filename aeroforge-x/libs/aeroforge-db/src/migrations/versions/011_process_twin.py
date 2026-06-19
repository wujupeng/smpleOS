"""Process route templates, digital twin extensions, twin sync logs

Revision ID: 011_process_twin
Revises: 010_cae_results_bom
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_process_twin"
down_revision: Union[str, None] = "010_cae_results_bom"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "process_route_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("part_type", sa.String(100), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.add_column(
        "digital_twins",
        sa.Column("twin_payload", sa.JSON(), nullable=True),
    )

    op.create_table(
        "twin_sync_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("twin_id", sa.String(36), sa.ForeignKey("digital_twins.id"), nullable=False),
        sa.Column("sync_type", sa.String(30), nullable=False),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_twin_sync_logs_twin_id", "twin_sync_logs", ["twin_id"])
    op.create_index("ix_twin_sync_logs_status", "twin_sync_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_twin_sync_logs_status")
    op.drop_index("ix_twin_sync_logs_twin_id")
    op.drop_table("twin_sync_logs")
    op.drop_column("digital_twins", "twin_payload")
    op.drop_table("process_route_templates")