from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.entities.workflow_definition import WorkflowDefinition, WorkflowNode, WorkflowEdge, ParameterMapping
from src.domain.enums import ConnectionType, DefinitionStatus, NodeType


PREDEFINED_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "DesignVerificationWorkflow",
        "nodes": [
            {"node_id": "dv-1", "type": "Task", "name": "Requirement Parsing", "handler": "requirement.parse"},
            {"node_id": "dv-2", "type": "Task", "name": "Design Generation", "handler": "ai.aerogpt_designer"},
            {"node_id": "dv-3", "type": "Task", "name": "Rule Check", "handler": "design.rule_check"},
            {"node_id": "dv-4", "type": "Task", "name": "CAE Analysis", "handler": "verification.cfd_analysis"},
            {"node_id": "dv-5", "type": "Task", "name": "Review", "handler": "human.review"},
        ],
        "edges": [
            {"edge_id": "dv-e1", "source_id": "dv-1", "target_id": "dv-2", "connection_type": "Sequence"},
            {"edge_id": "dv-e2", "source_id": "dv-2", "target_id": "dv-3", "connection_type": "Sequence"},
            {"edge_id": "dv-e3", "source_id": "dv-3", "target_id": "dv-4", "connection_type": "Sequence"},
            {"edge_id": "dv-e4", "source_id": "dv-4", "target_id": "dv-5", "connection_type": "Sequence"},
        ],
        "trigger_event": "design.baseline.frozen",
    },
    {
        "name": "ManufacturingExecutionWorkflow",
        "nodes": [
            {"node_id": "me-1", "type": "Task", "name": "EBOM Parsing", "handler": "bom.parse_ebom"},
            {"node_id": "me-2", "type": "Task", "name": "MBOM Transform", "handler": "manufacturing.mbom_transform"},
            {"node_id": "me-3", "type": "Task", "name": "Process Route", "handler": "manufacturing.process_route"},
            {"node_id": "me-4", "type": "Task", "name": "Work Order Generate", "handler": "manufacturing.work_order_generate"},
            {"node_id": "me-5", "type": "Task", "name": "Traveler", "handler": "manufacturing.traveler"},
            {"node_id": "me-6", "type": "Task", "name": "NDT Inspection", "handler": "quality.inspection"},
            {"node_id": "me-7", "type": "Task", "name": "Delivery", "handler": "delivery.create"},
        ],
        "edges": [
            {"edge_id": "me-e1", "source_id": "me-1", "target_id": "me-2", "connection_type": "Sequence"},
            {"edge_id": "me-e2", "source_id": "me-2", "target_id": "me-3", "connection_type": "Sequence"},
            {"edge_id": "me-e3", "source_id": "me-3", "target_id": "me-4", "connection_type": "Sequence"},
            {"edge_id": "me-e4", "source_id": "me-4", "target_id": "me-5", "connection_type": "Sequence"},
            {"edge_id": "me-e5", "source_id": "me-5", "target_id": "me-6", "connection_type": "Sequence"},
            {"edge_id": "me-e6", "source_id": "me-6", "target_id": "me-7", "connection_type": "Sequence"},
        ],
        "trigger_event": "ebom.generated",
    },
    {
        "name": "CertificationWorkflow",
        "nodes": [
            {"node_id": "cw-1", "type": "Task", "name": "Compliance Matrix", "handler": "certification.compliance_matrix"},
            {"node_id": "cw-2", "type": "Task", "name": "Evidence Collection", "handler": "certification.evidence_collect"},
            {"node_id": "cw-3", "type": "Task", "name": "Compliance Verification", "handler": "certification.compliance_check"},
            {"node_id": "cw-4", "type": "Task", "name": "Certification Application", "handler": "certification.apply"},
        ],
        "edges": [
            {"edge_id": "cw-e1", "source_id": "cw-1", "target_id": "cw-2", "connection_type": "Sequence"},
            {"edge_id": "cw-e2", "source_id": "cw-2", "target_id": "cw-3", "connection_type": "Sequence"},
            {"edge_id": "cw-e3", "source_id": "cw-3", "target_id": "cw-4", "connection_type": "Sequence"},
        ],
        "trigger_event": "cert.compliance.verified",
    },
    {
        "name": "ChangeManagementWorkflow",
        "nodes": [
            {"node_id": "cm-1", "type": "Task", "name": "ECR Creation", "handler": "change.create_ecr"},
            {"node_id": "cm-2", "type": "Task", "name": "Impact Analysis", "handler": "aircraft_core.impact_analysis"},
            {"node_id": "cm-3", "type": "Task", "name": "ECO Approval", "handler": "human.approval"},
            {"node_id": "cm-4", "type": "Task", "name": "Baseline Update", "handler": "aircraft_core.baseline_update"},
            {"node_id": "cm-5", "type": "Task", "name": "Downstream Sync", "handler": "aircraft_core.sync"},
        ],
        "edges": [
            {"edge_id": "cm-e1", "source_id": "cm-1", "target_id": "cm-2", "connection_type": "Sequence"},
            {"edge_id": "cm-e2", "source_id": "cm-2", "target_id": "cm-3", "connection_type": "Sequence"},
            {"edge_id": "cm-e3", "source_id": "cm-3", "target_id": "cm-4", "connection_type": "Sequence"},
            {"edge_id": "cm-e4", "source_id": "cm-4", "target_id": "cm-5", "connection_type": "Sequence"},
        ],
        "trigger_event": "ecr.approved",
    },
]


class WorkflowDefinitionService:

    @staticmethod
    async def create_definition(name: str, nodes: list[dict], edges: list[dict], parameter_mappings: list[dict] | None = None, pool=None) -> WorkflowDefinition:
        wf_nodes = [WorkflowNode(**n) for n in nodes]
        wf_edges = [WorkflowEdge(**e) for e in edges]
        wf_params = [ParameterMapping(**p) for p in (parameter_mappings or [])]

        definition = WorkflowDefinition(
            definition_id=str(uuid.uuid4()),
            name=name,
            nodes=wf_nodes,
            edges=wf_edges,
            parameter_mappings=wf_params,
        )

        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO workflow_engine.workflow_definitions (definition_id, name, version, status, nodes, edges, parameter_mappings) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    definition.definition_id, name, 1, "Draft",
                    [n.model_dump() for n in wf_nodes], [e.model_dump() for e in wf_edges],
                    [p.model_dump() for p in wf_params],
                )

        return definition

    @staticmethod
    async def publish_definition(definition_id: str, pool) -> WorkflowDefinition | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_engine.workflow_definitions WHERE definition_id = $1", definition_id
            )
            if row is None:
                return None

            definition = WorkflowDefinition(
                definition_id=row["definition_id"],
                name=row["name"],
                version=row["version"],
                status=DefinitionStatus(row["status"]),
                nodes=[WorkflowNode(**n) for n in row["nodes"]],
                edges=[WorkflowEdge(**e) for e in row["edges"]],
            )

            definition.publish()

            await conn.execute(
                "UPDATE workflow_engine.workflow_definitions SET status = $1, updated_at = NOW() WHERE definition_id = $2",
                definition.status.value, definition_id,
            )

        return definition

    @staticmethod
    async def list_templates() -> list[dict[str, Any]]:
        return PREDEFINED_TEMPLATES

    @staticmethod
    async def get_definition(definition_id: str, pool) -> dict[str, Any] | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_engine.workflow_definitions WHERE definition_id = $1", definition_id
            )
            if row is None:
                return None
            return dict(row)