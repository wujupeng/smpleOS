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

    event = NDTCompletedEvent(
        ndt_record_id=ndt.ndt_record_id,
        material_lot_id=ndt.material_lot_id,
        test_type=ndt.test_type,
        result=ndt.result,
    )
    try:
        await event_bus.publish_jetstream("aeroforge.quality.ndt.completed", event.model_dump())
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

    event = CARCreatedEvent(
        car_id=car.car_id,
        ndt_record_id=car.ndt_record_id,
        description=car.description,
        status=car.status,
    )
    try:
        await event_bus.publish_jetstream("aeroforge.quality.car.created", event.model_dump())
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
            await event_bus.publish_jetstream("aeroforge.quality.car.closed", event.model_dump())
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