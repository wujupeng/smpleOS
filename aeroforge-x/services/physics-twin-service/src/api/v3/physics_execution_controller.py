from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.domain.services.model_registry_service import ModelRegistryService
from src.domain.services.coupled_simulation_service import CoupledSimulationService

router = APIRouter(prefix="/api/v3/physics-twin", tags=["Physics Twin v3"])


@router.post("/plugins")
async def register_plugin(body: dict[str, Any]):
    try:
        result = ModelRegistryService.register_plugin(
            name=body.get("name", ""),
            model_type=body.get("model_type", ""),
            supported_fidelities=body.get("supported_fidelities", ["Low"]),
            schema_refs=body.get("schema_references"),
            plugin_path=body.get("plugin_path", ""),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/plugins")
async def discover_plugins(model_type: str | None = None, fidelity: str | None = None):
    return ModelRegistryService.discover_plugins(model_type, fidelity)


@router.post("/plugins/{name}/hot-reload")
async def hot_reload_plugin(name: str):
    result = ModelRegistryService.hot_reload_plugin(name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/models/execute")
async def execute_model(body: dict[str, Any]):
    model_type = body.get("model_type", "")
    fidelity = body.get("fidelity", "Low")
    params = body.get("params", {})
    dt = body.get("dt", 0.01)
    steps = body.get("steps", 100)
    inputs = body.get("inputs", {})

    try:
        instance = ModelRegistryService.load_plugin(model_type, fidelity, params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = []
    for i in range(steps):
        result = instance.step(dt, inputs)
        results.append(result)

    return {"model_type": model_type, "fidelity": fidelity, "steps": steps, "results": results}


@router.post("/models/{name}/parameters")
async def set_model_parameters(name: str, body: dict[str, Any]):
    params = body.get("params", {})
    fidelity = body.get("fidelity", "Low")
    try:
        instance = ModelRegistryService.load_plugin(name, fidelity, params)
        return {"status": "parameters_set", "model": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/models/{name}/state")
async def get_model_state(name: str):
    try:
        instance = ModelRegistryService.load_plugin(name)
        return instance.get_state()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/runtimes/coupled")
async def create_coupled_runtime(body: dict[str, Any]):
    model_configs = body.get("model_configs", [])
    data_exchange_map = body.get("data_exchange_map")
    return CoupledSimulationService.create_coupled_runtime(model_configs, data_exchange_map)


@router.post("/runtimes/{runtime_id}/step")
async def step_coupled_simulation(runtime_id: str, body: dict[str, Any]):
    dt = body.get("dt", 0.01)
    model_configs = body.get("model_configs", [])
    data_exchange_map = body.get("data_exchange_map", [])

    models = []
    for config in model_configs:
        plugin_name = config.get("model_type", "")
        fidelity = config.get("fidelity", "Low")
        params = config.get("params", {})
        instance = ModelRegistryService.load_plugin(plugin_name, fidelity, params)
        models.append({"name": plugin_name, "fidelity": fidelity, "instance": instance})

    return CoupledSimulationService.step_coupled_simulation(models, data_exchange_map, dt)


@router.get("/runtimes/{runtime_id}/coupling")
async def get_coupling_config(runtime_id: str):
    return {"runtime_id": runtime_id, "coupling": "6DOF→Control→6DOF, 6DOF→Battery"}