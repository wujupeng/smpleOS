"""AeroForge-X v6.0 SupplierCARService

Manages supplier quality issue lifecycle and Corrective Action Request (CAR)
tracking: issue creation, CAR management, timeliness tracking,
verification, and quality dashboards.
REQ-SUP-019~024
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IssueSeverity(str, Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class IssueStatus(str, Enum):
    REPORTED = "Reported"
    ROOT_CAUSE_ANALYSIS = "RootCauseAnalysis"
    CAR_ISSUED = "CARIssued"
    CAR_RESPONSE_RECEIVED = "CARResponseReceived"
    VERIFICATION_IN_PROGRESS = "VerificationInProgress"
    CLOSED = "Closed"
    REOPENED = "Reopened"


class CARVerificationStatus(str, Enum):
    PENDING = "Pending"
    EFFECTIVE = "Effective"
    NOT_EFFECTIVE = "NotEffective"


@dataclass
class SupplierQualityIssue:
    issue_id: str
    supplier_id: str
    issue_type: str
    description: str
    severity: IssueSeverity
    correlated_lots: list[str] = field(default_factory=list)
    correlated_ndt_records: list[str] = field(default_factory=list)
    affected_aircraft: list[str] = field(default_factory=list)
    car_id: str = ""
    status: IssueStatus = IssueStatus.REPORTED

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "supplier_id": self.supplier_id,
            "issue_type": self.issue_type,
            "description": self.description,
            "severity": self.severity.value,
            "correlated_lots": self.correlated_lots,
            "correlated_ndt_records": self.correlated_ndt_records,
            "affected_aircraft": self.affected_aircraft,
            "car_id": self.car_id,
            "status": self.status.value,
        }


@dataclass
class CorrectiveActionRequest:
    car_id: str
    issue_id: str
    supplier_id: str
    root_cause: str = ""
    corrective_action: str = ""
    due_date: str = ""
    response_date: str = ""
    is_overdue: bool = False
    verification_status: CARVerificationStatus = CARVerificationStatus.PENDING
    escalation_level: int = 0

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "issue_id": self.issue_id,
            "supplier_id": self.supplier_id,
            "root_cause": self.root_cause,
            "corrective_action": self.corrective_action,
            "due_date": self.due_date,
            "response_date": self.response_date,
            "is_overdue": self.is_overdue,
            "verification_status": self.verification_status.value,
            "escalation_level": self.escalation_level,
        }


@dataclass
class CARTimelinessStatus:
    car_id: str
    is_overdue: bool
    days_since_creation: int
    escalation_level: int
    escalation_rules: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "is_overdue": self.is_overdue,
            "days_since_creation": self.days_since_creation,
            "escalation_level": self.escalation_level,
        }


@dataclass
class CARVerificationResult:
    car_id: str
    is_effective: bool
    issue_reopened: bool
    supplier_rating_updated: bool
    enhanced_inspection_triggered: bool

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "is_effective": self.is_effective,
            "issue_reopened": self.issue_reopened,
            "supplier_rating_updated": self.supplier_rating_updated,
            "enhanced_inspection_triggered": self.enhanced_inspection_triggered,
        }


@dataclass
class SupplierQualityDashboard:
    top_defect_categories: list[dict] = field(default_factory=list)
    car_aging: dict = field(default_factory=dict)
    rating_trends: list[dict] = field(default_factory=list)
    lot_rejection_rate_trends: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "top_defect_categories": self.top_defect_categories,
            "car_aging": self.car_aging,
            "rating_trends": self.rating_trends,
            "lot_rejection_rate_trends": self.lot_rejection_rate_trends,
        }


class SupplierCARService:

    ESCALATION_RULES = [
        {"days": 7, "level": 1, "action": "Notify supplier manager"},
        {"days": 14, "level": 2, "action": "Escalate to procurement director"},
        {"days": 30, "level": 3, "action": "Suspend supplier"},
    ]

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._issues: dict[str, SupplierQualityIssue] = {}
        self._cars: dict[str, CorrectiveActionRequest] = {}

    def createQualityIssue(
        self, issue: SupplierQualityIssue
    ) -> SupplierQualityIssue:
        if issue.issue_id in self._issues:
            raise ValueError(f"Quality issue already exists: {issue.issue_id}")

        self._issues[issue.issue_id] = issue
        return issue

    def createCAR(self, issue_id: str) -> CorrectiveActionRequest:
        if issue_id not in self._issues:
            raise ValueError(f"Quality issue not found: {issue_id}")

        issue = self._issues[issue_id]
        car_id = f"CAR-{issue.supplier_id}-{uuid.uuid4().hex[:6]}"

        car = CorrectiveActionRequest(
            car_id=car_id,
            issue_id=issue_id,
            supplier_id=issue.supplier_id,
        )

        issue.car_id = car_id
        issue.status = IssueStatus.CAR_ISSUED
        self._cars[car_id] = car
        return car

    def trackCARTimeliness(self, car_id: str) -> CARTimelinessStatus:
        if car_id not in self._cars:
            raise ValueError(f"CAR not found: {car_id}")

        car = self._cars[car_id]

        escalation_level = 0
        for rule in self.ESCALATION_RULES:
            if car.is_overdue:
                escalation_level = max(escalation_level, rule["level"])

        if escalation_level > car.escalation_level:
            car.escalation_level = escalation_level

        return CARTimelinessStatus(
            car_id=car_id,
            is_overdue=car.is_overdue,
            days_since_creation=0,
            escalation_level=car.escalation_level,
            escalation_rules=self.ESCALATION_RULES,
        )

    def verifyCorrectiveAction(
        self, car_id: str, is_effective: bool
    ) -> CARVerificationResult:
        if car_id not in self._cars:
            raise ValueError(f"CAR not found: {car_id}")

        car = self._cars[car_id]
        issue = self._issues.get(car.issue_id)

        if is_effective:
            car.verification_status = CARVerificationStatus.EFFECTIVE
            if issue:
                issue.status = IssueStatus.CLOSED
            return CARVerificationResult(
                car_id=car_id,
                is_effective=True,
                issue_reopened=False,
                supplier_rating_updated=True,
                enhanced_inspection_triggered=False,
            )
        else:
            car.verification_status = CARVerificationStatus.NOT_EFFECTIVE
            if issue:
                issue.status = IssueStatus.REOPENED
            return CARVerificationResult(
                car_id=car_id,
                is_effective=False,
                issue_reopened=True,
                supplier_rating_updated=True,
                enhanced_inspection_triggered=True,
            )

    def generateQualityDashboard(self) -> SupplierQualityDashboard:
        defect_categories: dict[str, int] = {}
        car_aging = {"pending": 0, "effective": 0, "not_effective": 0}

        for issue in self._issues.values():
            category = issue.issue_type
            defect_categories[category] = defect_categories.get(category, 0) + 1

        for car in self._cars.values():
            if car.verification_status == CARVerificationStatus.PENDING:
                car_aging["pending"] += 1
            elif car.verification_status == CARVerificationStatus.EFFECTIVE:
                car_aging["effective"] += 1
            elif car.verification_status == CARVerificationStatus.NOT_EFFECTIVE:
                car_aging["not_effective"] += 1

        top_defects = sorted(
            [{"category": k, "count": v} for k, v in defect_categories.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        return SupplierQualityDashboard(
            top_defect_categories=top_defects,
            car_aging=car_aging,
        )

    def getIssue(self, issue_id: str) -> Optional[SupplierQualityIssue]:
        return self._issues.get(issue_id)

    def getCAR(self, car_id: str) -> Optional[CorrectiveActionRequest]:
        return self._cars.get(car_id)