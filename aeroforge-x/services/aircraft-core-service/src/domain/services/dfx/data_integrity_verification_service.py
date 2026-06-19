"""AeroForge-X v6.0 DataIntegrityVerificationService

Verifies data integrity across v6.0 Programs:
- Configuration baseline consistency
- Certification evidence immutability
- Supplier audit trail integrity
- Shop floor data quality
- Material lot verifiability
- UQ reproducibility

REQ-DFX-V6-033~038, REQ-NFR-V6-025
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntegrityCheckType(str, Enum):
    BASELINE_CONSISTENCY = "BaselineConsistency"
    EVIDENCE_IMMUTABILITY = "EvidenceImmutability"
    SUPPLIER_AUDIT_TRAIL = "SupplierAuditTrail"
    SHOP_FLOOR_DATA_QUALITY = "ShopFloorDataQuality"
    MATERIAL_LOT_VERIFIABILITY = "MaterialLotVerifiability"
    UQ_REPRODUCIBILITY = "UQReproducibility"


class IntegrityStatus(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    WARNING = "Warning"
    NOT_CHECKED = "NotChecked"


@dataclass
class IntegrityCheckResult:
    check_id: str
    check_type: IntegrityCheckType
    resource_id: str
    status: IntegrityStatus
    details: dict = field(default_factory=dict)
    violations: list[dict] = field(default_factory=list)
    checksum: str = ""
    expected_checksum: str = ""

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "check_type": self.check_type.value,
            "resource_id": self.resource_id,
            "status": self.status.value,
            "details": self.details,
            "violations": self.violations,
            "checksum": self.checksum,
            "expected_checksum": self.expected_checksum,
        }


@dataclass
class IntegrityReport:
    report_id: str
    overall_status: IntegrityStatus
    checks: list[IntegrityCheckResult] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    generated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        }


@dataclass
class ChecksumRecord:
    resource_type: str
    resource_id: str
    checksum: str
    computed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "checksum": self.checksum,
            "computed_at": self.computed_at,
        }


class DataIntegrityVerificationService:

    def __init__(self) -> None:
        self._checksums: dict[str, ChecksumRecord] = {}
        self._reports: dict[str, IntegrityReport] = {}
        self._locked_evidence: set[str] = set()

    def computeChecksum(self, data: dict) -> str:
        data_str = str(sorted(data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()

    def registerChecksum(
        self, resource_type: str, resource_id: str, data: dict
    ) -> ChecksumRecord:
        checksum = self.computeChecksum(data)
        key = f"{resource_type}:{resource_id}"
        record = ChecksumRecord(
            resource_type=resource_type,
            resource_id=resource_id,
            checksum=checksum,
        )
        self._checksums[key] = record
        return record

    def verifyChecksum(
        self, resource_type: str, resource_id: str, data: dict
    ) -> IntegrityCheckResult:
        key = f"{resource_type}:{resource_id}"
        existing = self._checksums.get(key)
        current = self.computeChecksum(data)

        if existing is None:
            return IntegrityCheckResult(
                check_id=f"CHK-{uuid.uuid4().hex[:8]}",
                check_type=IntegrityCheckType.SHOP_FLOOR_DATA_QUALITY,
                resource_id=resource_id,
                status=IntegrityStatus.NOT_CHECKED,
                checksum=current,
                details={"reason": "No baseline checksum registered"},
            )

        match = existing.checksum == current
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.SHOP_FLOOR_DATA_QUALITY,
            resource_id=resource_id,
            status=IntegrityStatus.PASS if match else IntegrityStatus.FAIL,
            checksum=current,
            expected_checksum=existing.checksum,
            violations=[] if match else [{
                "type": "ChecksumMismatch",
                "expected": existing.checksum,
                "actual": current,
            }],
        )

    def verifyBaselineConsistency(
        self, block_id: str, baseline_data: dict, current_config: dict
    ) -> IntegrityCheckResult:
        violations = []
        frozen_items = baseline_data.get("frozen_items", [])
        config_items = current_config.get("items", {})

        for item_id in frozen_items:
            if item_id in config_items:
                baseline_val = baseline_data.get("snapshot", {}).get(item_id)
                current_val = config_items[item_id]
                if baseline_val != current_val:
                    violations.append({
                        "type": "FrozenItemModified",
                        "item_id": item_id,
                        "baseline_value": baseline_val,
                        "current_value": current_val,
                    })

        status = IntegrityStatus.PASS if not violations else IntegrityStatus.FAIL
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.BASELINE_CONSISTENCY,
            resource_id=block_id,
            status=status,
            violations=violations,
            details={"frozen_items_count": len(frozen_items)},
        )

    def verifyEvidenceImmutability(
        self, package_id: str, evidence_data: dict
    ) -> IntegrityCheckResult:
        violations = []

        if package_id in self._locked_evidence:
            is_locked = evidence_data.get("is_locked", False)
            if not is_locked:
                violations.append({
                    "type": "LockedEvidenceModified",
                    "package_id": package_id,
                })

            for section in evidence_data.get("sections", []):
                for item in section.get("evidence_items", []):
                    if item.get("verification_status") != "Verified":
                        violations.append({
                            "type": "EvidenceItemNotVerified",
                            "evidence_id": item.get("evidence_id", ""),
                        })

        status = IntegrityStatus.PASS if not violations else IntegrityStatus.FAIL
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.EVIDENCE_IMMUTABILITY,
            resource_id=package_id,
            status=status,
            violations=violations,
        )

    def lockEvidenceForImmutability(self, package_id: str) -> None:
        self._locked_evidence.add(package_id)

    def verifySupplierAuditTrail(
        self, supplier_id: str, audit_entries: list[dict]
    ) -> IntegrityCheckResult:
        violations = []
        prev_hash = "genesis"

        for i, entry in enumerate(audit_entries):
            entry_hash = entry.get("immutable_hash", "")
            data = (
                f"{entry.get('audit_id', '')}|{entry.get('action', '')}|"
                f"{entry.get('resource_type', '')}|{entry.get('resource_id', '')}|"
                f"{entry.get('actor', '')}|{entry.get('timestamp', '')}|{prev_hash}"
            )
            expected = hashlib.sha256(data.encode()).hexdigest()

            if entry_hash and entry_hash != expected:
                violations.append({
                    "type": "AuditChainBroken",
                    "entry_index": i,
                    "audit_id": entry.get("audit_id", ""),
                })

            prev_hash = entry_hash or expected

        status = IntegrityStatus.PASS if not violations else IntegrityStatus.FAIL
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.SUPPLIER_AUDIT_TRAIL,
            resource_id=supplier_id,
            status=status,
            violations=violations,
            details={"entries_checked": len(audit_entries)},
        )

    def verifyShopFloorDataQuality(
        self, equipment_id: str, data_points: list[dict]
    ) -> IntegrityCheckResult:
        violations = []
        quality_flags = {"valid": 0, "suspect": 0, "bad": 0}

        for point in data_points:
            flag = point.get("quality_flag", "valid")
            if flag in quality_flags:
                quality_flags[flag] += 1

            if flag == "bad":
                violations.append({
                    "type": "BadDataPoint",
                    "timestamp": point.get("time", ""),
                    "parameter": point.get("data_type", ""),
                })

        total = len(data_points)
        bad_ratio = quality_flags["bad"] / total if total > 0 else 0
        status = IntegrityStatus.PASS
        if bad_ratio > 0.05:
            status = IntegrityStatus.FAIL
        elif bad_ratio > 0.01:
            status = IntegrityStatus.WARNING

        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.SHOP_FLOOR_DATA_QUALITY,
            resource_id=equipment_id,
            status=status,
            violations=violations,
            details={
                "total_points": total,
                "quality_distribution": quality_flags,
                "bad_ratio": round(bad_ratio, 4),
            },
        )

    def verifyMaterialLotVerifiability(
        self, lot_id: str, lot_data: dict, trace_chain: list[dict]
    ) -> IntegrityCheckResult:
        violations = []

        cert_of_conformance = lot_data.get("certificate_of_conformance", "")
        if not cert_of_conformance:
            violations.append({
                "type": "MissingCertificateOfConformance",
                "lot_id": lot_id,
            })

        test_results = lot_data.get("test_results", {})
        if not test_results:
            violations.append({
                "type": "MissingTestResults",
                "lot_id": lot_id,
            })

        if not trace_chain:
            violations.append({
                "type": "NoTraceChain",
                "lot_id": lot_id,
            })

        status = IntegrityStatus.PASS if not violations else IntegrityStatus.WARNING
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.MATERIAL_LOT_VERIFIABILITY,
            resource_id=lot_id,
            status=status,
            violations=violations,
            details={"trace_chain_length": len(trace_chain)},
        )

    def verifyUQReproducibility(
        self, model_id: str, original_result: dict, reproduced_result: dict
    ) -> IntegrityCheckResult:
        violations = []
        tolerance = 0.01

        orig_cov = original_result.get("coefficient_of_variation", 0)
        repr_cov = reproduced_result.get("coefficient_of_variation", 0)

        if abs(orig_cov - repr_cov) > tolerance:
            violations.append({
                "type": "UQResultNotReproducible",
                "original_cov": orig_cov,
                "reproduced_cov": repr_cov,
                "delta": abs(orig_cov - repr_cov),
            })

        orig_method = original_result.get("uq_method", "")
        repr_method = reproduced_result.get("uq_method", "")
        if orig_method != repr_method:
            violations.append({
                "type": "UQMethodMismatch",
                "original_method": orig_method,
                "reproduced_method": repr_method,
            })

        status = IntegrityStatus.PASS if not violations else IntegrityStatus.FAIL
        return IntegrityCheckResult(
            check_id=f"CHK-{uuid.uuid4().hex[:8]}",
            check_type=IntegrityCheckType.UQ_REPRODUCIBILITY,
            resource_id=model_id,
            status=status,
            violations=violations,
            details={
                "original_cov": orig_cov,
                "reproduced_cov": repr_cov,
            },
        )

    def generateFullReport(
        self, checks: list[IntegrityCheckResult]
    ) -> IntegrityReport:
        passed = sum(1 for c in checks if c.status == IntegrityStatus.PASS)
        failed = sum(1 for c in checks if c.status == IntegrityStatus.FAIL)
        warnings = sum(1 for c in checks if c.status == IntegrityStatus.WARNING)

        if failed > 0:
            overall = IntegrityStatus.FAIL
        elif warnings > 0:
            overall = IntegrityStatus.WARNING
        else:
            overall = IntegrityStatus.PASS

        report = IntegrityReport(
            report_id=f"RPT-{uuid.uuid4().hex[:8]}",
            overall_status=overall,
            checks=checks,
            total_checks=len(checks),
            passed=passed,
            failed=failed,
            warnings=warnings,
        )
        self._reports[report.report_id] = report
        return report

    def getReport(self, report_id: str) -> Optional[IntegrityReport]:
        return self._reports.get(report_id)