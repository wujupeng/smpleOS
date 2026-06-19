from __future__ import annotations

from typing import Any

from src.domain.entities.requirement_trace import RequirementTrace
from src.domain.value_objects.enums import TraceType, TraceSourceType


class RequirementTraceService:
    def __init__(self):
        self._traces: dict[str, RequirementTrace] = {}

    def create_trace(
        self,
        source_type: TraceSourceType,
        source_id: str,
        target_type: TraceSourceType,
        target_id: str,
        trace_type: TraceType,
        confidence: float = 1.0,
        created_by: str | None = None,
    ) -> RequirementTrace:
        trace = RequirementTrace(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            trace_type=trace_type,
            confidence=confidence,
            created_by=created_by,
        )
        violations = trace.validate()
        if violations:
            raise ValueError(f"Invalid trace: {'; '.join(violations)}")
        self._traces[trace.trace_id] = trace
        return trace

    def get_trace_chain(self, source_id: str, max_depth: int = 10) -> list[RequirementTrace]:
        chain: list[RequirementTrace] = []
        visited: set[str] = set()
        current_id = source_id
        for _ in range(max_depth):
            if current_id in visited:
                break
            visited.add(current_id)
            outgoing = [t for t in self._traces.values() if t.source_id == current_id]
            if not outgoing:
                break
            chain.extend(outgoing)
            current_id = outgoing[0].target_id
        return chain

    def get_traces_for_source(self, source_type: TraceSourceType, source_id: str) -> list[RequirementTrace]:
        return [
            t for t in self._traces.values()
            if t.source_type == source_type and t.source_id == source_id
        ]

    def get_traces_for_target(self, target_type: TraceSourceType, target_id: str) -> list[RequirementTrace]:
        return [
            t for t in self._traces.values()
            if t.target_type == target_type and t.target_id == target_id
        ]

    def verify_trace_completeness(
        self,
        source_type: TraceSourceType,
        source_id: str,
        required_target_types: list[TraceSourceType] | None = None,
    ) -> dict[str, Any]:
        outgoing = self.get_traces_for_source(source_type, source_id)
        covered_types: set[str] = set()
        for trace in outgoing:
            covered_types.add(trace.target_type.value)
        missing: list[str] = []
        if required_target_types:
            for rt in required_target_types:
                if rt.value not in covered_types:
                    missing.append(rt.value)
        completeness = 1.0
        if required_target_types and len(required_target_types) > 0:
            completeness = 1.0 - (len(missing) / len(required_target_types))
        return {
            "source_type": source_type.value,
            "source_id": source_id,
            "total_traces": len(outgoing),
            "covered_target_types": list(covered_types),
            "missing_target_types": missing,
            "completeness": completeness,
        }