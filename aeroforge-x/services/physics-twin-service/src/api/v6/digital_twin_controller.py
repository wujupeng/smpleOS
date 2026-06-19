from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.digital_factory.digital_twin_synchronizer_service import (
    DigitalTwinSynchronizerService,
    TwinCommand,
)

router = APIRouter(prefix="/api/v6/physics-twin", tags=["Digital Twin v6"])

_twin_service = DigitalTwinSynchronizerService()


@router.post("/digital-twin/{equipment_id}/sync")
async def sync_twin_state(equipment_id: str, body: dict[str, Any]):
    twin_state = body.get("twin_state", {})
    physical_state = body.get("physical_state", {})
    _twin_service.updateTwinState(equipment_id=equipment_id, state=twin_state)
    _twin_service.updatePhysicalState(equipment_id=equipment_id, state=physical_state)
    result = _twin_service.syncTwinState(equipment_id=equipment_id)
    return result.to_dict()


@router.post("/digital-twin/{equipment_id}/detect-deviation")
async def detect_deviation(equipment_id: str, body: dict[str, Any]):
    twin_state = body.get("twin_state", {})
    physical_state = body.get("physical_state", {})
    _twin_service.updateTwinState(equipment_id=equipment_id, state=twin_state)
    _twin_service.updatePhysicalState(equipment_id=equipment_id, state=physical_state)
    alert = _twin_service.detectDeviation(equipment_id=equipment_id)
    if alert:
        return alert.to_dict()
    return {"deviation_detected": False}


@router.post("/digital-twin/commands")
async def issue_twin_command(body: dict[str, Any]):
    command = TwinCommand(
        command_id=body.get("command_id", ""),
        command_type=body.get("command_type", ""),
        parameters=body.get("parameters", {}),
        authorized_by_production=body.get("authorized_by_production", ""),
        authorized_by_safety=body.get("authorized_by_safety", ""),
    )
    result = _twin_service.issueTwinCommand(command=command)
    return result.to_dict()


@router.post("/digital-twin/commands/verify-safety")
async def verify_command_safety(body: dict[str, Any]):
    command = TwinCommand(
        command_id=body.get("command_id", ""),
        command_type=body.get("command_type", ""),
        parameters=body.get("parameters", {}),
        authorized_by_production=body.get("authorized_by_production", ""),
        authorized_by_safety=body.get("authorized_by_safety", ""),
    )
    result = _twin_service.verifyCommandSafety(command=command)
    return result.to_dict()