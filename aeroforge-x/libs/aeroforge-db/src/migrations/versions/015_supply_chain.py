"""Phase 3 migration: suppliers, purchase_orders, inventory_items tables

Revision ID: 015
Revises: 014
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("contact_person", sa.String(100)),
        sa.Column("email", sa.String(200)),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.Text()),
        sa.Column("qualification_status", sa.String(20), server_default="pending"),
        sa.Column("qualification_expiry", sa.DateTime(timezone=True)),
        sa.Column("certifications", postgresql.JSONB(), server_default="[]"),
        sa.Column("rating", sa.Float(), server_default="0.0"),
        sa.Column("lead_time_days", sa.Integer(), server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=False),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("items", postgresql.JSONB(), server_default="[]"),
        sa.Column("total_amount", sa.Float(), server_default="0.0"),
        sa.Column("currency", sa.String(3), server_default="CNY"),
        sa.Column("ordered_at", sa.DateTime(timezone=True)),
        sa.Column("expected_delivery", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("part_id", sa.String(100), nullable=False),
        sa.Column("part_name", sa.String(200)),
        sa.Column("quantity", sa.Integer(), server_default="0"),
        sa.Column("unit", sa.String(20), server_default="pcs"),
        sa.Column("location", sa.String(100)),
        sa.Column("batch_number", sa.String(100)),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), server_default="in_stock"),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inventory_items_tenant_id", "inventory_items", ["tenant_id"])
    op.create_index("ix_inventory_items_part_id", "inventory_items", ["part_id"])


def downgrade() -> None:
    op.drop_table("inventory_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")