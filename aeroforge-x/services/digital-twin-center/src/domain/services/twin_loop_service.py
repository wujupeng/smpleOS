from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aeroforge_common.domain.base import DomainEvent

logger = logging.getLogger(__name__)


@dataclass
class FeedbackItem:
    feedback_id: str
    source_domain: str
    target_domain: str
    category: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    priority: str = "medium"
    status: str = "open"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "category": self.category,
            "description": self.description,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LoopReport:
    report_id: str
    aircraft_sn: str
    total_feedbacks: int
    feedbacks_by_domain: dict[str, int]
    improvement_metrics: dict[str, float]
    feedbacks: list[dict[str, Any]]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "aircraft_sn": self.aircraft_sn,
            "total_feedbacks": self.total_feedbacks,
            "feedbacks_by_domain": self.feedbacks_by_domain,
            "improvement_metrics": self.improvement_metrics,
            "feedbacks": self.feedbacks,
            "generated_at": self.generated_at.isoformat(),
        }


class TwinLoopService:
    def __init__(self) -> None:
        self._feedbacks: dict[str, list[FeedbackItem]] = {}

    def feedback_flight_to_design(
        self,
        aircraft_sn: str,
        flight_data: dict[str, Any],
        design_data: dict[str, Any],
    ) -> list[FeedbackItem]:
        feedbacks: list[FeedbackItem] = []

        flight_loads = flight_data.get("loads", {})
        design_limits = design_data.get("limits", {})
        flight_performance = flight_data.get("performance", {})
        design_targets = design_data.get("targets", {})

        max_load = flight_loads.get("max_load_factor", 0)
        design_limit_load = design_limits.get("limit_load_factor", 0)
        if design_limit_load > 0 and max_load > design_limit_load * 0.9:
            feedbacks.append(FeedbackItem(
                feedback_id=f"FB-{secrets.token_hex(4)}",
                source_domain="flight",
                target_domain="design",
                category="load_exceeded",
                description=f"Flight load {max_load:.2f}g approaching design limit {design_limit_load:.2f}g",
                evidence={"max_load": max_load, "design_limit": design_limit_load, "margin": design_limit_load - max_load},
                recommendation="Consider increasing design load limit or implementing operational restrictions",
                priority="high" if max_load > design_limit_load else "medium",
            ))

        cruise_drag = flight_performance.get("cruise_drag_count", 0)
        design_drag = design_targets.get("cruise_drag_count", 0)
        if design_drag > 0 and cruise_drag > design_drag * 1.05:
            feedbacks.append(FeedbackItem(
                feedback_id=f"FB-{secrets.token_hex(4)}",
                source_domain="flight",
                target_domain="design",
                category="aero_performance_deviation",
                description=f"Cruise drag {cruise_drag:.0f} counts exceeds design target {design_drag:.0f} by {((cruise_drag/design_drag)-1)*100:.1f}%",
                evidence={"actual_drag": cruise_drag, "target_drag": design_drag},
                recommendation="Review aerodynamic design and consider surface treatment or shape optimization",
                priority="medium",
            ))

        structural_response = flight_data.get("structural_response", {})
        design_stiffness = design_data.get("stiffness", {})
        if structural_response and design_stiffness:
            for mode, freq in structural_response.get("natural_frequencies", {}).items():
                design_freq = design_stiffness.get("natural_frequencies", {}).get(mode, 0)
                if design_freq > 0 and abs(freq - design_freq) / design_freq > 0.15:
                    feedbacks.append(FeedbackItem(
                        feedback_id=f"FB-{secrets.token_hex(4)}",
                        source_domain="flight",
                        target_domain="design",
                        category="structural_response_anomaly",
                        description=f"Mode {mode} frequency {freq:.1f}Hz deviates from design {design_freq:.1f}Hz",
                        evidence={"mode": mode, "actual_freq": freq, "design_freq": design_freq},
                        recommendation="Evaluate structural stiffness and consider reinforcement",
                        priority="high",
                    ))

        for fb in feedbacks:
            self._add_feedback(aircraft_sn, fb)

        if feedbacks:
            self._publish_loop_event("twin.loop.flight_to_design", aircraft_sn, len(feedbacks))

        logger.info("Flight→Design feedback: sn=%s items=%d", aircraft_sn, len(feedbacks))
        return feedbacks

    def feedback_manufacturing_to_design(
        self,
        aircraft_sn: str,
        manufacturing_data: dict[str, Any],
        design_data: dict[str, Any],
    ) -> list[FeedbackItem]:
        feedbacks: list[FeedbackItem] = []

        deviations = manufacturing_data.get("deviations", {})
        tolerances = design_data.get("tolerances", {})
        assembly_issues = manufacturing_data.get("assembly_issues", [])

        for param, deviation in deviations.items():
            tolerance = tolerances.get(param, 0)
            if tolerance > 0 and isinstance(deviation, (int, float)):
                if abs(deviation) > tolerance * 0.9:
                    feedbacks.append(FeedbackItem(
                        feedback_id=f"FB-{secrets.token_hex(4)}",
                        source_domain="manufacturing",
                        target_domain="design",
                        category="tolerance_frequent_exceedance",
                        description=f"Parameter {param} deviation {deviation:.4f} approaching tolerance {tolerance:.4f}",
                        evidence={"parameter": param, "deviation": deviation, "tolerance": tolerance},
                        recommendation="Consider relaxing design tolerance or improving manufacturing process capability",
                        priority="medium",
                    ))

        for issue in assembly_issues:
            feedbacks.append(FeedbackItem(
                feedback_id=f"FB-{secrets.token_hex(4)}",
                source_domain="manufacturing",
                target_domain="design",
                category="assembly_difficulty",
                description=f"Assembly difficulty: {issue.get('description', 'Unknown')}",
                evidence=issue,
                recommendation="Optimize design for manufacturability (DFM) - consider assembly access and tool clearance",
                priority="medium",
            ))

        for fb in feedbacks:
            self._add_feedback(aircraft_sn, fb)

        if feedbacks:
            self._publish_loop_event("twin.loop.mfg_to_design", aircraft_sn, len(feedbacks))

        logger.info("Mfg→Design feedback: sn=%s items=%d", aircraft_sn, len(feedbacks))
        return feedbacks

    def feedback_flight_to_maintenance(
        self,
        aircraft_sn: str,
        flight_data: dict[str, Any],
        maintenance_data: dict[str, Any],
    ) -> list[FeedbackItem]:
        feedbacks: list[FeedbackItem] = []

        load_trend = flight_data.get("load_trend", {})
        health_indicators = maintenance_data.get("health_indicators", {})

        avg_load = load_trend.get("avg_load_factor", 0)
        if avg_load > 2.5:
            current_interval = maintenance_data.get("inspection_interval_hours", 500)
            feedbacks.append(FeedbackItem(
                feedback_id=f"FB-{secrets.token_hex(4)}",
                source_domain="flight",
                target_domain="maintenance",
                category="load_trend_anomaly",
                description=f"Average flight load {avg_load:.1f}g above normal, recommend more frequent inspections",
                evidence={"avg_load": avg_load, "current_interval": current_interval},
                recommendation=f"Reduce inspection interval from {current_interval}h to {int(current_interval * 0.7)}h",
                priority="high",
            ))

        degradation_rate = health_indicators.get("degradation_rate", 0)
        if degradation_rate > 0.03:
            next_maintenance = maintenance_data.get("next_maintenance_date", "")
            feedbacks.append(FeedbackItem(
                feedback_id=f"FB-{secrets.token_hex(4)}",
                source_domain="flight",
                target_domain="maintenance",
                category="degradation_accelerated",
                description=f"Structural degradation rate {degradation_rate:.3f} accelerating, advance maintenance",
                evidence={"degradation_rate": degradation_rate, "next_maintenance": next_maintenance},
                recommendation="Advance next maintenance window by 20-30%",
                priority="high",
            ))

        for fb in feedbacks:
            self._add_feedback(aircraft_sn, fb)

        if feedbacks:
            self._publish_loop_event("twin.loop.flight_to_maint", aircraft_sn, len(feedbacks))

        logger.info("Flight→Maint feedback: sn=%s items=%d", aircraft_sn, len(feedbacks))
        return feedbacks

    def feedback_maintenance_to_manufacturing(
        self,
        aircraft_sn: str,
        maintenance_data: dict[str, Any],
        manufacturing_data: dict[str, Any],
    ) -> list[FeedbackItem]:
        feedbacks: list[FeedbackItem] = []

        repair_history = maintenance_data.get("repair_history", [])
        part_lifetimes = maintenance_data.get("part_lifetimes", {})

        part_repair_count: dict[str, int] = {}
        for repair in repair_history:
            part = repair.get("part_number", "")
            part_repair_count[part] = part_repair_count.get(part, 0) + 1

        for part, count in part_repair_count.items():
            if count >= 3:
                feedbacks.append(FeedbackItem(
                    feedback_id=f"FB-{secrets.token_hex(4)}",
                    source_domain="maintenance",
                    target_domain="manufacturing",
                    category="frequent_repair",
                    description=f"Part {part} repaired {count} times, check manufacturing process",
                    evidence={"part": part, "repair_count": count},
                    recommendation="Investigate manufacturing process deviation for this part",
                    priority="high",
                ))

        design_lifetimes = manufacturing_data.get("design_lifetimes", {})
        for part, actual_life in part_lifetimes.items():
            design_life = design_lifetimes.get(part, 0)
            if design_life > 0 and actual_life < design_life * 0.7:
                feedbacks.append(FeedbackItem(
                    feedback_id=f"FB-{secrets.token_hex(4)}",
                    source_domain="maintenance",
                    target_domain="manufacturing",
                    category="part_life_below_expected",
                    description=f"Part {part} lifetime {actual_life}h below design {design_life}h ({actual_life/design_life*100:.0f}%)",
                    evidence={"part": part, "actual_life": actual_life, "design_life": design_life},
                    recommendation="Check material quality and manufacturing process for this part",
                    priority="medium",
                ))

        for fb in feedbacks:
            self._add_feedback(aircraft_sn, fb)

        if feedbacks:
            self._publish_loop_event("twin.loop.maint_to_mfg", aircraft_sn, len(feedbacks))

        logger.info("Maint→Mfg feedback: sn=%s items=%d", aircraft_sn, len(feedbacks))
        return feedbacks

    def generate_loop_report(self, aircraft_sn: str) -> LoopReport:
        feedbacks = self._feedbacks.get(aircraft_sn, [])

        by_domain: dict[str, int] = {}
        for fb in feedbacks:
            key = f"{fb.source_domain}→{fb.target_domain}"
            by_domain[key] = by_domain.get(key, 0) + 1

        improvement_metrics = {
            "design_change_rate": round(len([f for f in feedbacks if f.target_domain == "design"]) / max(len(feedbacks), 1) * 100, 1),
            "maintenance_advance_rate": round(len([f for f in feedbacks if f.target_domain == "maintenance" and f.category == "degradation_accelerated"]) / max(len([f for f in feedbacks if f.target_domain == "maintenance"]), 1) * 100, 1),
            "manufacturing_improvement_rate": round(len([f for f in feedbacks if f.target_domain == "manufacturing"]) / max(len(feedbacks), 1) * 100, 1),
        }

        report = LoopReport(
            report_id=f"LR-{secrets.token_hex(4)}",
            aircraft_sn=aircraft_sn,
            total_feedbacks=len(feedbacks),
            feedbacks_by_domain=by_domain,
            improvement_metrics=improvement_metrics,
            feedbacks=[fb.to_dict() for fb in feedbacks],
        )

        logger.info("Loop report generated: sn=%s total=%d", aircraft_sn, len(feedbacks))
        return report

    def get_feedbacks(
        self,
        aircraft_sn: str,
        source_domain: str | None = None,
        target_domain: str | None = None,
    ) -> list[dict[str, Any]]:
        feedbacks = self._feedbacks.get(aircraft_sn, [])
        if source_domain:
            feedbacks = [f for f in feedbacks if f.source_domain == source_domain]
        if target_domain:
            feedbacks = [f for f in feedbacks if f.target_domain == target_domain]
        return [f.to_dict() for f in feedbacks]

    def _add_feedback(self, aircraft_sn: str, fb: FeedbackItem) -> None:
        if aircraft_sn not in self._feedbacks:
            self._feedbacks[aircraft_sn] = []
        self._feedbacks[aircraft_sn].append(fb)

    def _publish_loop_event(self, event_type: str, aircraft_sn: str, count: int) -> None:
        logger.info("Loop event: %s sn=%s count=%d", event_type, aircraft_sn, count)
