from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infrastructure.event_contract.event_contract_service import get_event_contract_service
from src.infrastructure.event_contract.schema_registry import schema_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Event Contract"])


@router.get("/event-contracts")
async def list_event_contracts():
    try:
        svc = await get_event_contract_service()
        db_contracts = await svc.list_contracts()
    except Exception:
        db_contracts = []
    mem_schemas = schema_registry.list_schemas()
    return {
        "db_contracts": db_contracts,
        "loaded_schemas": mem_schemas,
    }


@router.get("/event-contracts/{event_type}")
async def get_event_contract(event_type: str):
    schema = schema_registry.get_schema(event_type)
    if schema is None:
        try:
            svc = await get_event_contract_service()
            db_contract = await svc.get_contract(event_type)
            if db_contract:
                return db_contract
        except Exception:
            pass
        raise HTTPException(status_code=404, detail=f"Event contract not found: {event_type}")
    return {"event_type": event_type, "schema": schema}


class RegisterContractRequest(BaseModel):
    event_type: str
    schema: dict
    version: str = "1.0.0"


@router.post("/event-contracts", status_code=201)
async def register_event_contract(body: RegisterContractRequest):
    try:
        svc = await get_event_contract_service()
        result = await svc.register_contract(body.event_type, body.schema, body.version)
        return result
    except Exception as e:
        logger.error(f"Failed to register contract: {e}")
        raise HTTPException(status_code=422, detail=str(e))