from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.domain.handlers.v3_handlers import (
    CAETriggerHandler, CFDAnalysisHandler, ComplianceCheckHandler,
    ComplianceImpactHandler, DesignRuleCheckHandler, FEAAnalysisHandler,
    FRACASCreateHandler, InspectionHandler, MBOMTransformHandler,
    RootCauseAnalysisHandler, WorkOrderGenerateHandler,
)


CHAIN_CONFIGS: dict[str, dict[str, Any]] = {
    "DesignToCAE": {
        "chain_type": "DesignToCAE",
        "trigger_event_pattern": "aeroforge.aircraft.object.updated",
        "propagation_hint_filter": ["design.geometry.*", "design.structure.*"],
        "handler_sequence": [
            {"handler": "design.rule_check", "name": "Design Rule Check"},
            {"handler": "design.cae_trigger", "name": "CAE Parameter Extraction"},
            {"handler": "human.approval", "name": "CAE Parameter Confirmation", "role": "design_engineer", "timeout_hours": 24},
            {"handler": "verification.cfd_analysis", "name": "CFD Analysis"},
            {"handler": "verification.fea_analysis", "name": "FEA Analysis"},
        ],
    },
    "EBOMToMBOM": {
        "chain_type": "EBOMToMBOM",
        "trigger_event_pattern": "aeroforge.manufacturing.ebom.generated",
        "propagation_hint_filter": [],
        "handler_sequence": [
            {"handler": "manufacturing.mbom_transform", "name": "mBOM Transform"},
            {"handler": "human.approval", "name": "mBOM Review", "role": "manufacturing_engineer", "timeout_hours": 48},
            {"handler": "manufacturing.work_order_generate", "name": "Work Order Generation"},
        ],
    },
    "TwinToFRACAS": {
        "chain_type": "TwinToFRACAS",
        "trigger_event_pattern": "aeroforge.twin.anomaly.detected",
        "propagation_hint_filter": [],
        "handler_sequence": [
            {"handler": "quality.fracas_create", "name": "FRACAS Report Creation"},
            {"handler": "quality.root_cause_analysis", "name": "Root Cause Analysis"},
            {"handler": "human.approval", "name": "FRACAS Review", "role": "maintenance_engineer", "timeout_hours": 12},
            {"handler": "certification.compliance_impact", "name": "Compliance Impact Assessment"},
            {"handler": "human.approval", "name": "Safety-Critical Dual Approval", "role": "maintenance_engineer+airworthiness_engineer", "timeout_hours": 24, "dual_approval": True},
        ],
    },
}

_HANDLER_INSTANCES: dict[str, Any] = {
    "design.rule_check": DesignRuleCheckHandler(),
    "design.cae_trigger": CAETriggerHandler(),
    "verification.cfd_analysis": CFDAnalysisHandler(),
    "verification.fea_analysis": FEAAnalysisHandler(),
    "manufacturing.mbom_transform": MBOMTransformHandler(),
    "manufacturing.work_order_generate": WorkOrderGenerateHandler(),
    "certification.compliance_check": ComplianceCheckHandler(),
    "certification.compliance_impact": ComplianceImpactHandler(),
    "quality.fracas_create": FRACASCreateHandler(),
    "quality.root_cause_analysis": RootCauseAnalysisHandler(),
    "quality.inspection": InspectionHandler(),
}


class PropagationChainService:

    _chain_executions: dict[str, dict[str, Any]] = {}

    @classmethod
    def configure_chain(cls, chain_type: str) -> dict[str, Any]:
        config = CHAIN_CONFIGS.get(chain_type)
        if config is None:
            return {"error": f"Unknown chain type: {chain_type}"}

        chain_id = str(uuid.uuid4())
        execution = {
            "chain_id": chain_id,
            "chain_type": chain_type,
            "config": config,
            "status": "Configured",
            "created_at": datetime.utcnow().isoformat(),
        }
        cls._chain_executions[chain_id] = execution
        return execution

    @classmethod
    def execute_chain(cls, chain_type: str, event_data: dict[str, Any], object_data: dict[str, Any] | None = None) -> dict[str, Any]:
        config = CHAIN_CONFIGS.get(chain_type)
        if config is None:
            return {"error": f"Unknown chain type: {chain_type}"}

        chain_id = str(uuid.uuid4())
        execution_log = {
            "chain_id": chain_id,
            "chain_type": chain_type,
            "status": "Running",
            "started_at": datetime.utcnow().isoformat(),
            "nodes": [],
        }

        from src.domain.handlers.activity_handler_v3 import HandlerInput

        current_data = {**event_data, "parameters": dict(event_data)}
        if object_data:
            current_data["parameters"].update(object_data)

        for i, node in enumerate(config["handler_sequence"]):
            handler_name = node["handler"]

            if handler_name == "human.approval":
                execution_log["nodes"].append({
                    "node_index": i,
                    "handler": handler_name,
                    "name": node["name"],
                    "status": "PendingApproval",
                    "role": node.get("role", ""),
                    "timeout_hours": node.get("timeout_hours", 24),
                    "dual_approval": node.get("dual_approval", False),
                })
                continue

            handler = _HANDLER_INSTANCES.get(handler_name)
            if handler is None:
                execution_log["nodes"].append({"node_index": i, "handler": handler_name, "status": "Error", "error": f"Handler not found: {handler_name}"})
                execution_log["status"] = "Failed"
                break

            handler_input = HandlerInput(
                model_id=current_data.get("model_id", current_data.get("aggregate_id", "")),
                rule_set_id=current_data.get("rule_set_id", ""),
                parameters=current_data.get("parameters", {}),
            )

            validation_errors = handler.validate_input(handler_input)
            if validation_errors:
                execution_log["nodes"].append({"node_index": i, "handler": handler_name, "status": "ValidationError", "errors": validation_errors})
                execution_log["status"] = "Failed"
                break

            try:
                output = handler.execute(handler_input)
                execution_log["nodes"].append({
                    "node_index": i,
                    "handler": handler_name,
                    "name": node.get("name", handler_name),
                    "status": output.status,
                    "result": output.result,
                    "schema_refs_used": output.schema_refs_used,
                })
                current_data["parameters"].update(output.result)
            except Exception as e:
                execution_log["nodes"].append({"node_index": i, "handler": handler_name, "status": "Error", "error": str(e)})
                execution_log["status"] = "Failed"
                break

        if execution_log["status"] == "Running":
            execution_log["status"] = "Completed"
        execution_log["completed_at"] = datetime.utcnow().isoformat()

        cls._chain_executions[chain_id] = execution_log
        return execution_log

    @classmethod
    def get_chain_status(cls, chain_id: str) -> dict[str, Any] | None:
        return cls._chain_executions.get(chain_id)

    @classmethod
    def list_chains(cls) -> list[dict[str, Any]]:
        return list(cls._chain_executions.values())

    @classmethod
    def get_chain_configs(cls) -> dict[str, Any]:
        return CHAIN_CONFIGS