from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.domain.services.identity_service import get_identity_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Identity"])


@router.get("/identities")
async def list_identities(limit: int = 100, offset: int = 0):
    try:
        svc = await get_identity_service()
        return await svc.list_identities(limit, offset)
    except Exception as e:
        logger.error(f"Failed to list identities: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/identities/{identity_id}")
async def get_identity(identity_id: str):
    try:
        svc = await get_identity_service()
        result = await svc.get_identity(identity_id)
    except Exception as e:
        logger.error(f"Failed to get identity: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return result


@router.get("/identities/by-domain/{domain}/{domain_id}")
async def get_identity_by_domain(domain: str, domain_id: str):
    try:
        svc = await get_identity_service()
        result = await svc.get_identity_by_domain(domain, domain_id)
    except Exception as e:
        logger.error(f"Failed to get identity by domain: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"No identity found for {domain}/{domain_id}")
    return result