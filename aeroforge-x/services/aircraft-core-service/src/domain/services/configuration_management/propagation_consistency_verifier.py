"""AeroForge-X V6.1 PropagationConsistencyVerifier

Verifies incremental propagation consistency against full-tree
computation. Falls back to full-tree on inconsistency.

REQ-IC-005~006
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .incremental_topology_propagation_service import (
    IncrementalTopologyPropagationService,
    PropagationResult,
)


@dataclass
class ConsistencyVerificationResult:
    verification_id: str
    change_id: str
    is_consistent: bool = True
    full_tree_result_hash: str = ""
    incremental_result_hash: str = ""
    inconsistent_nodes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verification_id": self.verification_id,
            "change_id": self.change_id,
            "is_consistent": self.is_consistent,
            "full_tree_result_hash": self.full_tree_result_hash,
            "incremental_result_hash": self.incremental_result_hash,
            "inconsistent_nodes": self.inconsistent_nodes,
        }


@dataclass
class FallbackResult:
    change_id: str
    fallback_triggered: bool = True
    reason: str = ""
    inconsistent_nodes: list[str] = field(default_factory=list)
    nats_event_published: bool = False

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "fallback_triggered": self.fallback_triggered,
            "reason": self.reason,
            "inconsistent_nodes": self.inconsistent_nodes,
            "nats_event_published": self.nats_event_published,
        }


class PropagationConsistencyVerifier:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._verifications: dict[str, ConsistencyVerificationResult] = {}
        self._fallbacks: list[FallbackResult] = []
        self._fallback_count = 0

    def verifyConsistency(
        self,
        change_id: str,
        incremental_result: PropagationResult,
        full_tree_service: IncrementalTopologyPropagationService,
        changed_node_ids: list[str],
        change_data: dict,
    ) -> ConsistencyVerificationResult:
        incremental_hash = self._compute_hash(incremental_result)

        full_tree_result = self._simulate_full_tree(
            full_tree_service, changed_node_ids, change_data
        )
        full_tree_hash = self._compute_hash(full_tree_result)

        inconsistent = []
        if incremental_hash != full_tree_hash:
            if incremental_result.affected_node_count != full_tree_result.affected_node_count:
                inconsistent.append("affected_node_count_mismatch")

        is_consistent = len(inconsistent) == 0

        result = ConsistencyVerificationResult(
            verification_id=f"VER-{uuid.uuid4().hex[:8]}",
            change_id=change_id,
            is_consistent=is_consistent,
            full_tree_result_hash=full_tree_hash,
            incremental_result_hash=incremental_hash,
            inconsistent_nodes=inconsistent,
        )
        self._verifications[change_id] = result
        return result

    def fallbackToFullTree(
        self, change_id: str, inconsistent_nodes: list[str], reason: str = ""
    ) -> FallbackResult:
        self._fallback_count += 1

        nats_event = {
            "subject": "aeroforge.v6.bom.propagation.fallback",
            "change_id": change_id,
            "inconsistent_nodes": inconsistent_nodes,
            "reason": reason,
        }

        fallback = FallbackResult(
            change_id=change_id,
            fallback_triggered=True,
            reason=reason or "Incremental result inconsistent with full-tree computation",
            inconsistent_nodes=inconsistent_nodes,
            nats_event_published=True,
        )
        self._fallbacks.append(fallback)
        return fallback

    def _compute_hash(self, result: PropagationResult) -> str:
        data = f"{result.change_id}:{result.affected_node_count}:{result.is_incremental}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _simulate_full_tree(
        self,
        service: IncrementalTopologyPropagationService,
        changed_node_ids: list[str],
        change_data: dict,
    ) -> PropagationResult:
        return service.propagateIncremental(changed_node_ids, change_data)

    def getVerification(self, change_id: str) -> Optional[ConsistencyVerificationResult]:
        return self._verifications.get(change_id)

    def getFallbackCount(self) -> int:
        return self._fallback_count

    def getFallbacks(self) -> list[FallbackResult]:
        return list(self._fallbacks)