"""AeroForge-X v6.0 DFX API (physics-twin-service)

Endpoints for circuit breaker, reconnect, and plugin registry.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.domain.services.dfx.circuit_breaker_reconnect_service import (
    CircuitBreakerReconnectService,
    CircuitBreakerConfig,
    ConnectionProtocol,
    ReconnectConfig,
)
from src.domain.services.dfx.plugin_registry_service import (
    PluginRegistryService,
    PluginType,
    UQMethodPlugin,
    DisciplineSolverPlugin,
    RegulatoryLibraryPlugin,
    DataSourceAdapterPlugin,
    NDTMethodAdapterPlugin,
)

router = APIRouter(prefix="/api/v6/physics-twin/dfx", tags=["v6-dfx"])

_circuit_svc = CircuitBreakerReconnectService()
_plugin_svc = PluginRegistryService()


@router.post("/circuit-breaker/register")
async def register_circuit(body: dict):
    equipment_id = body.get("equipment_id", "")
    protocol = ConnectionProtocol(body.get("protocol", "OPC-UA"))
    circuit = _circuit_svc.registerCircuit(equipment_id, protocol)
    return circuit.to_dict()


@router.post("/circuit-breaker/success")
async def record_circuit_success(body: dict):
    equipment_id = body.get("equipment_id", "")
    circuit = _circuit_svc.recordSuccess(equipment_id)
    return circuit.to_dict()


@router.post("/circuit-breaker/failure")
async def record_circuit_failure(body: dict):
    equipment_id = body.get("equipment_id", "")
    circuit = _circuit_svc.recordFailure(equipment_id)
    return circuit.to_dict()


@router.get("/circuit-breaker/{equipment_id}")
async def check_circuit_state(equipment_id: str):
    circuit = _circuit_svc.checkCircuitState(equipment_id)
    if circuit is None:
        return {"error": "Circuit not found"}
    return circuit.to_dict()


@router.post("/circuit-breaker/reconnect")
async def attempt_reconnect(body: dict):
    equipment_id = body.get("equipment_id", "")
    success = body.get("success", False)
    error = body.get("error", "")
    attempt = _circuit_svc.attemptReconnect(equipment_id, success, error)
    return attempt.to_dict()


@router.get("/circuit-breaker/{equipment_id}/last-valid")
async def get_last_valid_values(equipment_id: str):
    values = _circuit_svc.getLastValidValues(equipment_id)
    return {k: v.to_dict() for k, v in values.items()}


@router.post("/plugins/register")
async def register_plugin(body: dict):
    plugin_type = PluginType(body.get("plugin_type", ""))
    name = body.get("name", "")

    plugin_map = {
        PluginType.UQ_METHOD: lambda: UQMethodPlugin(name, body.get("method_type", "")),
        PluginType.DISCIPLINE_SOLVER: lambda: DisciplineSolverPlugin(name),
        PluginType.REGULATORY_LIBRARY: lambda: RegulatoryLibraryPlugin(name, body.get("authority", "")),
        PluginType.DATA_SOURCE_ADAPTER: lambda: DataSourceAdapterPlugin(body.get("protocol", "")),
        PluginType.NDT_METHOD_ADAPTER: lambda: NDTMethodAdapterPlugin(name),
    }

    factory = plugin_map.get(plugin_type)
    if factory is None:
        return {"registered": False, "reason": "Unknown plugin type"}

    plugin = factory()
    descriptor = _plugin_svc.registerPlugin(plugin)
    return {"registered": True, "descriptor": descriptor.to_dict()}


@router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: dict):
    params = body.get("params", {})
    result = _plugin_svc.executePlugin(plugin_id, params)
    return result.to_dict()


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str):
    descriptor = _plugin_svc.enablePlugin(plugin_id)
    if descriptor is None:
        return {"enabled": False, "reason": "Plugin not found"}
    return {"enabled": True, "descriptor": descriptor.to_dict()}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str):
    descriptor = _plugin_svc.disablePlugin(plugin_id)
    if descriptor is None:
        return {"disabled": False, "reason": "Plugin not found"}
    return {"disabled": True, "descriptor": descriptor.to_dict()}


@router.get("/plugins")
async def list_plugins(plugin_type: str = ""):
    if plugin_type:
        pt = PluginType(plugin_type)
        descriptors = _plugin_svc.getPluginsByType(pt)
    else:
        descriptors = _plugin_svc.getAllPlugins()
    return [d.to_dict() for d in descriptors]


@router.post("/plugins/{plugin_id}/validate")
async def validate_plugin_config(plugin_id: str, body: dict):
    config = body.get("config", {})
    valid = _plugin_svc.validatePluginConfig(plugin_id, config)
    return {"plugin_id": plugin_id, "valid": valid}