"""MES tables - process_routes, process_steps, work_orders, stations, serial_numbers

Revision ID: 005_mes
Revises: 004_bom
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_mes"
down_revision: Union[str, None] = "004_bom"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("equipment", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("current_task", sa.String(200), nullable=True),
        sa.Column("operators", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "process_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("route_code", sa.String(50), nullable=False, unique=True),
        sa.Column("bom_item_id", sa.String(36), sa.ForeignKey("bom_items.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "process_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("route_id", sa.String(36), sa.ForeignKey("process_routes.id"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("station_id", sa.String(36), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("estimated_duration_min", sa.Integer(), nullable=True),
        sa.Column("required_tools", sa.JSON(), nullable=True),
        sa.Column("quality_check_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_process_steps_route_order", "process_steps", ["route_id", "step_order"], unique=True)

    op.create_table(
        "work_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_code", sa.String(50), nullable=False, unique=True),
        sa.Column("product_model", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("route_id", sa.String(36), sa.ForeignKey("process_routes.id"), nullable=True),
        sa.Column("station_id", sa.String(36), sa.ForeignKey("stations.id"), nullable=True),
        sa.Column("planned_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "serial_numbers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("serial_number", sa.String(50), nullable=False, unique=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("batch_number", sa.String(50), nullable=True),
        sa.Column("supplier", sa.String(200), nullable=True),
        sa.Column("work_order_id", sa.String(36), sa.ForeignKey("work_orders.id"), nullable=True),
        sa.Column("manufacturing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("installation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("installer", sa.String(100), nullable=True),
        sa.Column("flight_hours", sa.Float(), nullable=True, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_stock"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("serial_numbers")
    op.drop_table("work_orders")
    op.drop_index("ix_process_steps_route_order")
    op.drop_table("process_steps")
    op.drop_table("process_routes")
    op.drop_table("stations")