from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InferenceResult:
    inference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_node_ids: list[str] = field(default_factory=list)
    inferred_links: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_type: str = "transitive"
    explanation: str = ""

    def add_inferred_link(self, source_id: str, target_id: str, link_type: str, confidence: float) -> None:
        self.inferred_links.append({
            "source_node_id": source_id,
            "target_node_id": target_id,
            "link_type": link_type,
            "confidence": confidence,
            "is_inferred": True,
        })

    def to_dict(self) -> dict:
        return {
            "inference_id": self.inference_id,
            "input_node_ids": self.input_node_ids,
            "inferred_links": self.inferred_links,
            "confidence": self.confidence,
            "reasoning_type": self.reasoning_type,
            "explanation": self.explanation,
        }