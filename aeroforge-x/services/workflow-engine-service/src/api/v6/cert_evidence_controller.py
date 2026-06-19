from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.certification.certification_evidence_assembly_service import (
    CertificationEvidenceAssemblyService,
    EvidenceItem,
    EvidenceType,
    EvidenceVerificationStatus,
)

router = APIRouter(prefix="/api/v6/workflow-engine", tags=["Cert Evidence v6"])

_evidence_service = CertificationEvidenceAssemblyService()


@router.post("/cert-evidence-packages")
async def assemble_evidence_package(body: dict[str, Any]):
    checklist_id = body.get("checklist_id", "")
    project_id = body.get("project_id", "")
    items_data = body.get("evidence_items", [])
    evidence_items = [
        EvidenceItem(
            evidence_id=i.get("evidence_id", ""),
            evidence_type=EvidenceType(i.get("evidence_type", "TestReport")),
            document_ref=i.get("document_ref", ""),
            verification_status=EvidenceVerificationStatus(i.get("verification_status", "Draft")),
            regulation_section=i.get("regulation_section", ""),
        )
        for i in items_data
    ]
    package = _evidence_service.assembleEvidencePackage(
        checklist_id=checklist_id, project_id=project_id, evidence_items=evidence_items
    )
    return package.to_dict()


@router.post("/cert-evidence-packages/{package_id}/validate")
async def validate_evidence_package(package_id: str, body: dict[str, Any]):
    required_items = body.get("required_checklist_items", [])
    try:
        result = _evidence_service.validatePackageCompleteness(
            package_id=package_id, required_checklist_items=required_items
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/cert-evidence-packages/{package_id}/lock")
async def lock_evidence_package(package_id: str):
    try:
        package = _evidence_service.lockEvidencePackage(package_id=package_id)
        return package.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cert-evidence-packages/{package_id}/export")
async def export_evidence_package(package_id: str, body: dict[str, Any]):
    format = body.get("format", "PDF")
    try:
        result = _evidence_service.exportEvidencePackage(package_id=package_id, format=format)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))