"""CAE results and BOM extension tables (mBOM, sBOM, mapping rules)

Revision ID: 010_cae_results_bom
Revises: 009_cae_analysis
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_cae_results_bom"
down_revision: Union[str, None] = "009_cae_analysis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cae_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("model_id", sa.String(36), nullable=False),
        sa.Column("result_type", sa.String(30), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=True),
        sa.Column("file_paths", sa.JSON(), nullable=True),
        sa.Column("minio_bucket", sa.String(100), nullable=True),
        sa.Column("minio_keys", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "mbom_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ebom_item_id", sa.String(36), sa.ForeignKey("bom_items.id"), nullable=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("mbom_items.id"), nullable=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("part_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_of_measure", sa.String(20), nullable=False, server_default="ea"),
        sa.Column("manufacturing_process", sa.String(100), nullable=True),
        sa.Column("material_spec", sa.String(200), nullable=True),
        sa.Column("make_or_buy", sa.String(10), nullable=False, server_default="make"),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sbom_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mbom_item_id", sa.String(36), sa.ForeignKey("mbom_items.id"), nullable=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("sbom_items.id"), nullable=True),
        sa.Column("part_number", sa.String(100), nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("supplier_code", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("installed_assembly_id", sa.String(36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "bom_mapping_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("mapping_config", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    for table in ("cae_results", "mbom_items", "sbom_items", "bom_mapping_rules"):
        op.create_index(f"ix_{table}_id", table, ["id"])


def downgrade() -> None:
    for table in ("bom_mapping_rules", "sbom_items", "mbom_items", "cae_results"):
        op.drop_index(f"ix_{table}_id")
        op.drop_table(table)