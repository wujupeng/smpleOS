from __future__ import annotations

import logging
from typing import Any

from src.domain.entities.v1.compliance_item import ComplianceItem, ComplianceStatus

logger = logging.getLogger(__name__)


class VerificationResult:
    def __init__(self, item_id: str, verification_type: str):
        self.item_id = item_id
        self.verification_type = verification_type
        self.result: str = "pending"
        self.evidence_documents: list[str] = []
        self.findings: list[str] = []
        self.is_compliant: bool = False
        self.evidence_gap: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "verification_type": self.verification_type,
            "result": self.result,
            "evidence_documents": self.evidence_documents,
            "findings": self.findings,
            "is_compliant": self.is_compliant,
            "evidence_gap": self.evidence_gap,
        }


class ComplianceVerificationService:
    def __init__(self, event_publisher: Any | None = None):
        self._event_publisher = event_publisher
        self._verifications: dict[str, VerificationResult] = {}
        self._locked_baselines: set[str] = set()

    async def _publish_event(self, subject: str, data: dict[str, Any]) -> None:
        if self._event_publisher:
            await self._event_publisher.publish(subject, data)

    def lock_baseline(self, plan_id: str) -> None:
        self._locked_baselines.add(plan_id)

    def unlock_baseline(self, plan_id: str) -> None:
        self._locked_baselines.discard(plan_id)

    def verify_design_compliance(self, item_id: str, design_data: dict[str, Any], compliance_item: ComplianceItem | None = None) -> VerificationResult:
        result = VerificationResult(item_id, "design")
        required_evidence = ["design_report", "analysis_results"]
        provided_evidence = design_data.get("evidence_documents", [])
        result.evidence_documents = provided_evidence

        missing = [e for e in required_evidence if not any(e in doc for doc in provided_evidence)]
        if missing:
            result.findings.append(f"Missing required evidence: {', '.join(missing)}")
            result.evidence_gap = True
            result.result = "evidence_gap"
        else:
            design_rules_passed = design_data.get("design_rules_passed", True)
            cae_results_acceptable = design_data.get("cae_results_acceptable", True)
            if design_rules_passed and cae_results_acceptable:
                result.is_compliant = True
                result.result = "compliant"
                result.evidence_gap = False
            else:
                result.is_compliant = False
                result.result = "non_compliant"
                if not design_rules_passed:
                    result.findings.append("Design rule violations detected")
                if not cae_results_acceptable:
                    result.findings.append("CAE results outside acceptable limits")

        self._verifications[f"{item_id}_design"] = result
        return result

    def verify_manufacturing_compliance(self, item_id: str, mfg_data: dict[str, Any]) -> VerificationResult:
        result = VerificationResult(item_id, "manufacturing")
        required_evidence = ["process_qualification", "ndt_results"]
        provided_evidence = mfg_data.get("evidence_documents", [])
        result.evidence_documents = provided_evidence

        missing = [e for e in required_evidence if not any(e in doc for doc in provided_evidence)]
        if missing:
            result.findings.append(f"Missing required evidence: {', '.join(missing)}")
            result.evidence_gap = True
            result.result = "evidence_gap"
        else:
            dimensions_in_tolerance = mfg_data.get("dimensions_in_tolerance", True)
            ndt_passed = mfg_data.get("ndt_passed", True)
            if dimensions_in_tolerance and ndt_passed:
                result.is_compliant = True
                result.result = "compliant"
                result.evidence_gap = False
            else:
                result.is_compliant = False
                result.result = "non_compliant"
                if not dimensions_in_tolerance:
                    result.findings.append("Out-of-tolerance dimensions detected")
                if not ndt_passed:
                    result.findings.append("NDT inspection failures detected")

        self._verifications[f"{item_id}_manufacturing"] = result
        return result

    def verify_test_compliance(self, item_id: str, test_data: dict[str, Any]) -> VerificationResult:
        result = VerificationResult(item_id, "test")
        required_evidence = ["test_report", "test_data"]
        provided_evidence = test_data.get("evidence_documents", [])
        result.evidence_documents = provided_evidence

        missing = [e for e in required_evidence if not any(e in doc for doc in provided_evidence)]
        if missing:
            result.findings.append(f"Missing required evidence: {', '.join(missing)}")
            result.evidence_gap = True
            result.result = "evidence_gap"
        else:
            test_passed = test_data.get("test_passed", True)
            within_envelope = test_data.get("within_flight_envelope", True)
            if test_passed and within_envelope:
                result.is_compliant = True
                result.result = "compliant"
                result.evidence_gap = False
            else:
                result.is_compliant = False
                result.result = "non_compliant"
                if not test_passed:
                    result.findings.append("Test did not pass acceptance criteria")
                if not within_envelope:
                    result.findings.append("Test point outside flight envelope")

        self._verifications[f"{item_id}_test"] = result
        return result

    def link_evidence(self, item_id: str, evidence_ref: str, compliance_item: ComplianceItem | None = None) -> dict[str, Any]:
        if compliance_item:
            compliance_item.link_evidence(evidence_ref)
        return {"item_id": item_id, "evidence_ref": evidence_ref, "linked": True, "evidence_gap": compliance_item.evidence_gap if compliance_item else True}

    def generate_verification_report(self, plan_id: str) -> dict[str, Any]:
        plan_verifications = {k: v for k, v in self._verifications.items() if not plan_id or True}
        return {
            "plan_id": plan_id,
            "total_verifications": len(plan_verifications),
            "compliant": sum(1 for v in plan_verifications.values() if v.is_compliant),
            "non_compliant": sum(1 for v in plan_verifications.values() if v.result == "non_compliant"),
            "evidence_gaps": sum(1 for v in plan_verifications.values() if v.evidence_gap),
            "verifications": [v.to_dict() for v in plan_verifications.values()],
        }