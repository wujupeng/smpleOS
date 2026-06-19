from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..entities.continuous_airworthiness import (
    ADComplianceStatus,
    AirworthinessDirective,
    AirworthinessStatus,
    ContinuousAirworthinessRecord,
    MandatoryModification,
    ModificationStatus,
    RecurringInspection,
    SBExecutionStatus,
    ServiceBulletin,
)


class ContinuousAirworthinessService:
    def __init__(self) -> None:
        self._records: dict[str, ContinuousAirworthinessRecord] = {}
        self._by_aircraft: dict[str, str] = {}

    def create_record(
        self,
        tenant_id: str,
        aircraft_serial_number: str,
        certificate_id: str = "",
    ) -> ContinuousAirworthinessRecord:
        record = ContinuousAirworthinessRecord(
            tenant_id=tenant_id,
            aircraft_serial_number=aircraft_serial_number,
            certificate_id=certificate_id,
        )
        self._records[record.id] = record
        self._by_aircraft[aircraft_serial_number] = record.id
        return record

    def import_airworthiness_directive(
        self,
        aircraft_sn: str,
        ad_number: str,
        ad_title: str,
        issue_date: str,
        compliance_deadline: str,
        applicability: str = "",
    ) -> ContinuousAirworthinessRecord | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        ad = AirworthinessDirective(
            ad_number=ad_number,
            ad_title=ad_title,
            issue_date=issue_date,
            compliance_deadline=compliance_deadline,
            applicability=applicability,
        )

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if compliance_deadline < now_str:
            ad.compliance_status = ADComplianceStatus.OVERDUE

        record.add_airworthiness_directive(ad)
        return record

    def update_ad_compliance(
        self,
        aircraft_sn: str,
        ad_number: str,
        status: ADComplianceStatus,
    ) -> ContinuousAirworthinessRecord | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None
        record.update_ad_status(ad_number, status)
        return record

    def import_service_bulletin(
        self,
        aircraft_sn: str,
        sb_number: str,
        sb_title: str,
        issue_date: str,
        execution_deadline: str,
        priority: str = "medium",
    ) -> ContinuousAirworthinessRecord | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        sb = ServiceBulletin(
            sb_number=sb_number,
            sb_title=sb_title,
            issue_date=issue_date,
            execution_deadline=execution_deadline,
            priority=priority,
        )

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if execution_deadline < now_str:
            sb.execution_status = SBExecutionStatus.OVERDUE

        record.add_service_bulletin(sb)
        return record

    def update_sb_execution(
        self,
        aircraft_sn: str,
        sb_number: str,
        status: SBExecutionStatus,
    ) -> ContinuousAirworthinessRecord | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None
        record.update_sb_status(sb_number, status)
        return record

    def track_recurring_inspections(
        self,
        aircraft_sn: str,
        current_flight_hours: float,
    ) -> dict[str, Any] | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        due_soon: list[dict[str, Any]] = []
        overdue: list[dict[str, Any]] = []

        for insp in record.recurring_inspections:
            if insp.interval_type == "flight_hours":
                remaining = insp.next_due_at - current_flight_hours
                if remaining <= 0:
                    insp.status = "overdue"
                    overdue.append(insp.to_dict())
                elif remaining < insp.interval_value * 0.1:
                    insp.status = "due_soon"
                    due_soon.append(insp.to_dict())
                else:
                    insp.status = "ok"

        return {
            "aircraft_sn": aircraft_sn,
            "current_flight_hours": current_flight_hours,
            "due_soon_count": len(due_soon),
            "overdue_count": len(overdue),
            "due_soon": due_soon,
            "overdue": overdue,
        }

    def add_recurring_inspection(
        self,
        aircraft_sn: str,
        inspection_name: str,
        interval_type: str = "flight_hours",
        interval_value: float = 500.0,
        last_performed_at: float = 0.0,
    ) -> ContinuousAirworthinessRecord | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        inspection = RecurringInspection(
            inspection_id=str(uuid.uuid4()),
            inspection_name=inspection_name,
            interval_type=interval_type,
            interval_value=interval_value,
            last_performed_at=last_performed_at,
            next_due_at=last_performed_at + interval_value,
        )
        record.add_recurring_inspection(inspection)
        return record

    def assess_overall_airworthiness(
        self, aircraft_sn: str
    ) -> dict[str, Any] | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        status = record.assess_overall_status()

        ad_compliant = sum(1 for ad in record.airworthiness_directives if ad.compliance_status == ADComplianceStatus.COMPLIANT)
        ad_total = len(record.airworthiness_directives)
        sb_completed = sum(1 for sb in record.service_bulletins if sb.execution_status == SBExecutionStatus.COMPLETED)
        sb_total = len(record.service_bulletins)

        return {
            "aircraft_sn": aircraft_sn,
            "overall_status": status.value,
            "ad_compliance_rate": round(ad_compliant / max(ad_total, 1), 4),
            "sb_completion_rate": round(sb_completed / max(sb_total, 1), 4),
            "mandatory_mods_total": len(record.mandatory_modifications),
            "mandatory_mods_overdue": sum(1 for m in record.mandatory_modifications if m.status == ModificationStatus.OVERDUE),
            "inspections_total": len(record.recurring_inspections),
            "inspections_overdue": sum(1 for i in record.recurring_inspections if i.status == "overdue"),
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_airworthiness_review_report(
        self, aircraft_sn: str
    ) -> dict[str, Any] | None:
        record = self._get_by_aircraft(aircraft_sn)
        if not record:
            return None

        assessment = self.assess_overall_airworthiness(aircraft_sn)
        return {
            "report_type": "Airworthiness_Review_Report",
            "aircraft_serial_number": aircraft_sn,
            "certificate_id": record.certificate_id,
            "assessment": assessment,
            "airworthiness_directives": [ad.to_dict() for ad in record.airworthiness_directives],
            "service_bulletins": [sb.to_dict() for sb in record.service_bulletins],
            "mandatory_modifications": [m.to_dict() for m in record.mandatory_modifications],
            "recurring_inspections": [i.to_dict() for i in record.recurring_inspections],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_record(self, record_id: str) -> ContinuousAirworthinessRecord | None:
        return self._records.get(record_id)

    def get_by_aircraft(self, aircraft_sn: str) -> ContinuousAirworthinessRecord | None:
        return self._get_by_aircraft(aircraft_sn)

    def _get_by_aircraft(self, aircraft_sn: str) -> ContinuousAirworthinessRecord | None:
        record_id = self._by_aircraft.get(aircraft_sn)
        if not record_id:
            return None
        return self._records.get(record_id)