from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.propagation_chain_service import PropagationChainService
from src.domain.handlers.v3_handlers import _HANDLER_INSTANCES

router = APIRouter(prefix="/api/v3/workflow-engine", tags=["Propagation v3"])


@router.post("/propagation-chains")
async def configure_propagation_chain(body: dict[str, Any]):
    chain_type = body.get("chain_type", "")
    result = PropagationChainService.configure_chain(chain_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/propagation-chains")
async def list_propagation_chains():
    return PropagationChainService.list_chains()


@router.get("/propagation-chains/{chain_id}/status")
async def get_chain_status(chain_id: str):
    result = PropagationChainService.get_chain_status(chain_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Chain execution not found")
    return result


@router.get("/propagation-chains/{chain_id}/audit")
async def get_chain_audit(chain_id: str):
    result = PropagationChainService.get_chain_status(chain_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Chain execution not found")
    return {"chain_id": chain_id, "audit_log": result.get("nodes", [])}


@router.get("/propagation-chains/configs")
async def get_chain_configs():
    return PropagationChainService.get_chain_configs()


@router.post("/propagation-chains/execute")
async def execute_propagation_chain(body: dict[str, Any]):
    chain_type = body.get("chain_type", "")
    event_data = body.get("event_data", {})
    object_data = body.get("object_data")
    return PropagationChainService.execute_chain(chain_type, event_data, object_data)


@router.get("/handlers")
async def list_handlers():
    return [{"handler_name": name, "schema_references": h.get_schema_references()} for name, h in _HANDLER_INSTANCES.items()]


@router.post("/handlers/{name}/hot-reload")
async def hot_reload_handler(name: str):
    if name not in _HANDLER_INSTANCES:
        raise HTTPException(status_code=404, detail=f"Handler '{name}' not found")
    return {"handler_name": name, "status": "hot_reloaded"}