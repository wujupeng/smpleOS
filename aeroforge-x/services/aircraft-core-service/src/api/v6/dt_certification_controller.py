from __future__ import annotations

import logging
import uuid
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from src.infrastructure.database import get_pg_pool
from src.infrastructure.repositories.evidence_repository import EvidenceRepository
from src.infrastructure.repositories.compliance_repository import ComplianceRepository
from src.infrastructure.object_storage import object_storage
from src.infrastructure.event_bus import event_bus
from src.domain.events.evidence_uploaded_event import EvidenceUploadedEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Certification Thread DT"])

_evidence_repo: EvidenceRepository | None = None
_compliance_repo: ComplianceRepository | None = None
_initialized = False

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/tiff", "image/svg+xml",
    "model/step", "model/iges",
    "application/octet-stream",
}


async def _ensure_repos():
    global _evidence_repo, _compliance_repo, _initialized
    if _initialized and _evidence_repo and _compliance_repo:
        return
    try:
        pool = await get_pg_pool()
        _evidence_repo = EvidenceRepository(pool)
        _compliance_repo = ComplianceRepository(pool)
        _initialized = True
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


@router.post("/certification/evidence/upload", status_code=201)
async def upload_certification_evidence(
    file: UploadFile = File(...),
    requirement_id: str = Form(...),
    regulation: str = Form("FAR-25"),
    description: str = Form(""),
):
    await _ensure_repos()

    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_CONTENT_TYPES and not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")

    file_data = await file.read()
    file_size = len(file_data)
    if file_size > 52428800:
        raise HTTPException(status_code=413, detail="File size exceeds 50MB limit")

    await _compliance_repo.find_or_create(
        requirement_id=requirement_id,
        regulation=regulation,
        description=description or f"Compliance requirement {requirement_id}",
    )

    file_id = str(uuid.uuid4())
    bucket = "aeroforge-cert-evidence"
    upload_ok = False
    try:
        result = await object_storage.upload_file(
            bucket=bucket,
            file_name=file_id,
            file_data=file_data,
            content_type=content_type,
        )
        if result is not None:
            upload_ok = True
    except Exception as e:
        logger.warning(f"MinIO upload failed: {e}")

    if not upload_ok:
        local_dir = f"/tmp/aeroforge-evidence/{bucket}"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file_id)
        with open(local_path, "wb") as f:
            f.write(file_data)
        logger.warning(f"Stored evidence locally: {local_path}")

    evidence = await _evidence_repo.create(
        requirement_id=requirement_id,
        file_id=file_id,
        file_name=file.filename or "unnamed",
        bucket=bucket,
        content_type=content_type,
        file_size=file_size,
    )

    event = EvidenceUploadedEvent(
        evidence_id=evidence.evidence_id,
        requirement_id=requirement_id,
        file_id=file_id,
        file_name=evidence.file_name,
    )
    try:
        await event_bus.publish_jetstream("aeroforge.cert.evidence.uploaded", event.model_dump())
    except Exception as e:
        logger.warning(f"Event publish failed: {e}")

    presigned_url = None
    try:
        presigned_url = await object_storage.get_presigned_url(bucket, file_id)
    except Exception:
        pass

    resp = evidence.to_dict()
    resp["presigned_url"] = presigned_url
    return resp


@router.get("/certification/evidence/{evidence_id}")
async def get_certification_evidence(evidence_id: str):
    await _ensure_repos()
    evidence = await _evidence_repo.find_by_id(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Evidence not found: {evidence_id}")

    presigned_url = None
    try:
        presigned_url = await object_storage.get_presigned_url(evidence.bucket, evidence.file_id)
    except Exception:
        pass

    resp = evidence.to_dict()
    resp["presigned_url"] = presigned_url
    return resp


@router.get("/certification/compliance/{requirement_id}")
async def get_compliance(requirement_id: str):
    await _ensure_repos()
    compliance = await _compliance_repo.find_by_id(requirement_id)
    if compliance is None:
        compliance = await _compliance_repo.find_or_create(
            requirement_id=requirement_id,
            regulation="FAR-25",
            description=f"Compliance requirement {requirement_id}",
        )

    evidences = await _compliance_repo.find_evidences(requirement_id)
    resp = compliance.to_dict()
    resp["evidences"] = [e.to_dict() for e in evidences]
    return resp


class UpdateComplianceRequestModel(BaseModel):
    compliance_status: str
    responsible_person: Optional[str] = None


@router.patch("/certification/compliance/{requirement_id}")
async def update_compliance(requirement_id: str, body: UpdateComplianceRequestModel):
    await _ensure_repos()
    compliance = await _compliance_repo.find_by_id(requirement_id)
    if compliance is None:
        raise HTTPException(status_code=404, detail=f"Compliance requirement not found: {requirement_id}")

    updated = await _compliance_repo.update_compliance_status(
        requirement_id=requirement_id,
        compliance_status=body.compliance_status,
        responsible_person=body.responsible_person,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Compliance requirement not found: {requirement_id}")
    return updated.to_dict()


@router.get("/certification/compliance-requirements")
async def list_compliance_requirements(limit: int = 100, offset: int = 0):
    await _ensure_repos()
    items = await _compliance_repo.find_all(limit=limit, offset=offset)
    return [item.to_dict() for item in items]