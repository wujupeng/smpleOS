"""BOM items table

Revision ID: 004_bom
Revises: 003_plm
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_bom"
down_revision: Union[str, None] = "003_plm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bom_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_code", sa.String(50), nullable=False, unique=True),
        sa.Column("bom_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("bom_items.id"), nullable=True),
        sa.Column("spec_id", sa.String(36), sa.ForeignKey("aircraft_specs.id"), nullable=True),
        sa.Column("design_object_id", sa.String(36), sa.ForeignKey("design_objects.id"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bom_items_type_parent", "bom_items", ["bom_type", "parent_id"])


def downgrade() -> None:
    op.drop_index("ix_bom_items_type_parent")
    op.drop_table("bom_items")