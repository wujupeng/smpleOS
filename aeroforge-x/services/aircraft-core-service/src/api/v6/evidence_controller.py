from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query

from src.infrastructure.object_storage import object_storage

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Evidence Storage"])


@router.post("/evidence/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    bucket: str = Form("aeroforge-cert-evidence"),
):
    content_type = file.content_type or "application/octet-stream"
    file_data = await file.read()
    try:
        result = await object_storage.upload_file(
            bucket=bucket,
            file_name=file.filename or "unnamed",
            file_data=file_data,
            content_type=content_type,
        )
    except ValueError as e:
        msg = str(e)
        if "content type" in msg.lower():
            raise HTTPException(status_code=415, detail=msg)
        if "size" in msg.lower():
            raise HTTPException(status_code=413, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    if result is None:
        raise HTTPException(status_code=503, detail="MinIO is not available")
    return result


@router.get("/evidence/{file_id}/url")
async def get_evidence_url(
    file_id: str,
    bucket: str = Query("aeroforge-cert-evidence"),
):
    url = await object_storage.get_presigned_url(bucket, file_id)
    if url is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    return {"file_id": file_id, "url": url}