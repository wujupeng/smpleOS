from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.database import get_pg_pool
from src.infrastructure.repositories.material_lot_repository import MaterialLotRepository
from src.infrastructure.event_bus import event_bus
from src.domain.events.material_lot_created_event import MaterialLotCreatedEvent
from src.infrastructure.event_contract.event_contract_service import get_event_contract_service
from src.domain.services.identity_service import get_identity_service
from src.domain.services.trace_graph_service import get_trace_graph_service

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

    try:
        identity_svc = await get_identity_service()
        await identity_svc.resolve_or_create_identity(
            domain="material_lot",
            domain_id=lot.lot_id,
            label=lot.material_name,
            node_type="material_lot",
            related_domain="block" if body.block_id else None,
            related_domain_id=body.block_id if body.block_id else None,
        )
    except Exception as e:
        logger.warning(f"Identity resolution failed: {e}")

    try:
        tg_svc = await get_trace_graph_service()
        block_node = None
        if body.block_id:
            block_node = tg_svc._cache.find_node_by_domain("block", body.block_id)
            if block_node is None:
                block_node = await tg_svc.create_trace_node(
                    identity_id=None, node_type="block", label=body.block_id,
                    properties={"domain": "block", "domain_id": body.block_id},
                )
        mat_node = await tg_svc.create_trace_node(
            identity_id=None, node_type="material_lot", label=lot.material_name,
            properties={"domain": "material_lot", "domain_id": lot.lot_id},
        )
        if block_node:
            await tg_svc.create_trace_edge(block_node.node_id, mat_node.node_id, "contains_material")
    except Exception as e:
        logger.warning(f"Trace graph update failed: {e}")

    event = MaterialLotCreatedEvent(
        lot_id=lot.lot_id,
        material_code=lot.material_code,
        supplier_id=lot.supplier_id,
        block_id=body.block_id or "",
    )
    try:
        svc = await get_event_contract_service()
        await svc.validate_and_publish(
            "MaterialLotCreated",
            event.model_dump(),
            "aeroforge.material.lot.created",
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