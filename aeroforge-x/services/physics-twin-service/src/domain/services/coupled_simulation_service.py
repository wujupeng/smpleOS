from __future__ import annotations

from typing import Any

from src.domain.services.model_registry_service import ModelRegistryService


class CoupledSimulationService:

    @staticmethod
    def create_coupled_runtime(
        model_configs: list[dict[str, Any]],
        data_exchange_map: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        models = []
        for config in model_configs:
            plugin_name = config.get("model_type", "")
            fidelity = config.get("fidelity", "Low")
            params = config.get("params", {})
            instance = ModelRegistryService.load_plugin(plugin_name, fidelity, params)
            models.append({"name": plugin_name, "fidelity": fidelity, "instance": instance})

        default_exchange = [
            {"source": "6DOF", "source_output": "state.attitude", "target": "Control", "target_input": "current"},
            {"source": "6DOF", "source_output": "state.angular_rates", "target": "Control", "target_input": "angular_rates"},
            {"source": "Control", "source_output": "state.elevator_cmd", "target": "6DOF", "target_input": "elevator_cmd"},
            {"source": "Control", "source_output": "state.aileron_cmd", "target": "6DOF", "target_input": "aileron_cmd"},
            {"source": "Control", "source_output": "state.rudder_cmd", "target": "6DOF", "target_input": "rudder_cmd"},
            {"source": "Control", "source_output": "state.throttle_cmd", "target": "6DOF", "target_input": "thrust_scale"},
            {"source": "6DOF", "source_output": "state.velocity", "target": "Battery", "target_input": "power_demand_factor"},
        ]

        return {
            "runtime_id": f"coupled-{id(models)}",
            "models": [{"name": m["name"], "fidelity": m["fidelity"]} for m in models],
            "data_exchange_map": data_exchange_map or default_exchange,
            "status": "Ready",
        }

    @staticmethod
    def step_coupled_simulation(
        models: list[dict[str, Any]],
        data_exchange_map: list[dict[str, Any]],
        dt: float,
    ) -> dict[str, Any]:
        outputs: dict[str, dict[str, Any]] = {}

        for model_info in models:
            name = model_info["name"]
            instance = model_info["instance"]

            inputs = {}
            for mapping in data_exchange_map:
                if mapping["target"] == name:
                    source_output = mapping["source_output"]
                    source_data = outputs.get(mapping["source"], {})
                    value = CoupledSimulationService._extract_nested(source_data, source_output)
                    if value is not None:
                        inputs[mapping["target_input"]] = value

            if name == "6DOF" and "thrust_scale" in inputs:
                thrust_base = instance._params.get("max_thrust", 5000.0)
                inputs["thrust"] = thrust_base * inputs.pop("thrust_scale", 0.5)

            result = instance.step(dt, inputs)
            outputs[name] = result

        return {"step_outputs": outputs, "dt": dt}

    @staticmethod
    def switch_runtime_fidelity(models: list[dict[str, Any]], model_name: str, new_fidelity: str) -> dict[str, Any]:
        for model_info in models:
            if model_info["name"] == model_name:
                old_instance = model_info["instance"]
                params = old_instance._params
                new_instance = ModelRegistryService.load_plugin(model_name, new_fidelity, params)
                model_info["instance"] = new_instance
                model_info["fidelity"] = new_fidelity
                return {"model_name": model_name, "old_fidelity": model_info.get("fidelity", "Low"), "new_fidelity": new_fidelity}
        return {"error": f"Model '{model_name}' not found in runtime"}

    @staticmethod
    def _extract_nested(data: dict, path: str) -> Any:
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current