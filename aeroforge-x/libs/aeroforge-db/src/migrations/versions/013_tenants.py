"""Phase 3 migration: tenants, tenant_quotas, tenant_users tables

Revision ID: 013
Revises: 012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("features", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("expired_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "tenant_quotas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("max_projects", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_storage_gb", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("current_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_projects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_storage_gb", sa.Float(), nullable=False, server_default="0.0"),
    )

    op.create_table(
        "tenant_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])
    op.create_index("ix_tenant_users_user_id", "tenant_users", ["user_id"])
    op.create_unique_constraint("uq_tenant_users_tenant_user", "tenant_users", ["tenant_id", "user_id"])


def downgrade() -> None:
    op.drop_table("tenant_users")
    op.drop_table("tenant_quotas")
    op.drop_table("tenants")