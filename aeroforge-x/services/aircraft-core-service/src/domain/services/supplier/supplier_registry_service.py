"""AeroForge-X v6.0 SupplierRegistryService

Manages supplier registration, approval workflow, quality rating,
suspension, and supply chain impact assessment.
REQ-SUP-001~006
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SupplierStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    SUSPENDED = "Suspended"
    DISQUALIFIED = "Disqualified"


class ApprovalStage(str, Enum):
    APPLICATION = "Application"
    CAPABILITY_ASSESSMENT = "CapabilityAssessment"
    AUDIT_SCHEDULING = "AuditScheduling"
    AUDIT_EXECUTION = "AuditExecution"
    APPROVED = "Approved"
    REJECTED = "Rejected"


@dataclass
class SupplierProfile:
    supplier_id: str
    company_name: str
    certifications: list[str] = field(default_factory=list)
    capability_matrix: dict = field(default_factory=dict)
    quality_history: dict = field(default_factory=dict)
    status: SupplierStatus = SupplierStatus.PENDING
    approved_parts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "company_name": self.company_name,
            "certifications": self.certifications,
            "capability_matrix": self.capability_matrix,
            "quality_history": self.quality_history,
            "status": self.status.value,
            "approved_parts": self.approved_parts,
        }


@dataclass
class SupplierQualityRating:
    on_time_delivery_rate: float = 0.0
    first_pass_yield: float = 0.0
    defect_rate: float = 0.0
    car_responsiveness: float = 0.0
    audit_findings_score: float = 0.0
    overall_rating: float = 0.0
    is_below_threshold: bool = False

    def to_dict(self) -> dict:
        return {
            "on_time_delivery_rate": self.on_time_delivery_rate,
            "first_pass_yield": self.first_pass_yield,
            "defect_rate": self.defect_rate,
            "car_responsiveness": self.car_responsiveness,
            "audit_findings_score": self.audit_findings_score,
            "overall_rating": self.overall_rating,
            "is_below_threshold": self.is_below_threshold,
        }


@dataclass
class SupplierApprovalWorkflow:
    supplier_id: str
    current_stage: ApprovalStage = ApprovalStage.APPLICATION
    stage_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "current_stage": self.current_stage.value,
            "stage_history": self.stage_history,
        }


@dataclass
class SuspensionResult:
    supplier_id: str
    reason: str
    affected_parts: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "reason": self.reason,
            "affected_parts": self.affected_parts,
            "recommended_actions": self.recommended_actions,
        }


@dataclass
class SupplyChainImpactReport:
    supplier_id: str
    affected_parts_count: int
    affected_boms: list[str] = field(default_factory=list)
    alternative_suppliers: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "affected_parts_count": self.affected_parts_count,
            "affected_boms": self.affected_boms,
            "alternative_suppliers": self.alternative_suppliers,
        }


class SupplierRegistryService:

    RATING_THRESHOLD = 70.0
    WEIGHT_OTD = 0.25
    WEIGHT_FPY = 0.25
    WEIGHT_DEFECT = 0.20
    WEIGHT_CAR = 0.15
    WEIGHT_AUDIT = 0.15

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._suppliers: dict[str, SupplierProfile] = {}
        self._ratings: dict[str, SupplierQualityRating] = {}
        self._workflows: dict[str, SupplierApprovalWorkflow] = {}
        self._bom_parts: dict[str, list[str]] = {}

    async def _persist_supplier(self, profile: SupplierProfile) -> None:
        if self._repo is None:
            return
        await self._repo.save_supplier(profile.to_dict())

    async def _persist_rating(self, supplier_id: str, rating: SupplierQualityRating) -> None:
        if self._repo is None:
            return
        await self._repo.save_rating({
            "rating_id": f"RAT-{supplier_id}",
            "supplier_id": supplier_id,
            **rating.to_dict(),
        })

    async def registerSupplier(self, profile: SupplierProfile) -> SupplierProfile:
        if profile.supplier_id in self._suppliers:
            raise ValueError(f"Supplier already registered: {profile.supplier_id}")

        self._suppliers[profile.supplier_id] = profile
        self._ratings[profile.supplier_id] = SupplierQualityRating()
        self._workflows[profile.supplier_id] = SupplierApprovalWorkflow(
            supplier_id=profile.supplier_id
        )
        await self._persist_supplier(profile)
        return profile

    async def approveSupplierWorkflow(self, supplier_id: str) -> SupplierApprovalWorkflow:
        if supplier_id not in self._workflows:
            raise ValueError(f"Supplier workflow not found: {supplier_id}")

        workflow = self._workflows[supplier_id]
        stages = list(ApprovalStage)
        current_idx = stages.index(workflow.current_stage)

        if current_idx >= len(stages) - 2:
            raise ValueError("Workflow already completed or at final stage")

        next_stage = stages[current_idx + 1]
        workflow.stage_history.append(
            {"from": workflow.current_stage.value, "to": next_stage.value}
        )
        workflow.current_stage = next_stage

        if next_stage == ApprovalStage.APPROVED:
            supplier = self._suppliers[supplier_id]
            supplier.status = SupplierStatus.APPROVED
            await self._persist_supplier(supplier)
        elif next_stage == ApprovalStage.REJECTED:
            supplier = self._suppliers[supplier_id]
            supplier.status = SupplierStatus.DISQUALIFIED
            await self._persist_supplier(supplier)

        return workflow

    async def computeQualityRating(self, supplier_id: str) -> SupplierQualityRating:
        if supplier_id not in self._suppliers:
            raise ValueError(f"Supplier not found: {supplier_id}")

        rating = self._ratings.get(supplier_id, SupplierQualityRating())

        otd_score = rating.on_time_delivery_rate * 100
        fpy_score = rating.first_pass_yield * 100
        defect_score = max(0, (1 - rating.defect_rate) * 100)
        car_score = rating.car_responsiveness * 100
        audit_score = rating.audit_findings_score * 100

        overall = (
            otd_score * self.WEIGHT_OTD
            + fpy_score * self.WEIGHT_FPY
            + defect_score * self.WEIGHT_DEFECT
            + car_score * self.WEIGHT_CAR
            + audit_score * self.WEIGHT_AUDIT
        )

        rating.overall_rating = round(overall, 2)
        rating.is_below_threshold = overall < self.RATING_THRESHOLD
        self._ratings[supplier_id] = rating
        await self._persist_rating(supplier_id, rating)

        return rating

    async def suspendSupplier(
        self, supplier_id: str, reason: str
    ) -> SuspensionResult:
        if supplier_id not in self._suppliers:
            raise ValueError(f"Supplier not found: {supplier_id}")

        supplier = self._suppliers[supplier_id]
        supplier.status = SupplierStatus.SUSPENDED
        await self._persist_supplier(supplier)

        affected_parts = list(supplier.approved_parts)
        recommended = []
        if affected_parts:
            recommended.append("Identify alternative suppliers for affected parts")
            recommended.append("Enhance inspection for in-stock parts")

        return SuspensionResult(
            supplier_id=supplier_id,
            reason=reason,
            affected_parts=affected_parts,
            recommended_actions=recommended,
        )

    def assessSupplyChainImpact(self, supplier_id: str) -> SupplyChainImpactReport:
        if supplier_id not in self._suppliers:
            raise ValueError(f"Supplier not found: {supplier_id}")

        supplier = self._suppliers[supplier_id]
        affected_parts = supplier.approved_parts
        affected_boms = []

        for part in affected_parts:
            boms = self._bom_parts.get(part, [])
            affected_boms.extend(boms)

        return SupplyChainImpactReport(
            supplier_id=supplier_id,
            affected_parts_count=len(affected_parts),
            affected_boms=list(set(affected_boms)),
        )

    async def updateRatingMetrics(
        self,
        supplier_id: str,
        on_time_delivery_rate: float = None,
        first_pass_yield: float = None,
        defect_rate: float = None,
        car_responsiveness: float = None,
        audit_findings_score: float = None,
    ) -> SupplierQualityRating:
        if supplier_id not in self._ratings:
            raise ValueError(f"Rating not found: {supplier_id}")

        rating = self._ratings[supplier_id]
        if on_time_delivery_rate is not None:
            rating.on_time_delivery_rate = on_time_delivery_rate
        if first_pass_yield is not None:
            rating.first_pass_yield = first_pass_yield
        if defect_rate is not None:
            rating.defect_rate = defect_rate
        if car_responsiveness is not None:
            rating.car_responsiveness = car_responsiveness
        if audit_findings_score is not None:
            rating.audit_findings_score = audit_findings_score

        return await self.computeQualityRating(supplier_id)

    def _supplier_from_dict(self, data: dict) -> SupplierProfile:
        return SupplierProfile(
            supplier_id=data["supplier_id"],
            company_name=data.get("company_name", ""),
            certifications=data.get("certifications", []),
            capability_matrix=data.get("capability_matrix", {}),
            quality_history=data.get("quality_history", {}),
            status=SupplierStatus(data.get("status", "Pending")),
            approved_parts=data.get("approved_parts", []),
        )

    async def getSupplier(self, supplier_id: str) -> Optional[SupplierProfile]:
        if supplier_id in self._suppliers:
            return self._suppliers[supplier_id]
        if self._repo is not None:
            data = await self._repo.get_supplier(supplier_id)
            if data is not None:
                profile = self._supplier_from_dict(data)
                self._suppliers[supplier_id] = profile
                return profile
        return None