from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImpactResult:
    source_node_id: str = ""
    affected_nodes: list[dict] = field(default_factory=list)
    impact_paths: list[list[str]] = field(default_factory=list)
    total_impact_score: float = 0.0
    propagation_depth: int = 0
    is_partial: bool = False
    warnings: list[str] = field(default_factory=list)

    def add_affected_node(self, node_id: str, node_type: str, depth: int, confidence: float, path: list[str]) -> None:
        self.affected_nodes.append({
            "node_id": node_id,
            "node_type": node_type,
            "depth": depth,
            "confidence": confidence,
            "path": path,
        })
        self.total_impact_score += confidence * (0.8 ** depth)

    def to_dict(self) -> dict:
        return {
            "source_node_id": self.source_node_id,
            "affected_nodes": self.affected_nodes,
            "impact_paths": self.impact_paths,
            "total_impact_score": round(self.total_impact_score, 6),
            "propagation_depth": self.propagation_depth,
            "is_partial": self.is_partial,
            "warnings": self.warnings,
            "total_affected": len(self.affected_nodes),
        }