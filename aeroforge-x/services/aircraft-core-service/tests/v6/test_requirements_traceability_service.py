"""AeroForge-X V6.0/V6.1 Unit Tests - Requirements Traceability Service
REQ-VP-024, REQ-CERT-001~007
"""

import pytest

from src.domain.services.certification.requirements_traceability_service import (
    RequirementsTraceabilityService,
    TraceNode,
    TraceNodeType,
    TraceLink,
    LinkType,
    BrokenLink,
    TraceabilityCoverage,
)


@pytest.fixture
def service():
    return RequirementsTraceabilityService()


def _make_node(node_type: TraceNodeType, name: str) -> TraceNode:
    return TraceNode(node_id=f"{node_type.value}-{name}", node_type=node_type, name=name)


class TestTraceLinkCreation:

    def test_create_trace_link(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")
        link = service.createTraceLink(req, design, LinkType.SATISFIED_BY)
        assert link.source_node_id == req.node_id
        assert link.target_node_id == design.node_id
        assert link.link_type == LinkType.SATISFIED_BY

    def test_create_multiple_links(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")
        test = _make_node(TraceNodeType.TEST_CASE, "TC-001")
        service.createTraceLink(req, design, LinkType.SATISFIED_BY)
        service.createTraceLink(design, test, LinkType.VERIFIED_BY)


class TestBrokenLinkDetection:

    def test_detect_broken_link_no_downstream(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        service._nodes[req.node_id] = req
        broken = service.detectBrokenLinks(req.node_id)
        assert len(broken) > 0
        assert broken[0].missing_link_type == LinkType.SATISFIED_BY

    def test_detect_no_broken_links_full_chain(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")
        test = _make_node(TraceNodeType.TEST_CASE, "TC-001")
        evidence = _make_node(TraceNodeType.EVIDENCE_ITEM, "EV-001")
        cert = _make_node(TraceNodeType.CERTIFICATION_ITEM, "CI-001")

        service.createTraceLink(req, design, LinkType.SATISFIED_BY)
        service.createTraceLink(design, test, LinkType.VERIFIED_BY)
        service.createTraceLink(test, evidence, LinkType.PRODUCES)
        service.createTraceLink(evidence, cert, LinkType.DEMONSTRATES)

        broken = service.detectBrokenLinks(req.node_id)
        assert len(broken) == 0


class TestTraceabilityCoverage:

    def test_coverage_empty(self, service):
        coverage = service.computeTraceabilityCoverage("PROJ-001")
        assert coverage.total_requirements == 0
        assert coverage.coverage_percentage == 100.0

    def test_coverage_partial(self, service):
        req1 = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        req2 = _make_node(TraceNodeType.REQUIREMENT, "REQ-002")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")

        service.createTraceLink(req1, design, LinkType.SATISFIED_BY)
        service._nodes[req2.node_id] = req2

        coverage = service.computeTraceabilityCoverage("PROJ-001")
        assert coverage.total_requirements == 2
        assert coverage.coverage_percentage < 100.0


class TestBidirectionalNavigation:

    def test_forward_navigation(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")
        service.createTraceLink(req, design, LinkType.SATISFIED_BY)

        forward = service.navigateForward(req.node_id)
        assert len(forward) == 2
        node_ids = [n.node_id for n in forward]
        assert req.node_id in node_ids
        assert design.node_id in node_ids

    def test_backward_navigation(self, service):
        req = _make_node(TraceNodeType.REQUIREMENT, "REQ-001")
        design = _make_node(TraceNodeType.DESIGN_ELEMENT, "Wing-Design")
        service.createTraceLink(req, design, LinkType.SATISFIED_BY)

        backward = service.navigateBackward(design.node_id)
        assert len(backward) == 2