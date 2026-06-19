"""AeroForge-X v6.0 CrossProgramEventOrchestratorService

Orchestrates event-driven integration across the five Programs (H/I/J/K/E).
Implements 10 cross-Program integration points via NATS JetStream event
subscription and dispatch.

INT-1.1:  ConfigChange → Traceability update
INT-1.2:  CertEvidence locked → ConfigBaseline lock
INT-1.3:  MaterialLot downgrade → SN config update
INT-1.4:  SupplierQualityIssue → RequirementsTraceability
INT-1.5:  DigitalTwin deviation → Config state update
INT-1.6:  ShopFloor quality alert → CAR trigger
INT-1.7:  ShopFloor equipment status → ConfigChange trigger
INT-1.8:  UQ high uncertainty → 7-Discipline MDO propagation
INT-1.9:  7-Discipline MDO result → Design config update
INT-1.10: ConfigChange → DigitalTwin model update

REQ-DFX-V6-001~038, REQ-NFR-V6-001~047
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class IntegrationPoint(str, Enum):
    CONFIG_CHANGE_TO_TRACEABILITY = "ConfigChange→Traceability"
    CERT_EVIDENCE_TO_BASELINE_LOCK = "CertEvidence→BaselineLock"
    MATERIAL_LOT_TO_SN_CONFIG = "MaterialLot→SNConfig"
    SUPPLIER_ISSUE_TO_TRACEABILITY = "SupplierIssue→Traceability"
    TWIN_DEVIATION_TO_CONFIG = "TwinDeviation→Config"
    SHOP_FLOOR_QUALITY_TO_CAR = "ShopFloorQuality→CAR"
    SHOP_FLOOR_STATUS_TO_CONFIG_CHANGE = "ShopFloorStatus→ConfigChange"
    UQ_HIGH_UNCERTAINTY_TO_MDO = "UQHighUncertainty→MDO"
    MDO_RESULT_TO_DESIGN_CONFIG = "MDOResult→DesignConfig"
    CONFIG_CHANGE_TO_TWIN_UPDATE = "ConfigChange→TwinUpdate"


class IntegrationStatus(str, Enum):
    PENDING = "Pending"
    DISPATCHED = "Dispatched"
    COMPLETED = "Completed"
    FAILED = "Failed"
    RETRYING = "Retrying"


@dataclass
class CrossProgramEvent:
    event_id: str
    source_subject: str
    integration_point: IntegrationPoint
    payload: dict = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: str = ""
    source_program: str = ""
    target_program: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "source_subject": self.source_subject,
            "integration_point": self.integration_point.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "source_program": self.source_program,
            "target_program": self.target_program,
        }


@dataclass
class IntegrationResult:
    event_id: str
    integration_point: IntegrationPoint
    status: IntegrationStatus
    target_action: str
    result_data: dict = field(default_factory=dict)
    error: str = ""
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "integration_point": self.integration_point.value,
            "status": self.status.value,
            "target_action": self.target_action,
            "result_data": self.result_data,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class IntegrationHealth:
    integration_point: IntegrationPoint
    total_events: int = 0
    successful: int = 0
    failed: int = 0
    avg_latency_ms: float = 0.0
    last_event_at: str = ""

    def to_dict(self) -> dict:
        return {
            "integration_point": self.integration_point.value,
            "total_events": self.total_events,
            "successful": self.successful,
            "failed": self.failed,
            "avg_latency_ms": self.avg_latency_ms,
            "last_event_at": self.last_event_at,
        }


INTEGRATION_ROUTING = {
    "aeroforge.v6.config.change.propagated": IntegrationPoint.CONFIG_CHANGE_TO_TRACEABILITY,
    "aeroforge.v6.cert.evidence.package.locked": IntegrationPoint.CERT_EVIDENCE_TO_BASELINE_LOCK,
    "aeroforge.v6.supplier.rating.downgrade": IntegrationPoint.MATERIAL_LOT_TO_SN_CONFIG,
    "aeroforge.v6.supplier.quality.issue.created": IntegrationPoint.SUPPLIER_ISSUE_TO_TRACEABILITY,
    "aeroforge.v6.factory.deviation.alert": IntegrationPoint.TWIN_DEVIATION_TO_CONFIG,
    "aeroforge.v6.factory.quality.alert": IntegrationPoint.SHOP_FLOOR_QUALITY_TO_CAR,
    "aeroforge.v6.factory.equipment.status": IntegrationPoint.SHOP_FLOOR_STATUS_TO_CONFIG_CHANGE,
    "aeroforge.v6.uq.high_uncertainty": IntegrationPoint.UQ_HIGH_UNCERTAINTY_TO_MDO,
}

INTEGRATION_TARGET_PROGRAMS = {
    IntegrationPoint.CONFIG_CHANGE_TO_TRACEABILITY: ("Program-H", "Program-I"),
    IntegrationPoint.CERT_EVIDENCE_TO_BASELINE_LOCK: ("Program-I", "Program-H"),
    IntegrationPoint.MATERIAL_LOT_TO_SN_CONFIG: ("Program-J", "Program-H"),
    IntegrationPoint.SUPPLIER_ISSUE_TO_TRACEABILITY: ("Program-J", "Program-I"),
    IntegrationPoint.TWIN_DEVIATION_TO_CONFIG: ("Program-K", "Program-H"),
    IntegrationPoint.SHOP_FLOOR_QUALITY_TO_CAR: ("Program-K", "Program-J"),
    IntegrationPoint.SHOP_FLOOR_STATUS_TO_CONFIG_CHANGE: ("Program-K", "Program-H"),
    IntegrationPoint.UQ_HIGH_UNCERTAINTY_TO_MDO: ("Program-E", "Program-E"),
    IntegrationPoint.MDO_RESULT_TO_DESIGN_CONFIG: ("Program-E", "Program-H"),
    IntegrationPoint.CONFIG_CHANGE_TO_TWIN_UPDATE: ("Program-H", "Program-K"),
}

MAX_RETRY = 3


class CrossProgramEventOrchestratorService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._results: dict[str, IntegrationResult] = {}
        self._health: dict[IntegrationPoint, IntegrationHealth] = {
            pt: IntegrationHealth(integration_point=pt) for pt in IntegrationPoint
        }
        self._event_log: list[CrossProgramEvent] = []

    def routeEvent(
        self, nats_subject: str, payload: dict, correlation_id: str = ""
    ) -> Optional[IntegrationResult]:
        integration_point = INTEGRATION_ROUTING.get(nats_subject)
        if integration_point is None:
            return None

        src_program, tgt_program = INTEGRATION_TARGET_PROGRAMS.get(
            integration_point, ("", "")
        )

        event = CrossProgramEvent(
            event_id=f"CPE-{uuid.uuid4().hex[:8]}",
            source_subject=nats_subject,
            integration_point=integration_point,
            payload=payload,
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_program=src_program,
            target_program=tgt_program,
        )
        self._event_log.append(event)

        result = self._dispatch(event)
        self._results[event.event_id] = result
        self._update_health(integration_point, result)
        return result

    def _dispatch(self, event: CrossProgramEvent) -> IntegrationResult:
        handler = self._get_handler(event.integration_point)
        if handler is None:
            return IntegrationResult(
                event_id=event.event_id,
                integration_point=event.integration_point,
                status=IntegrationStatus.FAILED,
                target_action="Unknown",
                error=f"No handler for {event.integration_point.value}",
            )

        try:
            action, result_data = handler(event.payload)
            return IntegrationResult(
                event_id=event.event_id,
                integration_point=event.integration_point,
                status=IntegrationStatus.COMPLETED,
                target_action=action,
                result_data=result_data,
            )
        except Exception as exc:
            return IntegrationResult(
                event_id=event.event_id,
                integration_point=event.integration_point,
                status=IntegrationStatus.FAILED,
                target_action=handler.__name__ if hasattr(handler, "__name__") else "dispatch",
                error=str(exc),
            )

    def _get_handler(self, point: IntegrationPoint):
        handlers = {
            IntegrationPoint.CONFIG_CHANGE_TO_TRACEABILITY: self._handle_config_change_to_traceability,
            IntegrationPoint.CERT_EVIDENCE_TO_BASELINE_LOCK: self._handle_cert_evidence_to_baseline_lock,
            IntegrationPoint.MATERIAL_LOT_TO_SN_CONFIG: self._handle_material_lot_to_sn_config,
            IntegrationPoint.SUPPLIER_ISSUE_TO_TRACEABILITY: self._handle_supplier_issue_to_traceability,
            IntegrationPoint.TWIN_DEVIATION_TO_CONFIG: self._handle_twin_deviation_to_config,
            IntegrationPoint.SHOP_FLOOR_QUALITY_TO_CAR: self._handle_shop_floor_quality_to_car,
            IntegrationPoint.SHOP_FLOOR_STATUS_TO_CONFIG_CHANGE: self._handle_shop_floor_status_to_config_change,
            IntegrationPoint.UQ_HIGH_UNCERTAINTY_TO_MDO: self._handle_uq_high_uncertainty_to_mdo,
            IntegrationPoint.MDO_RESULT_TO_DESIGN_CONFIG: self._handle_mdo_result_to_design_config,
            IntegrationPoint.CONFIG_CHANGE_TO_TWIN_UPDATE: self._handle_config_change_to_twin_update,
        }
        return handlers.get(point)

    def _handle_config_change_to_traceability(self, payload: dict) -> tuple[str, dict]:
        block_id = payload.get("block_id", "")
        change_class = payload.get("change_class", "")
        affected_items = payload.get("affected_items", [])

        trace_updates = []
        for item in affected_items:
            trace_updates.append({
                "item_id": item.get("item_id", ""),
                "action": "update_trace_link",
                "reason": f"ConfigChange({change_class})",
                "block_id": block_id,
            })

        return "RequirementsTraceabilityService.updateTraceLinks", {
            "block_id": block_id,
            "change_class": change_class,
            "trace_updates": trace_updates,
            "subject": "aeroforge.v6.cert.trace.link.created",
        }

    def _handle_cert_evidence_to_baseline_lock(self, payload: dict) -> tuple[str, dict]:
        package_id = payload.get("package_id", "")
        checklist_id = payload.get("checklist_id", "")
        project_id = payload.get("project_id", "")

        return "ConfigurationBaselineService.lockBaseline", {
            "package_id": package_id,
            "checklist_id": checklist_id,
            "project_id": project_id,
            "lock_reason": "Certification evidence package locked",
            "subject": "aeroforge.v6.config.change.propagated",
        }

    def _handle_material_lot_to_sn_config(self, payload: dict) -> tuple[str, dict]:
        supplier_id = payload.get("supplier_id", "")
        lot_ids = payload.get("affected_lots", [])
        new_rating = payload.get("new_rating", 0.0)

        sn_updates = []
        for lot_id in lot_ids:
            sn_updates.append({
                "lot_id": lot_id,
                "action": "flag_sn_for_review",
                "reason": f"Supplier rating downgrade to {new_rating}",
            })

        return "ConfigurationManagerService.updateSNConfig", {
            "supplier_id": supplier_id,
            "sn_updates": sn_updates,
            "new_rating": new_rating,
        }

    def _handle_supplier_issue_to_traceability(self, payload: dict) -> tuple[str, dict]:
        issue_id = payload.get("issue_id", "")
        supplier_id = payload.get("supplier_id", "")
        severity = payload.get("severity", "")
        affected_aircraft = payload.get("affected_aircraft", [])

        trace_impacts = []
        for tail_number in affected_aircraft:
            trace_impacts.append({
                "tail_number": tail_number,
                "impact_type": "supplier_quality_issue",
                "issue_id": issue_id,
                "severity": severity,
            })

        return "RequirementsTraceabilityService.addTraceImpact", {
            "issue_id": issue_id,
            "supplier_id": supplier_id,
            "trace_impacts": trace_impacts,
            "subject": "aeroforge.v6.cert.trace.gap.alert",
        }

    def _handle_twin_deviation_to_config(self, payload: dict) -> tuple[str, dict]:
        equipment_id = payload.get("equipment_id", "")
        deviation_pct = payload.get("deviation_percentage", 0.0)
        root_cause = payload.get("root_cause", "")

        config_update = {
            "equipment_id": equipment_id,
            "deviation_percentage": deviation_pct,
            "root_cause": root_cause,
            "action": "mark_config_item_for_review",
            "requires_change_request": deviation_pct > 10.0,
        }

        return "ConfigurationManagerService.flagConfigForReview", config_update

    def _handle_shop_floor_quality_to_car(self, payload: dict) -> tuple[str, dict]:
        equipment_id = payload.get("equipment_id", "")
        alert_type = payload.get("alert_type", "")
        defect_data = payload.get("defect_data", {})

        car_trigger = {
            "equipment_id": equipment_id,
            "alert_type": alert_type,
            "defect_data": defect_data,
            "action": "create_supplier_quality_issue",
            "auto_create_car": alert_type in ("Critical", "Major"),
        }

        return "SupplierCARService.createQualityIssue", car_trigger

    def _handle_shop_floor_status_to_config_change(self, payload: dict) -> tuple[str, dict]:
        equipment_id = payload.get("equipment_id", "")
        new_status = payload.get("new_status", "")

        change_trigger = {
            "equipment_id": equipment_id,
            "new_status": new_status,
            "action": "evaluate_config_change_need",
            "auto_submit_change_request": new_status == "Decommissioned",
        }

        return "ConfigurationChangeControlService.submitChangeRequest", change_trigger

    def _handle_uq_high_uncertainty_to_mdo(self, payload: dict) -> tuple[str, dict]:
        model_id = payload.get("model_id", "")
        uq_method = payload.get("uq_method", "")
        coefficient_of_variation = payload.get("coefficient_of_variation", 0.0)

        mdo_propagation = {
            "model_id": model_id,
            "uq_method": uq_method,
            "coefficient_of_variation": coefficient_of_variation,
            "action": "propagate_uncertainty_to_mdo",
            "uncertainty_bounds": {
                "lower": 1.0 - coefficient_of_variation,
                "upper": 1.0 + coefficient_of_variation,
            },
        }

        return "SevenDisciplineMDOService.propagateUncertainty", mdo_propagation

    def _handle_mdo_result_to_design_config(self, payload: dict) -> tuple[str, dict]:
        run_id = payload.get("run_id", "")
        optimal_design = payload.get("optimal_design", {})
        objectives = payload.get("objectives", {})

        config_update = {
            "run_id": run_id,
            "optimal_design": optimal_design,
            "objectives": objectives,
            "action": "update_design_configuration",
            "source": "SevenDisciplineMDO",
        }

        return "ConfigurationManagerService.updateDesignConfig", config_update

    def _handle_config_change_to_twin_update(self, payload: dict) -> tuple[str, dict]:
        block_id = payload.get("block_id", "")
        changed_items = payload.get("changed_items", [])

        twin_update = {
            "block_id": block_id,
            "changed_items": changed_items,
            "action": "update_twin_models",
            "requires_resync": True,
        }

        return "DigitalTwinSynchronizerService.updateTwinState", twin_update

    def _update_health(
        self, point: IntegrationPoint, result: IntegrationResult
    ) -> None:
        health = self._health[point]
        health.total_events += 1
        if result.status == IntegrationStatus.COMPLETED:
            health.successful += 1
        else:
            health.failed += 1

    def retryFailed(self, event_id: str) -> Optional[IntegrationResult]:
        result = self._results.get(event_id)
        if result is None:
            return None
        if result.status != IntegrationStatus.FAILED:
            return result

        result.retry_count += 1
        if result.retry_count > MAX_RETRY:
            return result

        result.status = IntegrationStatus.RETRYING

        event = next(
            (e for e in self._event_log if e.event_id == event_id), None
        )
        if event is None:
            return result

        new_result = self._dispatch(event)
        new_result.retry_count = result.retry_count
        self._results[event_id] = new_result
        self._update_health(event.integration_point, new_result)
        return new_result

    def getIntegrationHealth(self) -> list[IntegrationHealth]:
        return list(self._health.values())

    def getIntegrationResult(self, event_id: str) -> Optional[IntegrationResult]:
        return self._results.get(event_id)

    def getEventLog(
        self, integration_point: Optional[IntegrationPoint] = None
    ) -> list[CrossProgramEvent]:
        if integration_point is None:
            return list(self._event_log)
        return [
            e for e in self._event_log if e.integration_point == integration_point
        ]

    def triggerMDOConfigUpdate(self, mdo_result: dict) -> IntegrationResult:
        event = CrossProgramEvent(
            event_id=f"CPE-{uuid.uuid4().hex[:8]}",
            source_subject="aeroforge.v6.mdo.7d.result",
            integration_point=IntegrationPoint.MDO_RESULT_TO_DESIGN_CONFIG,
            payload=mdo_result,
            source_program="Program-E",
            target_program="Program-H",
        )
        self._event_log.append(event)
        result = self._dispatch(event)
        self._results[event.event_id] = result
        self._update_health(event.integration_point, result)
        return result

    def triggerConfigTwinUpdate(self, config_change: dict) -> IntegrationResult:
        event = CrossProgramEvent(
            event_id=f"CPE-{uuid.uuid4().hex[:8]}",
            source_subject="aeroforge.v6.config.change.propagated",
            integration_point=IntegrationPoint.CONFIG_CHANGE_TO_TWIN_UPDATE,
            payload=config_change,
            source_program="Program-H",
            target_program="Program-K",
        )
        self._event_log.append(event)
        result = self._dispatch(event)
        self._results[event.event_id] = result
        self._update_health(event.integration_point, result)
        return result