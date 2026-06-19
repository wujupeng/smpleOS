"""Phase 3 migration: projects, project_members tables

Revision ID: 014
Revises: 013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aircraft_type", sa.String(30), nullable=False, server_default="fixed_wing"),
        sa.Column("status", sa.String(20), nullable=False, server_default="planning"),
        sa.Column("spec_id", sa.String(36)),
        sa.Column("current_baseline_id", sa.String(36)),
        sa.Column("settings", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.create_unique_constraint("uq_projects_tenant_code", "projects", ["tenant_id", "code"])

    op.create_table(
        "project_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_unique_constraint("uq_project_members_project_user", "project_members", ["project_id", "user_id"])


def downgrade() -> None:
    op.drop_table("project_members")
    op.drop_table("projects")