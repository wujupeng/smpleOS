"""AeroForge-X v6.0 DigitalTwinSynchronizerService

Manages digital twin bidirectional synchronization with physical factory:
real-time sync, deviation detection, command issuance, and safety verification.
REQ-FACTORY-007~012
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviationRootCause(str, Enum):
    SENSOR_ERROR = "SensorError"
    PROCESS_DRIFT = "ProcessDrift"
    EQUIPMENT_DEGRADATION = "EquipmentDegradation"
    UNKNOWN = "Unknown"


@dataclass
class DeviationAlert:
    equipment_id: str
    twin_predicted_value: float
    physical_actual_value: float
    deviation_percentage: float
    root_cause: DeviationRootCause = DeviationRootCause.UNKNOWN
    suggested_corrective_action: str = ""

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "twin_predicted_value": self.twin_predicted_value,
            "physical_actual_value": self.physical_actual_value,
            "deviation_percentage": self.deviation_percentage,
            "root_cause": self.root_cause.value,
            "suggested_corrective_action": self.suggested_corrective_action,
        }


@dataclass
class TwinCommand:
    command_id: str
    command_type: str
    parameters: dict = field(default_factory=dict)
    authorized_by_production: str = ""
    authorized_by_safety: str = ""
    safety_verified: bool = False

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type,
            "parameters": self.parameters,
            "authorized_by_production": self.authorized_by_production,
            "authorized_by_safety": self.authorized_by_safety,
            "safety_verified": self.safety_verified,
        }


@dataclass
class SafetyVerificationResult:
    is_safe: bool
    constraint_checks: list[dict] = field(default_factory=list)
    verified_by_safety_engineer: str = ""

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "constraint_checks": self.constraint_checks,
            "verified_by_safety_engineer": self.verified_by_safety_engineer,
        }


@dataclass
class TwinSyncResult:
    equipment_id: str
    is_synchronized: bool
    deviation_items: list[dict] = field(default_factory=list)
    sync_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "equipment_id": self.equipment_id,
            "is_synchronized": self.is_synchronized,
            "deviation_items": self.deviation_items,
            "sync_duration_ms": self.sync_duration_ms,
        }


@dataclass
class CommandResult:
    command_id: str
    executed: bool
    result_data: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "executed": self.executed,
            "result_data": self.result_data,
            "error": self.error,
        }


class DigitalTwinSynchronizerService:

    DEVIATION_THRESHOLD_PCT = 5.0

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._twin_states: dict[str, dict] = {}
        self._physical_states: dict[str, dict] = {}
        self._sync_log: list[dict] = []
        self._commands: dict[str, TwinCommand] = {}

    def syncTwinState(self, equipment_id: str) -> TwinSyncResult:
        import time as _time
        start = _time.monotonic()

        twin = self._twin_states.get(equipment_id, {})
        physical = self._physical_states.get(equipment_id, {})

        deviation_items = []
        is_synced = True

        all_keys = set(twin.keys()) | set(physical.keys())
        for key in all_keys:
            t_val = twin.get(key, 0)
            p_val = physical.get(key, 0)
            if t_val != 0 and p_val != 0:
                dev_pct = abs(t_val - p_val) / max(abs(t_val), abs(p_val)) * 100
                if dev_pct > self.DEVIATION_THRESHOLD_PCT:
                    is_synced = False
                    deviation_items.append({
                        "parameter": key,
                        "twin_value": t_val,
                        "physical_value": p_val,
                        "deviation_pct": dev_pct,
                    })

        elapsed_ms = (_time.monotonic() - start) * 1000.0

        result = TwinSyncResult(
            equipment_id=equipment_id,
            is_synchronized=is_synced,
            deviation_items=deviation_items,
            sync_duration_ms=elapsed_ms,
        )

        self._sync_log.append({
            "equipment_id": equipment_id,
            "is_synchronized": is_synced,
            "synced_at": _time.time(),
            "checksum": str(hash(frozenset({**twin, **physical}.items()))),
        })

        return result

    def detectDeviation(self, equipment_id: str) -> Optional[DeviationAlert]:
        twin = self._twin_states.get(equipment_id, {})
        physical = self._physical_states.get(equipment_id, {})

        for key in set(twin.keys()) & set(physical.keys()):
            t_val = twin[key]
            p_val = physical[key]
            if t_val != 0 and p_val != 0:
                dev_pct = abs(t_val - p_val) / max(abs(t_val), abs(p_val)) * 100
                if dev_pct > self.DEVIATION_THRESHOLD_PCT:
                    root_cause = self._analyze_root_cause(equipment_id, key, dev_pct)
                    return DeviationAlert(
                        equipment_id=equipment_id,
                        twin_predicted_value=t_val,
                        physical_actual_value=p_val,
                        deviation_percentage=dev_pct,
                        root_cause=root_cause,
                        suggested_corrective_action=self._suggest_correction(root_cause),
                    )
        return None

    def _analyze_root_cause(
        self, equipment_id: str, parameter: str, deviation_pct: float
    ) -> DeviationRootCause:
        if deviation_pct > 50:
            return DeviationRootCause.SENSOR_ERROR
        elif deviation_pct > 20:
            return DeviationRootCause.PROCESS_DRIFT
        else:
            return DeviationRootCause.EQUIPMENT_DEGRADATION

    def _suggest_correction(self, root_cause: DeviationRootCause) -> str:
        suggestions = {
            DeviationRootCause.SENSOR_ERROR: "Recalibrate sensor and verify reading",
            DeviationRootCause.PROCESS_DRIFT: "Adjust process parameters to nominal",
            DeviationRootCause.EQUIPMENT_DEGRADATION: "Schedule maintenance inspection",
            DeviationRootCause.UNKNOWN: "Investigate deviation source",
        }
        return suggestions.get(root_cause, "Investigate deviation source")

    def issueTwinCommand(self, command: TwinCommand) -> CommandResult:
        if not command.safety_verified:
            return CommandResult(
                command_id=command.command_id,
                executed=False,
                error="Command not safety-verified",
            )

        if not command.authorized_by_production or not command.authorized_by_safety:
            return CommandResult(
                command_id=command.command_id,
                executed=False,
                error="Dual authorization required",
            )

        self._commands[command.command_id] = command

        return CommandResult(
            command_id=command.command_id,
            executed=True,
            result_data={"command_type": command.command_type, "status": "Executed"},
        )

    def verifyCommandSafety(self, command: TwinCommand) -> SafetyVerificationResult:
        constraint_checks = []

        params = command.parameters
        if "temperature" in params and params["temperature"] > 1000:
            constraint_checks.append({
                "constraint": "MaxTemperature",
                "value": params["temperature"],
                "limit": 1000,
                "passed": False,
            })

        if "pressure" in params and params["pressure"] > 500:
            constraint_checks.append({
                "constraint": "MaxPressure",
                "value": params["pressure"],
                "limit": 500,
                "passed": False,
            })

        if not constraint_checks:
            constraint_checks.append({"constraint": "AllChecks", "passed": True})

        is_safe = all(c.get("passed", True) for c in constraint_checks)

        if is_safe and command.authorized_by_safety:
            command.safety_verified = True

        return SafetyVerificationResult(
            is_safe=is_safe,
            constraint_checks=constraint_checks,
            verified_by_safety_engineer=command.authorized_by_safety,
        )

    def updateTwinState(self, equipment_id: str, state: dict) -> None:
        self._twin_states[equipment_id] = state

    def updatePhysicalState(self, equipment_id: str, state: dict) -> None:
        self._physical_states[equipment_id] = state

    def getSyncAuditLog(self) -> list[dict]:
        return list(self._sync_log)