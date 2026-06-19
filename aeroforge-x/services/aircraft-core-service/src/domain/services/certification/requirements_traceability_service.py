"""AeroForge-X v6.0 RequirementsTraceabilityService

Manages requirements traceability matrix: ARP4754A/DO-178C/DO-254
traceability links, coverage computation, broken link detection,
and bidirectional navigation.
REQ-CERT-001~007
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TraceNodeType(str, Enum):
    REQUIREMENT = "Requirement"
    DESIGN_ELEMENT = "DesignElement"
    TEST_CASE = "TestCase"
    EVIDENCE_ITEM = "EvidenceItem"
    CERTIFICATION_ITEM = "CertificationItem"


class LinkType(str, Enum):
    SATISFIED_BY = "Satisfies"
    VERIFIED_BY = "Verifies"
    PRODUCES = "Produces"
    DEMONSTRATES = "Demonstrates"


@dataclass
class TraceNode:
    node_id: str
    node_type: TraceNodeType
    name: str
    status: str = "Active"

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "status": self.status,
        }


@dataclass
class TraceLink:
    source_node_id: str
    target_node_id: str
    link_type: LinkType
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "link_type": self.link_type.value,
            "confidence": self.confidence,
        }


@dataclass
class BrokenLink:
    source_node_id: str
    expected_target_type: TraceNodeType
    missing_link_type: LinkType

    def to_dict(self) -> dict:
        return {
            "source_node_id": self.source_node_id,
            "expected_target_type": self.expected_target_type.value,
            "missing_link_type": self.missing_link_type.value,
        }


@dataclass
class TraceabilityCoverage:
    total_requirements: int
    coverage_percentage: float
    test_linkage_percentage: float
    evidence_linkage_percentage: float
    broken_links: list[BrokenLink] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_requirements": self.total_requirements,
            "coverage_percentage": self.coverage_percentage,
            "test_linkage_percentage": self.test_linkage_percentage,
            "evidence_linkage_percentage": self.evidence_linkage_percentage,
            "broken_links": [b.to_dict() for b in self.broken_links],
        }


@dataclass
class RequirementsTraceabilityMatrix:
    project_id: str
    trace_standard: str
    nodes: list[TraceNode] = field(default_factory=list)
    links: list[TraceLink] = field(default_factory=list)
    coverage: Optional[TraceabilityCoverage] = None

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "trace_standard": self.trace_standard,
            "nodes": [n.to_dict() for n in self.nodes],
            "links": [l.to_dict() for l in self.links],
            "coverage": self.coverage.to_dict() if self.coverage else None,
        }


class RequirementsTraceabilityService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
def __init__(self, repo=None) -> None:
        self._matrices: dict[str, RequirementsTraceabilityMatrix] = {}
        self._nodes: dict[str, TraceNode] = {}
        self._links: list[TraceLink] = []

    def createTraceLink(
        self, source: TraceNode, target: TraceNode, link_type: LinkType
    ) -> TraceLink:
        link = TraceLink(
            source_node_id=source.node_id,
            target_node_id=target.node_id,
            link_type=link_type,
        )
        self._links.append(link)
        self._nodes[source.node_id] = source
        self._nodes[target.node_id] = target
        return link

    def getTraceabilityMatrix(self, project_id: str) -> RequirementsTraceabilityMatrix:
        if project_id not in self._matrices:
            project_nodes = [
                n for n in self._nodes.values()
            ]
            project_links = list(self._links)
            self._matrices[project_id] = RequirementsTraceabilityMatrix(
                project_id=project_id,
                trace_standard="ARP4754A",
                nodes=project_nodes,
                links=project_links,
            )
        return self._matrices[project_id]

    def detectBrokenLinks(self, requirement_id: str) -> list[BrokenLink]:
        broken = []
        downstream_links = [
            l for l in self._links if l.source_node_id == requirement_id
        ]

        if not downstream_links:
            broken.append(
                BrokenLink(
                    source_node_id=requirement_id,
                    expected_target_type=TraceNodeType.DESIGN_ELEMENT,
                    missing_link_type=LinkType.SATISFIED_BY,
                )
            )
            return broken

        design_ids = [
            l.target_node_id for l in downstream_links
            if l.link_type == LinkType.SATISFIED_BY
        ]
        if not design_ids:
            broken.append(
                BrokenLink(
                    source_node_id=requirement_id,
                    expected_target_type=TraceNodeType.DESIGN_ELEMENT,
                    missing_link_type=LinkType.SATISFIED_BY,
                )
            )

        for design_id in design_ids:
            test_links = [
                l for l in self._links
                if l.source_node_id == design_id and l.link_type == LinkType.VERIFIED_BY
            ]
            if not test_links:
                broken.append(
                    BrokenLink(
                        source_node_id=design_id,
                        expected_target_type=TraceNodeType.TEST_CASE,
                        missing_link_type=LinkType.VERIFIED_BY,
                    )
                )

            for test_link in test_links:
                evidence_links = [
                    l for l in self._links
                    if l.source_node_id == test_link.target_node_id
                    and l.link_type == LinkType.PRODUCES
                ]
                if not evidence_links:
                    broken.append(
                        BrokenLink(
                            source_node_id=test_link.target_node_id,
                            expected_target_type=TraceNodeType.EVIDENCE_ITEM,
                            missing_link_type=LinkType.PRODUCES,
                        )
                    )

                for ev_link in evidence_links:
                    cert_links = [
                        l for l in self._links
                        if l.source_node_id == ev_link.target_node_id
                        and l.link_type == LinkType.DEMONSTRATES
                    ]
                    if not cert_links:
                        broken.append(
                            BrokenLink(
                                source_node_id=ev_link.target_node_id,
                                expected_target_type=TraceNodeType.CERTIFICATION_ITEM,
                                missing_link_type=LinkType.DEMONSTRATES,
                            )
                        )

        return broken

    def computeTraceabilityCoverage(self, project_id: str) -> TraceabilityCoverage:
        req_nodes = [
            n for n in self._nodes.values()
            if n.node_type == TraceNodeType.REQUIREMENT
        ]
        total = len(req_nodes)
        if total == 0:
            return TraceabilityCoverage(
                total_requirements=0,
                coverage_percentage=100.0,
                test_linkage_percentage=100.0,
                evidence_linkage_percentage=100.0,
            )

        all_broken = []
        full_chain_count = 0
        test_linked_count = 0
        evidence_linked_count = 0

        for req in req_nodes:
            broken = self.detectBrokenLinks(req.node_id)
            all_broken.extend(broken)
            if not broken:
                full_chain_count += 1

            design_ids = [
                l.target_node_id for l in self._links
                if l.source_node_id == req.node_id and l.link_type == LinkType.SATISFIED_BY
            ]
            has_test = any(
                l.link_type == LinkType.VERIFIED_BY and l.source_node_id in design_ids
                for l in self._links
            )
            if has_test:
                test_linked_count += 1

            test_ids = [
                l.target_node_id for l in self._links
                if l.link_type == LinkType.VERIFIED_BY and l.source_node_id in design_ids
            ]
            has_evidence = any(
                l.link_type == LinkType.PRODUCES and l.source_node_id in test_ids
                for l in self._links
            )
            if has_evidence:
                evidence_linked_count += 1

        return TraceabilityCoverage(
            total_requirements=total,
            coverage_percentage=(full_chain_count / total) * 100.0,
            test_linkage_percentage=(test_linked_count / total) * 100.0,
            evidence_linkage_percentage=(evidence_linked_count / total) * 100.0,
            broken_links=all_broken,
        )

    def navigateForward(self, requirement_id: str) -> list[TraceNode]:
        result = []
        visited = set()
        queue = [requirement_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id in self._nodes:
                result.append(self._nodes[current_id])

            for link in self._links:
                if link.source_node_id == current_id and link.target_node_id not in visited:
                    queue.append(link.target_node_id)

        return result

    def navigateBackward(self, certification_id: str) -> list[TraceNode]:
        result = []
        visited = set()
        queue = [certification_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id in self._nodes:
                result.append(self._nodes[current_id])

            for link in self._links:
                if link.target_node_id == current_id and link.source_node_id not in visited:
                    queue.append(link.source_node_id)

        return result