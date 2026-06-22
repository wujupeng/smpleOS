from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.database import get_pg_pool
from src.infrastructure.repositories.material_lot_repository import MaterialLotRepository
from src.infrastructure.event_bus import event_bus
from src.domain.events.material_lot_created_event import MaterialLotCreatedEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Material Thread"])

_repo: MaterialLotRepository | None = None
_repo_initialized = False


async def _ensure_repo() -> MaterialLotRepository:
    global _repo, _repo_initialized
    if _repo_initialized and _repo is not None:
        return _repo
    try:
        pool = await get_pg_pool()
        _repo = MaterialLotRepository(pool)
        _repo_initialized = True
        return _repo
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


class CreateMaterialLotRequest(BaseModel):
    material_code: str
    material_name: str
    supplier_id: str
    manufacture_date: str
    received_date: str
    certificate_no: str
    block_id: Optional[str] = None


@router.post("/material-lots", status_code=201)
async def create_material_lot(body: CreateMaterialLotRequest):
    repo = await _ensure_repo()
    try:
        lot = await repo.create(
            material_code=body.material_code,
            material_name=body.material_name,
            supplier_id=body.supplier_id,
            manufacture_date=body.manufacture_date,
            received_date=body.received_date,
            certificate_no=body.certificate_no,
            block_id=body.block_id,
        )
    except Exception as e:
        logger.error(f"Failed to create MaterialLot: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    event = MaterialLotCreatedEvent(
        lot_id=lot.lot_id,
        material_code=lot.material_code,
        supplier_id=lot.supplier_id,
        block_id=body.block_id or "",
    )
    try:
        await event_bus.publish_jetstream(
            "aeroforge.material.lot.created",
            event.model_dump(),
        )
    except Exception as e:
        logger.warning(f"Event publish failed: {e}")

    return lot.to_dict()


@router.get("/material-lots/{lot_id}")
async def get_material_lot(lot_id: str):
    repo = await _ensure_repo()
    lot = await repo.find_by_id(lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail=f"MaterialLot not found: {lot_id}")
    return lot.to_dict()


@router.get("/blocks/{block_id}/materials")
async def get_block_materials(block_id: str):
    repo = await _ensure_repo()
    lots = await repo.find_by_block(block_id)
    return [lot.to_dict() for lot in lots]


@router.get("/material-lots")
async def list_material_lots(limit: int = 100, offset: int = 0):
    repo = await _ensure_repo()
    lots = await repo.find_all(limit=limit, offset=offset)
    return [lot.to_dict() for lot in lots]