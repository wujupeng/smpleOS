from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.manufacturing.bom_three_view_manager_service import (
    BOMThreeViewManagerService,
    ManufacturingRule,
    ServiceRule,
    EBOMChange,
    ChangeType,
)

router = APIRouter(prefix="/api/v5/aircraft-core", tags=["BOM Three View v5"])

_service = BOMThreeViewManagerService()


@router.post("/ebom")
async def create_ebom(body: dict[str, Any]):
    project_id = body.get("project_id", "")
    root_node_data = body.get("root_node")
    ebom = _service.create_ebom(project_id=project_id, root_node_data=root_node_data)
    return {
        "bom_id": ebom.bom_id,
        "project_id": ebom.project_id,
        "version": ebom.version,
        "locked": ebom.locked,
    }


@router.post("/ebom/{ebom_id}/convert-to-mbom")
async def convert_ebom_to_mbom(ebom_id: str, body: dict[str, Any]):
    rules_data = body.get("rules", [])
    rules = [
        ManufacturingRule(
            rule_id=r.get("rule_id", ""),
            rule_type=r.get("rule_type", "AssemblySequence"),
            condition=r.get("condition", ""),
            action=r.get("action", {}),
            priority=r.get("priority", 0),
        )
        for r in rules_data
    ]
    try:
        mbom = _service.convert_ebom_to_mbom(ebom_id=ebom_id, rules=rules)
        return {
            "bom_id": mbom.bom_id,
            "source_ebom_id": mbom.source_ebom_id,
            "version": mbom.version,
            "manufacturing_rules_applied": mbom.manufacturing_rules_applied,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/mbom/{mbom_id}/convert-to-sbom")
async def convert_mbom_to_sbom(mbom_id: str, body: dict[str, Any]):
    rules_data = body.get("rules", [])
    rules = [
        ServiceRule(
            rule_id=r.get("rule_id", ""),
            rule_type=r.get("rule_type", "SparePartIdentification"),
            condition=r.get("condition", ""),
            action=r.get("action", {}),
        )
        for r in rules_data
    ]
    try:
        sbom = _service.convert_mbom_to_sbom(mbom_id=mbom_id, rules=rules)
        return {
            "bom_id": sbom.bom_id,
            "source_mbom_id": sbom.source_mbom_id,
            "version": sbom.version,
            "service_rules_applied": sbom.service_rules_applied,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ebom/{ebom_id}/propagate-change")
async def propagate_ebom_change(ebom_id: str, body: dict[str, Any]):
    change = EBOMChange(
        change_id=body.get("change_id", f"CHG-{id(body):08x}"),
        change_type=ChangeType(body.get("change_type", "ModifyPart")),
        affected_node_id=body.get("affected_node_id"),
        new_values=body.get("new_values", {}),
        reason=body.get("reason", ""),
        requested_by=body.get("requested_by", ""),
    )
    try:
        result = _service.propagate_ebom_change(ebom_id=ebom_id, change=change)
        return {
            "change_id": result.change_id,
            "mbom_changes": result.mbom_changes,
            "sbom_changes": result.sbom_changes,
            "manual_resolutions_needed": result.manual_resolutions_needed,
            "propagation_time_ms": result.propagation_time_ms,
            "status": result.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bom/{bom_id}/inconsistencies")
async def detect_inconsistencies(bom_id: str):
    report = _service.detect_inconsistencies(bom_id=bom_id)
    return {
        "bom_id": report.bom_id,
        "is_consistent": report.is_consistent,
        "inconsistencies": report.inconsistencies,
    }


@router.get("/bom/{bom_id}/versions")
async def get_bom_versions(bom_id: str):
    result = _service.get_bom_version(bom_id=bom_id)
    if result is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    return result