"""AeroForge-X v6.0 NDTIntegrationService

Manages NDT (Non-Destructive Testing) data integration:
multi-method data import, reject/conditional result handling,
and statistical analysis.
REQ-SUP-013~018
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NDTMethod(str, Enum):
    UT = "UT"
    RT = "RT"
    PT = "PT"
    MT = "MT"
    ET = "ET"


class NDTResult(str, Enum):
    ACCEPT = "Accept"
    REJECT = "Reject"
    CONDITIONAL = "Conditional"


@dataclass
class NDTRecord:
    ndt_id: str
    part_id: str
    inspection_method: NDTMethod
    equipment_calibration_data: dict = field(default_factory=dict)
    inspection_procedure_ref: str = ""
    inspector_certification: str = ""
    acceptance_criteria: str = ""
    result: NDTResult = NDTResult.ACCEPT
    linked_lot_id: str = ""
    linked_operation_id: str = ""
    defects_found: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ndt_id": self.ndt_id,
            "part_id": self.part_id,
            "inspection_method": self.inspection_method.value,
            "equipment_calibration_data": self.equipment_calibration_data,
            "inspection_procedure_ref": self.inspection_procedure_ref,
            "inspector_certification": self.inspector_certification,
            "acceptance_criteria": self.acceptance_criteria,
            "result": self.result.value,
            "linked_lot_id": self.linked_lot_id,
            "linked_operation_id": self.linked_operation_id,
            "defects_found": self.defects_found,
        }


@dataclass
class FRACASLinkResult:
    ndt_id: str
    fracas_report_id: str
    disposition_process_started: bool

    def to_dict(self) -> dict:
        return {
            "ndt_id": self.ndt_id,
            "fracas_report_id": self.fracas_report_id,
            "disposition_process_started": self.disposition_process_started,
        }


@dataclass
class NDTStatistics:
    defect_rate_by_supplier: dict = field(default_factory=dict)
    method_effectiveness: dict = field(default_factory=dict)
    false_call_rate: dict = field(default_factory=dict)
    total_records: int = 0
    accept_count: int = 0
    reject_count: int = 0
    conditional_count: int = 0

    def to_dict(self) -> dict:
        return {
            "defect_rate_by_supplier": self.defect_rate_by_supplier,
            "method_effectiveness": self.method_effectiveness,
            "false_call_rate": self.false_call_rate,
            "total_records": self.total_records,
            "accept_count": self.accept_count,
            "reject_count": self.reject_count,
            "conditional_count": self.conditional_count,
        }


@dataclass
class NDTFilter:
    supplier_id: str = ""
    method: NDTMethod | None = None
    result: NDTResult | None = None
    part_id: str = ""


class NDTIntegrationService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._records: dict[str, NDTRecord] = {}
        self._conditional_reviews: dict[str, dict] = {}

    def importNDTRecord(self, ndt_data: NDTRecord) -> NDTRecord:
        if ndt_data.ndt_id in self._records:
            raise ValueError(f"NDT record already exists: {ndt_data.ndt_id}")

        self._records[ndt_data.ndt_id] = ndt_data

        if ndt_data.result == NDTResult.REJECT:
            self.handleRejectResult(ndt_data.ndt_id)
        elif ndt_data.result == NDTResult.CONDITIONAL:
            self.handleConditionalResult(ndt_data.ndt_id)

        return ndt_data

    def handleRejectResult(self, ndt_id: str) -> FRACASLinkResult:
        if ndt_id not in self._records:
            raise ValueError(f"NDT record not found: {ndt_id}")

        fracas_id = f"FRACAS-NDT-{uuid.uuid4().hex[:8]}"

        return FRACASLinkResult(
            ndt_id=ndt_id,
            fracas_report_id=fracas_id,
            disposition_process_started=True,
        )

    def handleConditionalResult(self, ndt_id: str) -> dict:
        if ndt_id not in self._records:
            raise ValueError(f"NDT record not found: {ndt_id}")

        self._conditional_reviews[ndt_id] = {
            "ndt_id": ndt_id,
            "status": "PendingEngineeringReview",
            "disposition_decision": None,
        }

        return {
            "ndt_id": ndt_id,
            "flagged_for_review": True,
            "review_status": "PendingEngineeringReview",
        }

    def resolveConditionalResult(self, ndt_id: str, disposition: str) -> dict:
        if ndt_id not in self._conditional_reviews:
            raise ValueError(f"Conditional review not found: {ndt_id}")

        review = self._conditional_reviews[ndt_id]
        review["disposition_decision"] = disposition
        review["status"] = "Resolved"

        return review

    def computeNDTStatistics(self, ndt_filter: NDTFilter | None = None) -> NDTStatistics:
        records = list(self._records.values())

        if ndt_filter:
            if ndt_filter.supplier_id:
                records = [r for r in records if r.linked_lot_id.startswith(ndt_filter.supplier_id)]
            if ndt_filter.method:
                records = [r for r in records if r.inspection_method == ndt_filter.method]
            if ndt_filter.result:
                records = [r for r in records if r.result == ndt_filter.result]
            if ndt_filter.part_id:
                records = [r for r in records if r.part_id == ndt_filter.part_id]

        stats = NDTStatistics(
            total_records=len(records),
            accept_count=sum(1 for r in records if r.result == NDTResult.ACCEPT),
            reject_count=sum(1 for r in records if r.result == NDTResult.REJECT),
            conditional_count=sum(1 for r in records if r.result == NDTResult.CONDITIONAL),
        )

        method_counts: dict[str, dict[str, int]] = {}
        for r in records:
            method = r.inspection_method.value
            if method not in method_counts:
                method_counts[method] = {"total": 0, "reject": 0}
            method_counts[method]["total"] += 1
            if r.result == NDTResult.REJECT:
                method_counts[method]["reject"] += 1

        stats.method_effectiveness = {
            m: {"detection_rate": c["reject"] / c["total"] if c["total"] > 0 else 0}
            for m, c in method_counts.items()
        }

        return stats

    def getRecord(self, ndt_id: str) -> Optional[NDTRecord]:
        return self._records.get(ndt_id)