from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aeroforge_common.domain.base import AggregateRoot


class AirworthinessStatus(str, Enum):
    AIRWORTHY = "airworthy"
    CONDITIONALLY_AIRWORTHY = "conditionally_airworthy"
    UNAIRWORTHY = "unairworthy"


class ADComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    OVERDUE = "overdue"


class SBExecutionStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"
    NOT_APPLICABLE = "not_applicable"
    OVERDUE = "overdue"


class ModificationStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"


@dataclass
class AirworthinessDirective:
    ad_number: str
    ad_title: str
    issue_date: str
    compliance_deadline: str
    applicability: str = ""
    compliance_status: ADComplianceStatus = ADComplianceStatus.PENDING
    compliance_date: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ad_number": self.ad_number,
            "ad_title": self.ad_title,
            "issue_date": self.issue_date,
            "compliance_deadline": self.compliance_deadline,
            "applicability": self.applicability,
            "compliance_status": self.compliance_status.value,
            "compliance_date": self.compliance_date,
            "notes": self.notes,
        }


@dataclass
class ServiceBulletin:
    sb_number: str
    sb_title: str
    issue_date: str
    execution_deadline: str
    priority: str = "medium"
    execution_status: SBExecutionStatus = SBExecutionStatus.NOT_STARTED
    execution_date: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sb_number": self.sb_number,
            "sb_title": self.sb_title,
            "issue_date": self.issue_date,
            "execution_deadline": self.execution_deadline,
            "priority": self.priority,
            "execution_status": self.execution_status.value,
            "execution_date": self.execution_date,
            "notes": self.notes,
        }


@dataclass
class MandatoryModification:
    mod_id: str
    mod_title: str
    required_by: str
    status: ModificationStatus = ModificationStatus.SCHEDULED
    completed_date: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mod_id": self.mod_id,
            "mod_title": self.mod_title,
            "required_by": self.required_by,
            "status": self.status.value,
            "completed_date": self.completed_date,
            "notes": self.notes,
        }


@dataclass
class RecurringInspection:
    inspection_id: str
    inspection_name: str
    interval_type: str = "flight_hours"
    interval_value: float = 500.0
    last_performed_at: float = 0.0
    last_performed_date: str = ""
    next_due_at: float = 500.0
    next_due_date: str = ""
    status: str = "due_soon"

    def to_dict(self) -> dict[str, Any]:
        return {
            "inspection_id": self.inspection_id,
            "inspection_name": self.inspection_name,
            "interval_type": self.interval_type,
            "interval_value": self.interval_value,
            "last_performed_at": self.last_performed_at,
            "last_performed_date": self.last_performed_date,
            "next_due_at": self.next_due_at,
            "next_due_date": self.next_due_date,
            "status": self.status,
        }


class ContinuousAirworthinessRecord(AggregateRoot):
    def __init__(
        self,
        tenant_id: str,
        aircraft_serial_number: str,
        certificate_id: str = "",
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self.aircraft_serial_number = aircraft_serial_number
        self.certificate_id = certificate_id
        self.airworthiness_directives: list[AirworthinessDirective] = []
        self.service_bulletins: list[ServiceBulletin] = []
        self.mandatory_modifications: list[MandatoryModification] = []
        self.recurring_inspections: list[RecurringInspection] = []
        self.overall_status = AirworthinessStatus.AIRWORTHY
        self.next_inspection_due: str = ""
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_airworthiness_directive(self, ad: AirworthinessDirective) -> None:
        self.airworthiness_directives.append(ad)
        self.updated_at = datetime.now(timezone.utc)

    def update_ad_status(self, ad_number: str, status: ADComplianceStatus) -> bool:
        for ad in self.airworthiness_directives:
            if ad.ad_number == ad_number:
                ad.compliance_status = status
                if status == ADComplianceStatus.COMPLIANT:
                    ad.compliance_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def add_service_bulletin(self, sb: ServiceBulletin) -> None:
        self.service_bulletins.append(sb)
        self.updated_at = datetime.now(timezone.utc)

    def update_sb_status(self, sb_number: str, status: SBExecutionStatus) -> bool:
        for sb in self.service_bulletins:
            if sb.sb_number == sb_number:
                sb.execution_status = status
                if status == SBExecutionStatus.COMPLETED:
                    sb.execution_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def add_mandatory_modification(self, mod: MandatoryModification) -> None:
        self.mandatory_modifications.append(mod)
        self.updated_at = datetime.now(timezone.utc)

    def add_recurring_inspection(self, inspection: RecurringInspection) -> None:
        self.recurring_inspections.append(inspection)
        self.updated_at = datetime.now(timezone.utc)

    def update_inspection_status(
        self, inspection_id: str, current_flight_hours: float
    ) -> bool:
        for insp in self.recurring_inspections:
            if insp.inspection_id == inspection_id:
                insp.last_performed_at = current_flight_hours
                insp.last_performed_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                insp.next_due_at = current_flight_hours + insp.interval_value
                insp.status = "completed"
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False

    def assess_overall_status(self) -> AirworthinessStatus:
        overdue_ads = any(
            ad.compliance_status in (ADComplianceStatus.NON_COMPLIANT, ADComplianceStatus.OVERDUE)
            for ad in self.airworthiness_directives
        )
        overdue_sbs = any(
            sb.execution_status == SBExecutionStatus.OVERDUE
            for sb in self.service_bulletins
        )
        overdue_mods = any(
            mod.status == ModificationStatus.OVERDUE
            for mod in self.mandatory_modifications
        )

        if overdue_ads or overdue_mods:
            self.overall_status = AirworthinessStatus.UNAIRWORTHY
        elif overdue_sbs:
            self.overall_status = AirworthinessStatus.CONDITIONALLY_AIRWORTHY
        else:
            self.overall_status = AirworthinessStatus.AIRWORTHY

        self.updated_at = datetime.now(timezone.utc)
        return self.overall_status

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "aircraft_serial_number": self.aircraft_serial_number,
            "certificate_id": self.certificate_id,
            "overall_status": self.overall_status.value,
            "next_inspection_due": self.next_inspection_due,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_detail_dict(self) -> dict[str, Any]:
        base = self.to_dict()
        base.update({
            "airworthiness_directives": [ad.to_dict() for ad in self.airworthiness_directives],
            "service_bulletins": [sb.to_dict() for sb in self.service_bulletins],
            "mandatory_modifications": [m.to_dict() for m in self.mandatory_modifications],
            "recurring_inspections": [i.to_dict() for i in self.recurring_inspections],
            "summary": {
                "ads_total": len(self.airworthiness_directives),
                "ads_compliant": sum(1 for ad in self.airworthiness_directives if ad.compliance_status == ADComplianceStatus.COMPLIANT),
                "sbs_total": len(self.service_bulletins),
                "sbs_completed": sum(1 for sb in self.service_bulletins if sb.execution_status == SBExecutionStatus.COMPLETED),
                "inspections_total": len(self.recurring_inspections),
                "inspections_due_soon": sum(1 for i in self.recurring_inspections if i.status == "due_soon"),
            },
        })
        return base