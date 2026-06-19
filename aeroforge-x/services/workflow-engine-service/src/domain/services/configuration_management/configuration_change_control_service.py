"""AeroForge-X v6.0 ConfigurationChangeControlService

Manages configuration change control workflow: request submission, impact analysis,
approval, implementation, and verification.
REQ-CFG-018~022
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChangeClass(str, Enum):
    CLASS_I = "ClassI"
    CLASS_II = "ClassII"


class ChangeRequestStatus(str, Enum):
    SUBMITTED = "Submitted"
    IMPACT_ANALYZED = "ImpactAnalyzed"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"


@dataclass
class ConfigurationChangeRequest:
    request_id: str
    block_id: str
    change_class: ChangeClass
    change_type: str
    description: str
    requested_by: str
    affected_items: list[dict] = field(default_factory=list)
    impact_analysis: Optional[dict] = None
    approval: Optional[dict] = None
    status: ChangeRequestStatus = ChangeRequestStatus.SUBMITTED
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "block_id": self.block_id,
            "change_class": self.change_class.value,
            "change_type": self.change_type,
            "description": self.description,
            "requested_by": self.requested_by,
            "affected_items": self.affected_items,
            "impact_analysis": self.impact_analysis,
            "approval": self.approval,
            "status": self.status.value,
            "created_at": self.created_at,
        }


@dataclass
class ImpactAnalysisResult:
    request_id: str
    affected_design_items: list[str] = field(default_factory=list)
    affected_mfg_items: list[str] = field(default_factory=list)
    affected_op_items: list[str] = field(default_factory=list)
    affected_sns: list[str] = field(default_factory=list)
    estimated_propagation_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "affected_design_items": self.affected_design_items,
            "affected_mfg_items": self.affected_mfg_items,
            "affected_op_items": self.affected_op_items,
            "affected_sns": self.affected_sns,
            "estimated_propagation_time_ms": self.estimated_propagation_time_ms,
        }


@dataclass
class ChangeApproval:
    request_id: str
    approver: str
    change_class: ChangeClass
    approved: bool
    approved_at: str = ""
    comments: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "approver": self.approver,
            "change_class": self.change_class.value,
            "approved": self.approved,
            "approved_at": self.approved_at,
            "comments": self.comments,
        }


@dataclass
class ChangeImplementationResult:
    request_id: str
    items_updated: int
    propagation_completed: bool
    propagation_duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "items_updated": self.items_updated,
            "propagation_completed": self.propagation_completed,
            "propagation_duration_ms": self.propagation_duration_ms,
            "errors": self.errors,
        }


@dataclass
class ChangeVerificationResult:
    request_id: str
    is_verified: bool
    verification_details: list[dict] = field(default_factory=list)
    baseline_updated: bool = False

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "is_verified": self.is_verified,
            "verification_details": self.verification_details,
            "baseline_updated": self.baseline_updated,
        }


class ConfigurationChangeControlService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._requests: dict[str, ConfigurationChangeRequest] = {}
        self._impact_analyses: dict[str, ImpactAnalysisResult] = {}
        self._approvals: dict[str, ChangeApproval] = {}
        self._audit_trail: list[dict] = []

    def submitChangeRequest(
        self, request: ConfigurationChangeRequest
    ) -> ConfigurationChangeRequest:
        if request.request_id in self._requests:
            raise ValueError(f"Change request already exists: {request.request_id}")

        request.status = ChangeRequestStatus.SUBMITTED
        self._requests[request.request_id] = request
        self._audit_trail.append(
            {
                "action": "Submitted",
                "request_id": request.request_id,
                "requested_by": request.requested_by,
            }
        )
        return request

    def performImpactAnalysis(
        self, request_id: str
    ) -> ImpactAnalysisResult:
        if request_id not in self._requests:
            raise ValueError(f"Change request not found: {request_id}")

        request = self._requests[request_id]
        affected_design = []
        affected_mfg = []
        affected_op = []
        affected_sns = []

        for item in request.affected_items:
            item_id = item.get("item_id", "")
            views = item.get("affected_views", [])
            if "Design" in views or not views:
                affected_design.append(item_id)
            if "Manufacturing" in views or not views:
                affected_mfg.append(item_id)
            if "Operational" in views or not views:
                affected_op.append(item_id)
            sns = item.get("affected_sns", [])
            affected_sns.extend(sns)

        result = ImpactAnalysisResult(
            request_id=request_id,
            affected_design_items=affected_design,
            affected_mfg_items=affected_mfg,
            affected_op_items=affected_op,
            affected_sns=list(set(affected_sns)),
            estimated_propagation_time_ms=len(affected_design) * 100.0,
        )

        request.impact_analysis = result.to_dict()
        request.status = ChangeRequestStatus.IMPACT_ANALYZED
        self._impact_analyses[request_id] = result
        self._audit_trail.append(
            {
                "action": "ImpactAnalyzed",
                "request_id": request_id,
                "affected_items_count": len(affected_design),
            }
        )
        return result

    def approveChangeRequest(
        self, request_id: str, approver: str, change_class: ChangeClass
    ) -> ChangeApproval:
        if request_id not in self._requests:
            raise ValueError(f"Change request not found: {request_id}")

        request = self._requests[request_id]

        if request.change_class == ChangeClass.CLASS_I and not approver.startswith("Chief"):
            raise ValueError("Class I changes require Chief Engineer approval")
        if request.change_class == ChangeClass.CLASS_II and not approver.startswith("Lead"):
            raise ValueError("Class II changes require Lead Engineer approval")

        approval = ChangeApproval(
            request_id=request_id,
            approver=approver,
            change_class=change_class,
            approved=True,
        )

        request.approval = approval.to_dict()
        request.status = ChangeRequestStatus.APPROVED
        self._approvals[request_id] = approval
        self._audit_trail.append(
            {
                "action": "Approved",
                "request_id": request_id,
                "approver": approver,
                "change_class": change_class.value,
            }
        )
        return approval

    def implementChange(
        self, request_id: str
    ) -> ChangeImplementationResult:
        if request_id not in self._requests:
            raise ValueError(f"Change request not found: {request_id}")

        request = self._requests[request_id]
        if request.status != ChangeRequestStatus.APPROVED:
            raise ValueError(f"Change request must be approved before implementation: {request_id}")

        items_updated = len(request.affected_items)
        result = ChangeImplementationResult(
            request_id=request_id,
            items_updated=items_updated,
            propagation_completed=True,
            propagation_duration_ms=items_updated * 100.0,
        )

        request.status = ChangeRequestStatus.IMPLEMENTED
        self._audit_trail.append(
            {
                "action": "Implemented",
                "request_id": request_id,
                "items_updated": items_updated,
            }
        )
        return result

    def verifyChange(
        self, request_id: str
    ) -> ChangeVerificationResult:
        if request_id not in self._requests:
            raise ValueError(f"Change request not found: {request_id}")

        request = self._requests[request_id]
        if request.status != ChangeRequestStatus.IMPLEMENTED:
            raise ValueError(f"Change request must be implemented before verification: {request_id}")

        verification_details = []
        for item in request.affected_items:
            verification_details.append(
                {
                    "item_id": item.get("item_id", ""),
                    "verified": True,
                    "verification_method": "Automated",
                }
            )

        result = ChangeVerificationResult(
            request_id=request_id,
            is_verified=True,
            verification_details=verification_details,
            baseline_updated=True,
        )

        request.status = ChangeRequestStatus.VERIFIED
        self._audit_trail.append(
            {
                "action": "Verified",
                "request_id": request_id,
                "is_verified": True,
                "baseline_updated": True,
            }
        )
        return result

    def getAuditTrail(self) -> list[dict]:
        return list(self._audit_trail)

    def getChangeRequest(self, request_id: str) -> Optional[ConfigurationChangeRequest]:
        return self._requests.get(request_id)