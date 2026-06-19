"""AeroForge-X V6.1 PropagationIdempotencyGuard

Ensures exactly-once semantics for BOM incremental propagation
using idempotency keys, deduplication, and optimistic locking.

REQ-IC-007
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IdempotencyCheckResult:
    change_id: str
    is_duplicate: bool
    previous_result_hash: str = ""
    can_proceed: bool = True

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "is_duplicate": self.is_duplicate,
            "previous_result_hash": self.previous_result_hash,
            "can_proceed": self.can_proceed,
        }


class PropagationIdempotencyGuard:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._processed: dict[str, str] = {}
        self._locks: dict[str, int] = {}

    def checkIdempotency(
        self, change_id: str, change_data: dict, expected_version: int = 0
    ) -> IdempotencyCheckResult:
        data_hash = hashlib.sha256(str(sorted(change_data.items())).encode()).hexdigest()[:16]
        composite_key = f"{change_id}:{data_hash}"

        if composite_key in self._processed:
            return IdempotencyCheckResult(
                change_id=change_id,
                is_duplicate=True,
                previous_result_hash=self._processed[composite_key],
                can_proceed=False,
            )

        current_version = self._locks.get(change_id, 0)
        if expected_version > 0 and current_version != expected_version:
            return IdempotencyCheckResult(
                change_id=change_id,
                is_duplicate=False,
                can_proceed=False,
            )

        return IdempotencyCheckResult(
            change_id=change_id,
            is_duplicate=False,
            can_proceed=True,
        )

    def recordCompletion(
        self, change_id: str, change_data: dict, result_hash: str
    ) -> None:
        data_hash = hashlib.sha256(str(sorted(change_data.items())).encode()).hexdigest()[:16]
        composite_key = f"{change_id}:{data_hash}"
        self._processed[composite_key] = result_hash
        self._locks[change_id] = self._locks.get(change_id, 0) + 1

    def getVersion(self, change_id: str) -> int:
        return self._locks.get(change_id, 0)