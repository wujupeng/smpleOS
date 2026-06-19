from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.configuration_management.configuration_manager_service import (
    ConfigurationManagerService,
)
from src.domain.services.configuration_management.three_view_config_propagation_service import (
    ThreeViewConfigPropagationService,
    ManufacturingRule,
    OperationalRule,
    DesignConfigChange,
)
from src.domain.services.configuration_management.configuration_baseline_service import (
    ConfigurationBaselineService,
)

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Configuration Management v6"])

_config_service = ConfigurationManagerService()
_propagation_service = ThreeViewConfigPropagationService()
_baseline_service = ConfigurationBaselineService()


@router.post("/block-configurations")
async def create_block_config(body: dict[str, Any]):
    aircraft_type = body.get("aircraft_type", "")
    block_name = body.get("block_name", "")
    block = _config_service.createBlockConfig(aircraft_type=aircraft_type, block_name=block_name)
    return block.to_dict()


@router.post("/sn-configurations")
async def create_sn_config(body: dict[str, Any]):
    block_id = body.get("block_id", "")
    tail_number = body.get("tail_number", "")
    try:
        sn = _config_service.createSNConfig(block_id=block_id, tail_number=tail_number)
        return sn.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/config-hierarchies/{aircraft_type}")
async def get_config_hierarchy(aircraft_type: str):
    try:
        hierarchy = _config_service.getConfigHierarchy(aircraft_type=aircraft_type)
        return hierarchy.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/block-configurations/{block_id}/inherit")
async def inherit_block_config(block_id: str, body: dict[str, Any]):
    new_block_name = body.get("new_block_name", "")
    changes = body.get("changes", {})
    try:
        block = _config_service.inheritBlockConfig(
            new_block_name=new_block_name, source_block_id=block_id, changes=changes
        )
        return block.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sn-configurations/{sn_id}/inherit")
async def inherit_sn_config(sn_id: str, body: dict[str, Any]):
    block_id = body.get("block_id", "")
    modifications = body.get("modifications", {})
    try:
        sn = _config_service.inheritSNConfig(
            new_sn_id=sn_id, block_id=block_id, modifications=modifications
        )
        return sn.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/config-conflicts/detect")
async def detect_config_conflicts(body: dict[str, Any]):
    block_id = body.get("block_id", "")
    sn_id = body.get("sn_id", "")
    try:
        report = _config_service.detectConfigConflicts(block_id=block_id, sn_id=sn_id)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/design-configs/{config_id}/derive-manufacturing")
async def derive_manufacturing_config(config_id: str, body: dict[str, Any]):
    rules_data = body.get("rules", [])
    rules = [
        ManufacturingRule(
            rule_id=r.get("rule_id", ""),
            rule_type=r.get("rule_type", "ProcessAssignment"),
            rule_expression=r.get("rule_expression", ""),
            priority=r.get("priority", 0),
        )
        for r in rules_data
    ]
    design_config = body.get("design_config", {})
    from src.domain.services.configuration_management.configuration_manager_service import DesignConfiguration
    dc = DesignConfiguration(config_id=config_id)
    mfg = _propagation_service.deriveManufacturingConfig(design_config=dc, rules=rules if rules else None)
    return mfg.to_dict()


@router.post("/mfg-configs/{config_id}/derive-operational")
async def derive_operational_config(config_id: str, body: dict[str, Any]):
    rules_data = body.get("rules", [])
    rules = [
        OperationalRule(
            rule_id=r.get("rule_id", ""),
            rule_type=r.get("rule_type", "EquipmentInstallation"),
            rule_expression=r.get("rule_expression", ""),
            priority=r.get("priority", 0),
        )
        for r in rules_data
    ]
    from src.domain.services.configuration_management.configuration_manager_service import ManufacturingConfiguration
    mc = ManufacturingConfiguration(config_id=config_id, source_design_config_id="")
    op = _propagation_service.deriveOperationalConfig(mfg_config=mc, rules=rules if rules else None)
    return op.to_dict()


@router.post("/design-configs/{config_id}/propagate-change")
async def propagate_design_change(config_id: str, body: dict[str, Any]):
    block_id = body.get("block_id", "")
    block = _config_service.getBlock(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    change = DesignConfigChange(
        block_id=block_id,
        changed_items=body.get("changed_items", []),
        change_reason=body.get("reason", ""),
    )
    result = _propagation_service.propagateDesignChange(block=block, change=change)
    return result.to_dict()


@router.get("/configs/{config_id}/inconsistencies")
async def detect_inconsistencies(config_id: str):
    block = _config_service.getBlock(config_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {config_id}")
    report = _propagation_service.detectInconsistencies(block=block)
    return report.to_dict()


@router.post("/baselines/fbl")
async def establish_fbl(body: dict[str, Any]):
    block_id = body.get("block_id", "")
    established_by = body.get("established_by", "")
    block = _config_service.getBlock(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    baseline = _baseline_service.establishFBL(block=block, established_by=established_by)
    return baseline.to_dict()


@router.post("/baselines/fcl")
async def establish_fcl(body: dict[str, Any]):
    block_id = body.get("block_id", "")
    established_by = body.get("established_by", "")
    block = _config_service.getBlock(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    baseline = _baseline_service.establishFCL(block=block, established_by=established_by)
    return baseline.to_dict()


@router.post("/baselines/fsdl")
async def establish_fsdl(body: dict[str, Any]):
    block_id = body.get("block_id", "")
    established_by = body.get("established_by", "")
    block = _config_service.getBlock(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")
    baseline = _baseline_service.establishFSDL(block=block, established_by=established_by)
    return baseline.to_dict()


@router.post("/baselines/compare")
async def compare_baselines(body: dict[str, Any]):
    baseline_id_1 = body.get("baseline_id_1", "")
    baseline_id_2 = body.get("baseline_id_2", "")
    try:
        report = _baseline_service.compareBaselines(baseline_id_1=baseline_id_1, baseline_id_2=baseline_id_2)
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))