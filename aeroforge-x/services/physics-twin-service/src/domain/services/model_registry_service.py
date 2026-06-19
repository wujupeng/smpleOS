from __future__ import annotations

import hashlib
from typing import Any

from src.domain.plugins.dof6_model import DOF6Model
from src.domain.plugins.battery_model import BatteryModel
from src.domain.plugins.control_model import ControlModel


_BUILTIN_PLUGINS: dict[str, type] = {
    "6DOF": DOF6Model,
    "Battery": BatteryModel,
    "Control": ControlModel,
}


class ModelRegistryService:

    _plugins: dict[str, dict[str, Any]] = {}

    @classmethod
    def register_plugin(cls, name: str, model_type: str, supported_fidelities: list[str], schema_refs: list[str] | None = None, plugin_path: str = "") -> dict[str, Any]:
        if name in cls._plugins:
            raise ValueError(f"Plugin '{name}' already registered")

        entry = {
            "name": name,
            "model_type": model_type,
            "supported_fidelities": supported_fidelities,
            "schema_references": schema_refs or [],
            "plugin_path": plugin_path,
            "interface_version": "1.0.0",
            "checksum": cls._compute_checksum(plugin_path) if plugin_path else "",
            "status": "Registered",
        }
        cls._plugins[name] = entry
        return entry

    @classmethod
    def discover_plugins(cls, model_type: str | None = None, fidelity: str | None = None) -> list[dict[str, Any]]:
        results = []
        for entry in cls._plugins.values():
            if model_type and entry["model_type"] != model_type:
                continue
            if fidelity and fidelity not in entry["supported_fidelities"]:
                continue
            results.append(entry)
        return results

    @classmethod
    def load_plugin(cls, name: str, fidelity: str = "Low", params: dict[str, Any] | None = None) -> Any:
        entry = cls._plugins.get(name)
        if entry is None:
            builtin_cls = _BUILTIN_PLUGINS.get(name)
            if builtin_cls is None:
                raise ValueError(f"Plugin '{name}' not found")
            instance = builtin_cls(fidelity=fidelity)
            if params:
                instance.initialize(params)
            entry = {
                "name": name,
                "model_type": name,
                "supported_fidelities": instance.get_supported_fidelities(),
                "status": "Loaded",
            }
            cls._plugins[name] = entry
            return instance

        if fidelity not in entry["supported_fidelities"]:
            raise ValueError(f"Fidelity '{fidelity}' not supported by plugin '{name}'")

        builtin_cls = _BUILTIN_PLUGINS.get(entry["model_type"])
        if builtin_cls is None:
            raise ValueError(f"Unknown model type: {entry['model_type']}")

        instance = builtin_cls(fidelity=fidelity)
        if params:
            instance.initialize(params)
        entry["status"] = "Loaded"
        return instance

    @classmethod
    def hot_reload_plugin(cls, name: str) -> dict[str, Any]:
        entry = cls._plugins.get(name)
        if entry is None:
            return {"error": f"Plugin '{name}' not found"}
        entry["status"] = "Loaded"
        return {"name": name, "status": "hot_reloaded"}

    @classmethod
    def validate_plugin_interface(cls, name: str) -> dict[str, Any]:
        entry = cls._plugins.get(name)
        if entry is None:
            return {"valid": False, "error": f"Plugin '{name}' not found"}

        required_methods = ["initialize", "step", "get_state", "reset", "get_supported_fidelities", "get_schema_references"]
        builtin_cls = _BUILTIN_PLUGINS.get(entry["model_type"])
        if builtin_cls is None:
            return {"valid": False, "error": f"Unknown model type: {entry['model_type']}"}

        missing = [m for m in required_methods if not hasattr(builtin_cls, m)]
        if missing:
            return {"valid": False, "error": f"Missing methods: {missing}"}
        return {"valid": True}

    @classmethod
    def _compute_checksum(cls, path: str) -> str:
        if not path:
            return ""
        h = hashlib.sha256()
        h.update(path.encode())
        return h.hexdigest()[:16]


for _name, _cls in _BUILTIN_PLUGINS.items():
    try:
        ModelRegistryService.register_plugin(
            name=_name,
            model_type=_name,
            supported_fidelities=["Low", "Mid", "Detail"],
            schema_refs=_cls(fidelity="Low").get_schema_references(),
        )
    except ValueError:
        pass