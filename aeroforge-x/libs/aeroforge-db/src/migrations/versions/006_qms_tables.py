"""QMS tables - inspection_plans, inspection_records, capas

Revision ID: 006_qms
Revises: 005_mes
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_qms"
down_revision: Union[str, None] = "005_mes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inspection_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_code", sa.String(50), nullable=False, unique=True),
        sa.Column("inspection_type", sa.String(20), nullable=False),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("work_order_id", sa.String(36), sa.ForeignKey("work_orders.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "inspection_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("record_code", sa.String(50), nullable=False, unique=True),
        sa.Column("inspection_type", sa.String(20), nullable=False),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("inspection_plans.id"), nullable=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("inspector", sa.String(100), nullable=False),
        sa.Column("inspection_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=True),
        sa.Column("measurements", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "capas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("capa_code", sa.String(50), nullable=False, unique=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("preventive_action", sa.Text(), nullable=True),
        sa.Column("verification_result", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("inspection_record_id", sa.String(36), sa.ForeignKey("inspection_records.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("capas")
    op.drop_table("inspection_records")
    op.drop_table("inspection_plans")