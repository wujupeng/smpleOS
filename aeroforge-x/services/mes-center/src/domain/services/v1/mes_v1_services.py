from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.domain.entities.v1.traveler_record import TravelerRecord, TravelerStatus, TemperatureReading
from src.domain.entities.v1.ndt_inspection import NDTInspection, NDTMethod, NDTResult, NDTStatus
from src.domain.entities.v1.tool_calibration import ToolCalibration, CalibrationStatus


class TravelerService:
    def create_traveler(self, work_order_id: str, serial_number: str,
                        process_step: str, operator_id: str | None = None,
                        curing_oven: str | None = None) -> TravelerRecord:
        return TravelerRecord(
            work_order_id=work_order_id,
            serial_number=serial_number,
            process_step=process_step,
            operator_id=operator_id,
            curing_oven=curing_oven,
        )

    def record_temperature_profile(self, traveler: TravelerRecord, temperature_c: Decimal,
                                    target_temp_c: Decimal, tolerance_c: Decimal = Decimal("5"),
                                    duration_s: Decimal = Decimal("0")) -> TemperatureReading:
        return traveler.record_temperature(temperature_c, target_temp_c, tolerance_c, duration_s)

    def confirm_traveler(self, traveler: TravelerRecord, inspector_id: str) -> None:
        traveler.confirm(inspector_id)

    def finalize_traveler(self, traveler: TravelerRecord) -> None:
        traveler.finalize()


class NDTService:
    def create_inspection(self, serial_number: str, method: str,
                          traveler_ref: str | None = None,
                          tool_calibration_ref: str | None = None,
                          tool_calibration_valid: bool = True) -> NDTInspection:
        return NDTInspection(
            serial_number=serial_number,
            inspection_method=method,
            traveler_ref=traveler_ref,
            tool_calibration_ref=tool_calibration_ref,
            tool_calibration_valid=tool_calibration_valid,
        )

    def record_result(self, inspection: NDTInspection, result: str,
                       defect_description: str | None = None,
                       inspector_id: str | None = None) -> None:
        inspection.record_result(result, defect_description, inspector_id)

    def judge_result(self, inspection: NDTInspection) -> dict[str, Any]:
        if inspection.result == NDTResult.ACCEPTABLE:
            return {"judgment": "pass", "action": "release"}
        elif inspection.result == NDTResult.MARGINAL:
            return {"judgment": "review_required", "action": "escalate_to_level_ii"}
        elif inspection.result == NDTResult.UNACCEPTABLE:
            return {"judgment": "fail", "action": "quarantine_and_investigate"}
        return {"judgment": "pending", "action": "await_result"}


class ToolCalibrationService:
    def __init__(self):
        self._calibrations: dict[str, ToolCalibration] = {}

    def record_calibration(self, tool_id: str, tool_name: str, calibration_date: str,
                            next_due_date: str, result: str = "pass",
                            uncertainty: float | None = None,
                            certificate_ref: str | None = None,
                            calibrated_by: str | None = None) -> ToolCalibration:
        from datetime import date as date_type
        cal = ToolCalibration(
            tool_id=tool_id,
            tool_name=tool_name,
            calibration_date=date_type.fromisoformat(calibration_date),
            next_due_date=date_type.fromisoformat(next_due_date),
            result=result,
            uncertainty=Decimal(str(uncertainty)) if uncertainty else None,
            certificate_ref=certificate_ref,
            calibrated_by=calibrated_by,
        )
        cal.check_expiry()
        self._calibrations[cal.calibration_id] = cal
        return cal

    def check_calibration_expiry(self, warning_days: int = 7) -> list[ToolCalibration]:
        expiring = []
        for cal in self._calibrations.values():
            cal.check_expiry(warning_days)
            if cal.status in (CalibrationStatus.EXPIRING_SOON, CalibrationStatus.EXPIRED):
                expiring.append(cal)
        return expiring

    def trace_affected_work_orders(self, calibration_id: str) -> list[str]:
        cal = self._calibrations.get(calibration_id)
        if not cal:
            return []
        return cal.invalidate("Post-calibration review found invalid")

    def is_tool_usable(self, tool_id: str) -> bool:
        for cal in self._calibrations.values():
            if cal.tool_id == tool_id:
                return cal.is_usable()
        return False