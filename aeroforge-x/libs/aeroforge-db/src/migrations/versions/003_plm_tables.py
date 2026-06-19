"""PLM tables - design_objects, object_versions, baselines, baseline_objects

Revision ID: 003_plm
Revises: 002_specs_models
Create Date: 2026-06-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_plm"
down_revision: Union[str, None] = "002_specs_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "design_objects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("object_code", sa.String(50), nullable=False, unique=True),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("spec_id", sa.String(36), sa.ForeignKey("aircraft_specs.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "object_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("object_id", sa.String(36), sa.ForeignKey("design_objects.id"), nullable=False),
        sa.Column("major", sa.Integer(), nullable=False),
        sa.Column("minor", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_object_versions_object_major_minor", "object_versions", ["object_id", "major", "minor"], unique=True)

    op.create_table(
        "baselines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("baseline_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "baseline_objects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("baseline_id", sa.String(36), sa.ForeignKey("baselines.id"), nullable=False),
        sa.Column("object_version_id", sa.String(36), sa.ForeignKey("object_versions.id"), nullable=False),
    )
    op.create_index("ix_baseline_objects_unique", "baseline_objects", ["baseline_id", "object_version_id"], unique=True)


def downgrade() -> None:
    op.drop_table("baseline_objects")
    op.drop_table("baselines")
    op.drop_index("ix_object_versions_object_major_minor")
    op.drop_table("object_versions")
    op.drop_table("design_objects")