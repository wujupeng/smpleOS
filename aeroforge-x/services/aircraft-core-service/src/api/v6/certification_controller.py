from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.certification.requirements_traceability_service import (
    RequirementsTraceabilityService,
    TraceNode,
    TraceNodeType,
    LinkType,
)
from src.domain.services.certification.regulatory_library_service import (
    RegulatoryLibraryService,
    RegulationType,
)
from src.domain.services.certification.compliance_checklist_service import (
    ComplianceChecklistService,
)

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Certification Digital Thread v6"])

_trace_service = RequirementsTraceabilityService()
_regulatory_service = RegulatoryLibraryService()
_checklist_service = ComplianceChecklistService()


@router.post("/trace-links")
async def create_trace_link(body: dict[str, Any]):
    source_data = body.get("source", {})
    target_data = body.get("target", {})
    link_type_str = body.get("link_type", "Satisfies")

    source = TraceNode(
        node_id=source_data.get("node_id", ""),
        node_type=TraceNodeType(source_data.get("node_type", "Requirement")),
        name=source_data.get("name", ""),
    )
    target = TraceNode(
        node_id=target_data.get("node_id", ""),
        node_type=TraceNodeType(target_data.get("node_type", "DesignElement")),
        name=target_data.get("name", ""),
    )
    link = _trace_service.createTraceLink(
        source=source, target=target, link_type=LinkType(link_type_str)
    )
    return link.to_dict()


@router.get("/traceability-matrices/{project_id}")
async def get_traceability_matrix(project_id: str):
    matrix = _trace_service.getTraceabilityMatrix(project_id=project_id)
    return matrix.to_dict()


@router.post("/traceability-coverage")
async def compute_traceability_coverage(body: dict[str, Any]):
    project_id = body.get("project_id", "")
    coverage = _trace_service.computeTraceabilityCoverage(project_id=project_id)
    return coverage.to_dict()


@router.post("/trace-links/detect-broken")
async def detect_broken_links(body: dict[str, Any]):
    requirement_id = body.get("requirement_id", "")
    broken = _trace_service.detectBrokenLinks(requirement_id=requirement_id)
    return {"broken_links": [b.to_dict() for b in broken]}


@router.post("/trace-links/navigate-forward")
async def navigate_forward(body: dict[str, Any]):
    requirement_id = body.get("requirement_id", "")
    nodes = _trace_service.navigateForward(requirement_id=requirement_id)
    return {"nodes": [n.to_dict() for n in nodes]}


@router.post("/trace-links/navigate-backward")
async def navigate_backward(body: dict[str, Any]):
    certification_id = body.get("certification_id", "")
    nodes = _trace_service.navigateBackward(certification_id=certification_id)
    return {"nodes": [n.to_dict() for n in nodes]}


@router.post("/regulatory-libraries")
async def import_regulatory_library(body: dict[str, Any]):
    regulation_type = RegulationType(body.get("regulation_type", "FAA_Part_25"))
    title = body.get("title", "")
    version = body.get("version", "1.0")
    library = _regulatory_service.importRegulation(
        regulation_type=regulation_type, title=title, version=version
    )
    return library.to_dict()


@router.put("/regulatory-libraries/{regulation_id}/version")
async def update_regulation_version(regulation_id: str, body: dict[str, Any]):
    new_version = body.get("new_version", "")
    try:
        result = _regulatory_service.updateRegulationVersion(
            regulation_id=regulation_id, new_version=new_version
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/regulatory-requirements/map")
async def map_equivalent_requirements(body: dict[str, Any]):
    faa_section = body.get("faa_section", "")
    easa_section = body.get("easa_section", "")
    mapping = _regulatory_service.mapEquivalentRequirements(
        faa_section=faa_section, easa_section=easa_section
    )
    return mapping.to_dict()


@router.post("/compliance-checklists")
async def generate_compliance_checklist(body: dict[str, Any]):
    regulation_id = body.get("regulation_id", "")
    project_id = body.get("project_id", "")
    library = _regulatory_service.getLibrary(regulation_id)
    if not library:
        raise HTTPException(status_code=404, detail=f"Regulation not found: {regulation_id}")
    checklist = _checklist_service.generateChecklist(regulation=library, project_id=project_id)
    return checklist.to_dict()


@router.post("/compliance-checklists/items/{item_id}/link-evidence")
async def link_checklist_to_evidence(item_id: str, body: dict[str, Any]):
    checklist_id = body.get("checklist_id", "")
    evidence_id = body.get("evidence_id", "")
    try:
        item = _checklist_service.linkChecklistToEvidence(
            checklist_id=checklist_id, item_id=item_id, evidence_id=evidence_id
        )
        return item.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))