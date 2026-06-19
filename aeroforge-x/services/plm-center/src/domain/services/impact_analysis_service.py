from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .change_mgmt_domain_service import ECR, ChangeItem

logger = logging.getLogger(__name__)


@dataclass
class ImpactResult:
    affected_parts: list[dict[str, Any]] = field(default_factory=list)
    affected_bom_items: list[dict[str, Any]] = field(default_factory=list)
    affected_processes: list[dict[str, Any]] = field(default_factory=list)
    affected_wip_batches: list[dict[str, Any]] = field(default_factory=list)
    safety_critical: bool = False
    elevated_review: bool = False
    impact_level: str = "low"
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "affected_parts": self.affected_parts,
            "affected_bom_items": self.affected_bom_items,
            "affected_processes": self.affected_processes,
            "affected_wip_batches": self.affected_wip_batches,
            "safety_critical": self.safety_critical,
            "elevated_review": self.elevated_review,
            "impact_level": self.impact_level,
            "summary": self.summary,
        }


SAFETY_CRITICAL_PART_TYPES = {"spar", "frame", "rib", "h-spar", "v-spar", "landing_gear", "engine_mount"}
STRUCTURAL_PART_TYPES = {"spar", "frame", "rib", "skin", "h-spar", "v-spar"}


class ImpactAnalysisService:
    def __init__(self) -> None:
        self._bom_graph: dict[str, list[str]] = {}
        self._process_graph: dict[str, list[str]] = {}
        self._wip_batches: dict[str, list[str]] = {}

    def register_bom_graph(self, parent_code: str, child_codes: list[str]) -> None:
        self._bom_graph[parent_code] = child_codes

    def register_process_link(self, part_code: str, process_ids: list[str]) -> None:
        self._process_graph[part_code] = process_ids

    def register_wip_batch(self, batch_id: str, part_codes: list[str]) -> None:
        self._wip_batches[batch_id] = part_codes

    def analyze_affected_parts(self, ecr: ECR) -> list[dict[str, Any]]:
        affected: list[dict[str, Any]] = []

        for item in ecr.change_items:
            affected.append({
                "object_id": item.object_id,
                "object_name": item.object_name,
                "object_type": item.object_type,
                "change_type": item.change_type,
                "propagation_path": [item.object_id],
            })

            children = self._bom_graph.get(item.object_id, [])
            for child_code in children:
                affected.append({
                    "object_id": child_code,
                    "object_name": child_code,
                    "object_type": "dependent_part",
                    "change_type": "propagated",
                    "propagation_path": [item.object_id, child_code],
                })

            parent_code = self._find_parent(item.object_id)
            if parent_code:
                affected.append({
                    "object_id": parent_code,
                    "object_name": parent_code,
                    "object_type": "parent_assembly",
                    "change_type": "propagated_upward",
                    "propagation_path": [item.object_id, parent_code],
                })

        return affected

    def analyze_affected_bom(self, ecr: ECR) -> list[dict[str, Any]]:
        affected: list[dict[str, Any]] = []

        for item in ecr.change_items:
            affected.append({
                "bom_type": "ebom",
                "item_code": item.object_id,
                "item_name": item.object_name,
                "impact": "direct_change",
                "propagation": [],
            })

            if item.object_id in self._bom_graph:
                affected.append({
                    "bom_type": "mbom",
                    "item_code": item.object_id,
                    "item_name": item.object_name,
                    "impact": "requires_mbom_update",
                    "propagation": ["ebom_to_mbom"],
                })
                affected.append({
                    "bom_type": "sbom",
                    "item_code": item.object_id,
                    "item_name": item.object_name,
                    "impact": "requires_sbom_update",
                    "propagation": ["ebom_to_mbom_to_sbom"],
                })

        return affected

    def analyze_affected_process(self, ecr: ECR) -> list[dict[str, Any]]:
        affected: list[dict[str, Any]] = []

        for item in ecr.change_items:
            process_ids = self._process_graph.get(item.object_id, [])
            for pid in process_ids:
                affected.append({
                    "process_id": pid,
                    "part_code": item.object_id,
                    "impact": "process_requires_update",
                    "process_type": "manufacturing",
                })

            if item.change_type == "modify" and item.object_type in STRUCTURAL_PART_TYPES:
                affected.append({
                    "process_id": f"PROC-INSPECT-{item.object_id}",
                    "part_code": item.object_id,
                    "impact": "inspection_process_change",
                    "process_type": "quality_inspection",
                })

        return affected

    def analyze_affected_wip(self, ecr: ECR) -> list[dict[str, Any]]:
        affected: list[dict[str, Any]] = []

        for item in ecr.change_items:
            for batch_id, part_codes in self._wip_batches.items():
                if item.object_id in part_codes:
                    affected.append({
                        "batch_id": batch_id,
                        "part_code": item.object_id,
                        "impact": "wip_batch_affected",
                        "action": "hold_for_review",
                    })

        return affected

    def check_safety_critical(self, ecr: ECR) -> bool:
        for item in ecr.change_items:
            part_name_lower = item.object_name.lower()
            object_id_lower = item.object_id.lower()
            for critical_type in SAFETY_CRITICAL_PART_TYPES:
                if critical_type in part_name_lower or critical_type in object_id_lower:
                    return True
            if item.object_type in ("structural", "safety_critical"):
                return True
        return False

    def full_analysis(self, ecr: ECR) -> ImpactResult:
        result = ImpactResult()

        result.affected_parts = self.analyze_affected_parts(ecr)
        result.affected_bom_items = self.analyze_affected_bom(ecr)
        result.affected_processes = self.analyze_affected_process(ecr)
        result.affected_wip_batches = self.analyze_affected_wip(ecr)

        result.safety_critical = self.check_safety_critical(ecr)
        result.elevated_review = len(result.affected_parts) > 5 or result.safety_critical

        total_impacts = (
            len(result.affected_parts)
            + len(result.affected_bom_items)
            + len(result.affected_processes)
            + len(result.affected_wip_batches)
        )

        if result.safety_critical or total_impacts > 20:
            result.impact_level = "critical"
        elif total_impacts > 10:
            result.impact_level = "high"
        elif total_impacts > 3:
            result.impact_level = "medium"
        else:
            result.impact_level = "low"

        result.summary = (
            f"Impact: {len(result.affected_parts)} parts, "
            f"{len(result.affected_bom_items)} BOM items, "
            f"{len(result.affected_processes)} processes, "
            f"{len(result.affected_wip_batches)} WIP batches. "
            f"Level: {result.impact_level}. "
            f"Safety critical: {result.safety_critical}."
        )

        ecr.set_impact_analysis(result.to_dict())
        logger.info("Impact analysis for ECR %s: %s", ecr.ecr_code, result.summary)

        return result

    def _find_parent(self, child_code: str) -> str | None:
        for parent, children in self._bom_graph.items():
            if child_code in children:
                return parent
        return None