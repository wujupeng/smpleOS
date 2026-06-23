from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infrastructure.database import get_pg_pool
from src.infrastructure.repositories.ndt_record_repository import NDTRecordRepository
from src.infrastructure.repositories.car_repository import CARRepository
from src.infrastructure.repositories.material_lot_repository import MaterialLotRepository
from src.infrastructure.event_bus import event_bus
from src.domain.events.ndt_completed_event import NDTCompletedEvent
from src.domain.events.car_created_event import CARCreatedEvent
from src.domain.events.car_closed_event import CARClosedEvent
from src.infrastructure.event_contract.event_contract_service import get_event_contract_service
from src.domain.services.identity_service import get_identity_service
from src.domain.services.trace_graph_service import get_trace_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Quality Thread"])

_ndt_repo: NDTRecordRepository | None = None
_car_repo: CARRepository | None = None
_ml_repo: MaterialLotRepository | None = None
_initialized = False


async def _ensure_repos():
    global _ndt_repo, _car_repo, _ml_repo, _initialized
    if _initialized and _ndt_repo and _car_repo and _ml_repo:
        return
    try:
        pool = await get_pg_pool()
        _ndt_repo = NDTRecordRepository(pool)
        _car_repo = CARRepository(pool)
        _ml_repo = MaterialLotRepository(pool)
        _initialized = True
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


class CreateNDTRecordRequest(BaseModel):
    material_lot_id: str
    test_type: str
    result: str
    inspector: str
    test_date: str
    notes: Optional[str] = None


class CreateCARRequest(BaseModel):
    ndt_record_id: str
    description: str
    responsible_person: str


class UpdateCARRequest(BaseModel):
    status: str
    closed_by: Optional[str] = None


@router.post("/ndt-records", status_code=201)
async def create_ndt_record(body: CreateNDTRecordRequest):
    await _ensure_repos()
    lot = await _ml_repo.find_by_id(body.material_lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail=f"MaterialLot not found: {body.material_lot_id}")

    ndt = await _ndt_repo.create(
        material_lot_id=body.material_lot_id,
        test_type=body.test_type,
        result=body.result,
        inspector=body.inspector,
        test_date=body.test_date,
        notes=body.notes,
    )

    try:
        identity_svc = await get_identity_service()
        await identity_svc.resolve_or_create_identity(
            domain="ndt_record",
            domain_id=ndt.ndt_record_id,
            label=f"NDT-{ndt.test_type}",
            node_type="ndt_record",
            related_domain="material_lot",
            related_domain_id=ndt.material_lot_id,
        )
    except Exception as e:
        logger.warning(f"Identity resolution failed: {e}")

    try:
        tg_svc = await get_trace_graph_service()
        mat_node = tg_svc._cache.find_node_by_domain("material_lot", ndt.material_lot_id)
        ndt_node = await tg_svc.create_trace_node(
            identity_id=None, node_type="ndt_record", label=f"NDT-{ndt.test_type}",
            properties={"domain": "ndt_record", "domain_id": str(ndt.ndt_record_id)},
        )
        if mat_node:
            await tg_svc.create_trace_edge(mat_node.node_id, ndt_node.node_id, "tested_by")
    except Exception as e:
        logger.warning(f"Trace graph update failed: {e}")

    event = NDTCompletedEvent(
        ndt_record_id=ndt.ndt_record_id,
        material_lot_id=ndt.material_lot_id,
        test_type=ndt.test_type,
        result=ndt.result,
    )
    try:
        svc = await get_event_contract_service()
        await svc.validate_and_publish("NDTCompleted", event.model_dump(), "aeroforge.quality.ndt.completed")
    except Exception as e:
        logger.warning(f"Event publish failed: {e}")

    return ndt.to_dict()


@router.get("/ndt-records/{ndt_record_id}")
async def get_ndt_record(ndt_record_id: str):
    await _ensure_repos()
    ndt = await _ndt_repo.find_by_id(ndt_record_id)
    if ndt is None:
        raise HTTPException(status_code=404, detail=f"NDT Record not found: {ndt_record_id}")
    return ndt.to_dict()


@router.post("/corrective-actions", status_code=201)
async def create_car(body: CreateCARRequest):
    await _ensure_repos()
    ndt = await _ndt_repo.find_by_id(body.ndt_record_id)
    if ndt is None:
        raise HTTPException(status_code=404, detail=f"NDT Record not found: {body.ndt_record_id}")
    if ndt.result == "pass":
        raise HTTPException(
            status_code=400,
            detail="CAR can only be created for failed or conditional NDT results",
        )

    car = await _car_repo.create(
        ndt_record_id=body.ndt_record_id,
        description=body.description,
        responsible_person=body.responsible_person,
    )

    try:
        identity_svc = await get_identity_service()
        await identity_svc.resolve_or_create_identity(
            domain="car",
            domain_id=car.car_id,
            label=car.description[:80],
            node_type="car",
            related_domain="ndt_record",
            related_domain_id=car.ndt_record_id,
        )
    except Exception as e:
        logger.warning(f"Identity resolution failed: {e}")

    try:
        tg_svc = await get_trace_graph_service()
        ndt_node = tg_svc._cache.find_node_by_domain("ndt_record", str(car.ndt_record_id))
        car_node = await tg_svc.create_trace_node(
            identity_id=None, node_type="car", label=car.description[:80],
            properties={"domain": "car", "domain_id": str(car.car_id)},
        )
        if ndt_node:
            await tg_svc.create_trace_edge(ndt_node.node_id, car_node.node_id, "corrected_by")
    except Exception as e:
        logger.warning(f"Trace graph update failed: {e}")

    event = CARCreatedEvent(
        car_id=car.car_id,
        ndt_record_id=car.ndt_record_id,
        description=car.description,
        status=car.status,
    )
    try:
        svc = await get_event_contract_service()
        await svc.validate_and_publish("CARCreated", event.model_dump(), "aeroforge.quality.car.created")
    except Exception as e:
        logger.warning(f"Event publish failed: {e}")

    return car.to_dict()


@router.patch("/corrective-actions/{car_id}")
async def update_car(car_id: str, body: UpdateCARRequest):
    await _ensure_repos()
    existing = await _car_repo.find_by_id(car_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"CAR not found: {car_id}")
    if existing.status == "closed":
        raise HTTPException(status_code=400, detail="CAR is already closed")

    car = await _car_repo.update_status(
        car_id=car_id,
        status=body.status,
        closed_by=body.closed_by,
    )
    if car is None:
        raise HTTPException(status_code=404, detail=f"CAR not found: {car_id}")

    if body.status == "closed":
        event = CARClosedEvent(
            car_id=car.car_id,
            closed_by=body.closed_by or "",
        )
        try:
            svc = await get_event_contract_service()
            await svc.validate_and_publish("CARClosed", event.model_dump(), "aeroforge.quality.car.closed")
        except Exception as e:
            logger.warning(f"Event publish failed: {e}")

    return car.to_dict()


@router.get("/material-lots/{lot_id}/quality")
async def get_quality_thread(lot_id: str):
    await _ensure_repos()
    lot = await _ml_repo.find_by_id(lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail=f"MaterialLot not found: {lot_id}")

    ndt_records = await _ndt_repo.find_by_material_lot(lot_id)
    result = {
        "lot_id": lot_id,
        "ndt_records": [],
    }
    for ndt in ndt_records:
        cars = await _car_repo.find_by_ndt_record(ndt.ndt_record_id)
        ndt_dict = ndt.to_dict()
        ndt_dict["cars"] = [car.to_dict() for car in cars]
        result["ndt_records"].append(ndt_dict)

    return result