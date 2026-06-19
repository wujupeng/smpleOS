from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FMEAFailureMode:
    mode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    failure_description: str = ""
    severity: int = 5
    occurrence: int = 5
    detection: int = 5
    rpn: int = 125
    is_safety_critical: bool = False
    corrective_actions: list[str] = field(default_factory=list)

    def calculate_rpn(self) -> int:
        self.rpn = self.severity * self.occurrence * self.detection
        return self.rpn

    def is_high_risk(self, threshold: int = 200) -> bool:
        return self.rpn >= threshold


@dataclass
class FMEAAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fmea_type: str = "dfmea"
    component_id: str | None = None
    component_name: str | None = None
    failure_modes: list[FMEAFailureMode] = field(default_factory=list)
    highest_rpn: int = 0
    status: str = "in_progress"
    created_by: str | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def add_failure_mode(self, description: str, severity: int, occurrence: int,
                         detection: int, is_safety_critical: bool = False) -> FMEAFailureMode:
        mode = FMEAFailureMode(
            failure_description=description,
            severity=max(1, min(10, severity)),
            occurrence=max(1, min(10, occurrence)),
            detection=max(1, min(10, detection)),
            is_safety_critical=is_safety_critical,
        )
        mode.calculate_rpn()
        self.failure_modes.append(mode)
        self.highest_rpn = max(m.rpn for m in self.failure_modes)
        self.updated_at = datetime.utcnow()
        if is_safety_critical:
            self.domain_events.append({
                "event_type": "fmea.safety_critical_detected",
                "analysis_id": self.analysis_id,
                "mode_id": mode.mode_id,
                "rpn": mode.rpn,
            })
        return mode

    def recommend_corrective_actions(self, rpn_threshold: int = 200) -> dict[str, list[str]]:
        recommendations: dict[str, list[str]] = {}
        for mode in self.failure_modes:
            if mode.rpn >= rpn_threshold:
                actions = []
                if mode.severity >= 8:
                    actions.append("Redesign to reduce severity of failure effect")
                if mode.occurrence >= 7:
                    actions.append("Improve design or process controls to reduce occurrence")
                if mode.detection >= 7:
                    actions.append("Add detection methods or improve inspection frequency")
                recommendations[mode.mode_id] = actions
                mode.corrective_actions = actions
        return recommendations

    def complete(self) -> None:
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "fmea.completed",
            "analysis_id": self.analysis_id,
            "highest_rpn": self.highest_rpn,
        })

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events


@dataclass
class FRACASCorrectiveAction:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_description: str = ""
    responsible: str | None = None
    due_date: str | None = None
    implemented_at: datetime | None = None
    verified_at: datetime | None = None
    verified_by: str | None = None
    effectiveness: str | None = None
    status: str = "planned"


@dataclass
class FRACASRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    failure_description: str = ""
    affected_component: str | None = None
    serial_number: str | None = None
    failure_mode: str | None = None
    detection_method: str | None = None
    root_cause: str | None = None
    is_safety_critical: bool = False
    corrective_actions: list[FRACASCorrectiveAction] = field(default_factory=list)
    status: str = "reported"
    reported_by: str | None = None
    assigned_to: str | None = None
    closed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def record_root_cause(self, root_cause: str) -> None:
        self.root_cause = root_cause
        self.status = "root_cause_identified"
        self.updated_at = datetime.utcnow()

    def add_corrective_action(self, description: str, responsible: str | None = None) -> FRACASCorrectiveAction:
        action = FRACASCorrectiveAction(action_description=description, responsible=responsible)
        self.corrective_actions.append(action)
        self.status = "corrective_action_planned"
        self.updated_at = datetime.utcnow()
        return action

    def verify_corrective_action(self, action_id: str, verified_by: str, effectiveness: str) -> None:
        for action in self.corrective_actions:
            if action.action_id == action_id:
                action.verified_by = verified_by
                action.verified_at = datetime.utcnow()
                action.effectiveness = effectiveness
                action.status = "verified"
                break
        all_verified = all(a.status == "verified" for a in self.corrective_actions)
        if all_verified and self.corrective_actions:
            self.status = "verified"
        self.updated_at = datetime.utcnow()

    def close(self) -> None:
        self.status = "closed"
        self.closed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "fracas.report.created",
            "record_id": self.record_id,
            "is_safety_critical": self.is_safety_critical,
        })

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events


@dataclass
class ReliabilityPrediction:
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component_id: str = ""
    component_name: str | None = None
    mtbf_hours: float = 0.0
    failure_rate_per_million_hours: float = 0.0
    confidence_level: float = 0.90
    confidence_interval: dict[str, float] = field(default_factory=dict)
    data_sources: list[str] = field(default_factory=list)
    status: str = "predicted"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_mtbf(self, mtbf: float, confidence: dict[str, float] | None = None) -> None:
        self.mtbf_hours = mtbf
        self.failure_rate_per_million_hours = 1e6 / mtbf if mtbf > 0 else 0
        if confidence:
            self.confidence_interval = confidence
        self.status = "updated"
        self.updated_at = datetime.utcnow()


@dataclass
class LifePrediction:
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component_id: str = ""
    serial_number: str | None = None
    remaining_useful_life_hours: float = 0.0
    total_life_hours: float = 0.0
    warning_threshold_hours: float = 100.0
    consumption_pct: float = 0.0
    maintenance_suggestion: str | None = None
    status: str = "active"
    predicted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_life(self, remaining_hours: float, total_hours: float) -> None:
        self.remaining_useful_life_hours = remaining_hours
        self.total_life_hours = total_hours
        self.consumption_pct = round((1 - remaining_hours / total_hours) * 100, 2) if total_hours > 0 else 0
        if remaining_hours <= self.warning_threshold_hours * 0.5:
            self.status = "critical"
            self.maintenance_suggestion = "Immediate replacement required"
        elif remaining_hours <= self.warning_threshold_hours:
            self.status = "warning"
            self.maintenance_suggestion = "Schedule replacement within warning threshold"
        else:
            self.status = "active"
            self.maintenance_suggestion = None
        self.updated_at = datetime.utcnow()


class FMEAService:
    def create_analysis(self, fmea_type: str, component_id: str | None = None,
                        component_name: str | None = None, created_by: str | None = None) -> FMEAAnalysis:
        return FMEAAnalysis(fmea_type=fmea_type, component_id=component_id,
                            component_name=component_name, created_by=created_by)

    def add_failure_mode(self, analysis: FMEAAnalysis, description: str, severity: int,
                         occurrence: int, detection: int, is_safety_critical: bool = False) -> FMEAFailureMode:
        return analysis.add_failure_mode(description, severity, occurrence, detection, is_safety_critical)

    def calculate_rpn(self, mode: FMEAFailureMode) -> int:
        return mode.calculate_rpn()


class FRACASService:
    def create_failure_report(self, description: str, component: str | None = None,
                              serial_number: str | None = None, reported_by: str | None = None,
                              is_safety_critical: bool = False) -> FRACASRecord:
        return FRACASRecord(
            failure_description=description, affected_component=component,
            serial_number=serial_number, reported_by=reported_by,
            is_safety_critical=is_safety_critical,
        )

    def record_root_cause(self, record: FRACASRecord, root_cause: str) -> None:
        record.record_root_cause(root_cause)

    def add_corrective_action(self, record: FRACASRecord, description: str,
                               responsible: str | None = None) -> FRACASCorrectiveAction:
        return record.add_corrective_action(description, responsible)

    def verify_corrective_action(self, record: FRACASRecord, action_id: str,
                                  verified_by: str, effectiveness: str) -> None:
        record.verify_corrective_action(action_id, verified_by, effectiveness)


class ReliabilityService:
    def predict_mtbf(self, component_id: str, total_operating_hours: float,
                     total_failures: int, confidence_level: float = 0.90) -> ReliabilityPrediction:
        if total_failures == 0:
            mtbf = total_operating_hours * 2
        else:
            mtbf = total_operating_hours / total_failures
        ci_lower = mtbf * 0.7
        ci_upper = mtbf * 1.3
        return ReliabilityPrediction(
            component_id=component_id,
            mtbf_hours=round(mtbf, 2),
            failure_rate_per_million_hours=round(1e6 / mtbf, 6) if mtbf > 0 else 0,
            confidence_level=confidence_level,
            confidence_interval={"lower": round(ci_lower, 2), "upper": round(ci_upper, 2)},
        )

    def predict_remaining_life(self, component_id: str, serial_number: str | None,
                                total_life_hours: float, consumed_hours: float,
                                warning_threshold_hours: float = 100.0) -> LifePrediction:
        remaining = total_life_hours - consumed_hours
        return LifePrediction(
            component_id=component_id,
            serial_number=serial_number,
            remaining_useful_life_hours=round(remaining, 2),
            total_life_hours=total_life_hours,
            warning_threshold_hours=warning_threshold_hours,
        )