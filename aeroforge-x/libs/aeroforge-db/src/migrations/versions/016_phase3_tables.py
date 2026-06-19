"""Phase 3 migration: spc_control_charts, spc_measurements, production_schedules, schedule_constraints, ai_proposals, optimization_tasks, reports, report_instances, i18n_translations, audit_logs extension

Revision ID: 016
Revises: 015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spc_control_charts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("chart_name", sa.String(200), nullable=False),
        sa.Column("characteristic", sa.String(100), nullable=False),
        sa.Column("chart_type", sa.String(20), server_default="xbar_r"),
        sa.Column("ucl", sa.Float()),
        sa.Column("lcl", sa.Float()),
        sa.Column("cl", sa.Float()),
        sa.Column("sample_size", sa.Integer(), server_default="5"),
        sa.Column("specification_usl", sa.Float()),
        sa.Column("specification_lsl", sa.Float()),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_spc_charts_tenant_id", "spc_control_charts", ["tenant_id"])

    op.create_table(
        "spc_measurements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chart_id", sa.String(36), sa.ForeignKey("spc_control_charts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sample_number", sa.Integer(), nullable=False),
        sa.Column("values", postgresql.JSONB(), server_default="[]"),
        sa.Column("mean", sa.Float()),
        sa.Column("range", sa.Float()),
        sa.Column("is_out_of_control", sa.Boolean(), server_default="false"),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("measured_by", sa.String(36)),
    )
    op.create_index("ix_spc_measurements_chart_id", "spc_measurements", ["chart_id"])

    op.create_table(
        "production_schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("schedule_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("start_date", sa.DateTime(timezone=True)),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("items", postgresql.JSONB(), server_default="[]"),
        sa.Column("optimization_score", sa.Float()),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_production_schedules_tenant_id", "production_schedules", ["tenant_id"])

    op.create_table(
        "schedule_constraints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("schedule_id", sa.String(36), sa.ForeignKey("production_schedules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("constraint_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}"),
        sa.Column("priority", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "ai_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), server_default="pending_review"),
        sa.Column("natural_language_input", sa.Text()),
        sa.Column("parsed_spec", postgresql.JSONB(), server_default="{}"),
        sa.Column("generated_model_ref", sa.String(200)),
        sa.Column("feasibility_report", postgresql.JSONB(), server_default="{}"),
        sa.Column("risk_markers", postgresql.JSONB(), server_default="[]"),
        sa.Column("iteration_history", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ai_proposals_tenant_id", "ai_proposals", ["tenant_id"])

    op.create_table(
        "optimization_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("task_type", sa.String(30), server_default="multi_objective"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("objectives", postgresql.JSONB(), server_default="[]"),
        sa.Column("constraints", postgresql.JSONB(), server_default="{}"),
        sa.Column("results", postgresql.JSONB(), server_default="{}"),
        sa.Column("pareto_front", postgresql.JSONB(), server_default="[]"),
        sa.Column("topology_result", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_optimization_tasks_tenant_id", "optimization_tasks", ["tenant_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("template_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("schedule", sa.String(20), server_default="on_demand"),
        sa.Column("created_by", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_reports_tenant_id", "reports", ["tenant_id"])

    op.create_table(
        "report_instances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), server_default="generated"),
        sa.Column("data", postgresql.JSONB(), server_default="{}"),
        sa.Column("file_ref", sa.String(500)),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "i18n_translations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("locale", sa.String(10), nullable=False),
        sa.Column("namespace", sa.String(100), nullable=False, server_default="common"),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_i18n_locale_ns", "i18n_translations", ["locale", "namespace"])
    op.create_unique_constraint("uq_i18n_locale_ns_key", "i18n_translations", ["locale", "namespace", "key"])

    op.add_column("audit_logs", sa.Column("tenant_id", sa.String(36), nullable=True))
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_id", "audit_logs")
    op.drop_column("audit_logs", "tenant_id")

    op.drop_table("i18n_translations")
    op.drop_table("report_instances")
    op.drop_table("reports")
    op.drop_table("optimization_tasks")
    op.drop_table("ai_proposals")
    op.drop_table("schedule_constraints")
    op.drop_table("production_schedules")
    op.drop_table("spc_measurements")
    op.drop_table("spc_control_charts")