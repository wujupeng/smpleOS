from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone
from typing import Any

from ..entities.compliance_verification import (
    VerificationCheck,
    VerificationReport,
    VerificationResult,
    VerificationType,
)
from ..entities.certification_plan import CertificationPlan, ItemStatus

_DESIGN_VERIFICATION_RULES: list[dict[str, Any]] = [
    {
        "clause": "§23.201",
        "description": "Check lift coefficient meets requirement",
        "parameter": "CL_max",
        "expected_min": 1.5,
        "unit": "",
    },
    {
        "clause": "§23.301",
        "description": "Check structural load factors",
        "parameter": "load_factor_limit",
        "expected_min": 3.8,
        "unit": "g",
    },
    {
        "clause": "§23.305",
        "description": "Check stress within allowable limits",
        "parameter": "safety_factor",
        "expected_min": 1.5,
        "unit": "",
    },
    {
        "clause": "§25.341",
        "description": "Check gust load analysis completed",
        "parameter": "gust_load_factor",
        "expected_max": 5.0,
        "unit": "g",
    },
    {
        "clause": "§23.603",
        "description": "Check material specifications defined",
        "parameter": "material_spec_count",
        "expected_min": 1,
        "unit": "",
    },
    {
        "clause": "§25.1309",
        "description": "Check system safety assessment completed",
        "parameter": "fh_loss_rate",
        "expected_max": 1e-5,
        "unit": "per flight hour",
    },
]

_MFG_VERIFICATION_RULES: list[dict[str, Any]] = [
    {
        "clause": "§23.605",
        "description": "Check fabrication methods qualified",
        "parameter": "process_qualification_rate",
        "expected_min": 1.0,
        "unit": "",
    },
    {
        "clause": "§23.609",
        "description": "Check surface protection applied",
        "parameter": "protection_compliance_rate",
        "expected_min": 1.0,
        "unit": "",
    },
    {
        "clause": "§23.613",
        "description": "Check material strength verified",
        "parameter": "material_test_pass_rate",
        "expected_min": 0.99,
        "unit": "",
    },
    {
        "clause": "§25.605",
        "description": "Check manufacturing process controls",
        "parameter": "process_control_compliance",
        "expected_min": 1.0,
        "unit": "",
    },
]

_TEST_VERIFICATION_RULES: list[dict[str, Any]] = [
    {
        "clause": "§23.201",
        "description": "Check flight test covers stall demonstration",
        "parameter": "stall_test_completed",
        "expected_min": 1,
        "unit": "",
    },
    {
        "clause": "§23.207",
        "description": "Check stall warning system tested",
        "parameter": "stall_warning_tested",
        "expected_min": 1,
        "unit": "",
    },
    {
        "clause": "§25.201",
        "description": "Check stall demonstration test completed",
        "parameter": "stall_demo_completed",
        "expected_min": 1,
        "unit": "",
    },
    {
        "clause": "§23.221",
        "description": "Check spin recovery test completed",
        "parameter": "spin_test_completed",
        "expected_min": 1,
        "unit": "",
    },
]


class ComplianceVerificationService:
    def __init__(self) -> None:
        self._reports: dict[str, VerificationReport] = {}

    def verify_design_compliance(
        self,
        plan_id: str,
        design_data: dict[str, Any] | None = None,
    ) -> VerificationReport:
        checks: list[VerificationCheck] = []
        for rule in _DESIGN_VERIFICATION_RULES:
            actual = design_data.get(rule["parameter"], random.uniform(0.5, 6.0)) if design_data else random.uniform(0.5, 6.0)

            if "expected_min" in rule:
                deviation = max(0, rule["expected_min"] - actual)
                result = VerificationResult.COMPLIANT if actual >= rule["expected_min"] else (
                    VerificationResult.NON_COMPLIANT if deviation > rule["expected_min"] * 0.2 else VerificationResult.NEEDS_REVIEW
                )
                expected_str = f">= {rule['expected_min']}"
            else:
                deviation = max(0, actual - rule["expected_max"])
                result = VerificationResult.COMPLIANT if actual <= rule["expected_max"] else (
                    VerificationResult.NON_COMPLIANT if deviation > rule["expected_max"] * 0.2 else VerificationResult.NEEDS_REVIEW
                )
                expected_str = f"<= {rule['expected_max']}"

            checks.append(VerificationCheck(
                check_id=str(uuid.uuid4()),
                regulation_clause=rule["clause"],
                check_description=rule["description"],
                expected_value=expected_str,
                actual_value=f"{actual:.4f}",
                result=result,
                deviation=round(deviation, 4),
            ))

        report = self._build_report(plan_id, VerificationType.DESIGN, checks)
        self._reports[report.report_id] = report
        return report

    def verify_manufacturing_compliance(
        self,
        plan_id: str,
        mfg_data: dict[str, Any] | None = None,
    ) -> VerificationReport:
        checks: list[VerificationCheck] = []
        for rule in _MFG_VERIFICATION_RULES:
            actual = mfg_data.get(rule["parameter"], random.uniform(0.85, 1.05)) if mfg_data else random.uniform(0.85, 1.05)

            if "expected_min" in rule:
                deviation = max(0, rule["expected_min"] - actual)
                result = VerificationResult.COMPLIANT if actual >= rule["expected_min"] else VerificationResult.NON_COMPLIANT
                expected_str = f">= {rule['expected_min']}"
            else:
                deviation = max(0, actual - rule["expected_max"])
                result = VerificationResult.COMPLIANT if actual <= rule["expected_max"] else VerificationResult.NON_COMPLIANT
                expected_str = f"<= {rule['expected_max']}"

            checks.append(VerificationCheck(
                check_id=str(uuid.uuid4()),
                regulation_clause=rule["clause"],
                check_description=rule["description"],
                expected_value=expected_str,
                actual_value=f"{actual:.4f}",
                result=result,
                deviation=round(deviation, 4),
            ))

        report = self._build_report(plan_id, VerificationType.MANUFACTURING, checks)
        self._reports[report.report_id] = report
        return report

    def verify_test_compliance(
        self,
        plan_id: str,
        test_data: dict[str, Any] | None = None,
    ) -> VerificationReport:
        checks: list[VerificationCheck] = []
        for rule in _TEST_VERIFICATION_RULES:
            actual = test_data.get(rule["parameter"], random.randint(0, 2)) if test_data else random.randint(0, 2)

            deviation = max(0, rule["expected_min"] - actual)
            result = VerificationResult.COMPLIANT if actual >= rule["expected_min"] else VerificationResult.NON_COMPLIANT

            checks.append(VerificationCheck(
                check_id=str(uuid.uuid4()),
                regulation_clause=rule["clause"],
                check_description=rule["description"],
                expected_value=f">= {rule['expected_min']}",
                actual_value=str(actual),
                result=result,
                deviation=round(deviation, 4),
            ))

        report = self._build_report(plan_id, VerificationType.TEST, checks)
        self._reports[report.report_id] = report
        return report

    def generate_verification_report(self, plan_id: str) -> list[VerificationReport]:
        return [
            r for r in self._reports.values()
            if r.plan_id == plan_id
        ]

    def _build_report(
        self,
        plan_id: str,
        v_type: VerificationType,
        checks: list[VerificationCheck],
    ) -> VerificationReport:
        compliant = sum(1 for c in checks if c.result == VerificationResult.COMPLIANT)
        non_compliant = sum(1 for c in checks if c.result == VerificationResult.NON_COMPLIANT)
        needs_review = sum(1 for c in checks if c.result == VerificationResult.NEEDS_REVIEW)

        if non_compliant > 0:
            overall = VerificationResult.NON_COMPLIANT
        elif needs_review > 0:
            overall = VerificationResult.NEEDS_REVIEW
        else:
            overall = VerificationResult.COMPLIANT

        return VerificationReport(
            report_id=str(uuid.uuid4()),
            plan_id=plan_id,
            verification_type=v_type,
            checks=checks,
            overall_result=overall,
            compliant_count=compliant,
            non_compliant_count=non_compliant,
            needs_review_count=needs_review,
        )