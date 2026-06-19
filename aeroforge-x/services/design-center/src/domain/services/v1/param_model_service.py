from __future__ import annotations

import math
from typing import Any

from src.domain.entities.v1.parametric_model import ParametricModel, ModelType, ModelStatus


class ParamModelService:
    def generate_model(self, spec_params: dict[str, Any], model_type: ModelType = ModelType.FULL_ASSEMBLY) -> ParametricModel:
        model = ParametricModel(
            model_name=f"Model-{spec_params.get('aircraft_type', 'unknown')}",
            model_type=model_type,
            spec_ref=spec_params.get("spec_id"),
            parameters=spec_params.copy(),
            created_by=spec_params.get("created_by"),
        )
        payload = float(spec_params.get("payload_kg", 0))
        mtow = payload * 2.5 if payload > 0 else 100.0
        wing_loading = 150.0
        wing_area = (mtow / wing_loading) if wing_loading > 0 else 1.0
        aspect_ratio = float(spec_params.get("aspect_ratio", 8.0))
        span = math.sqrt(wing_area * aspect_ratio)
        model.parameters.update({
            "mtow_estimate_kg": mtow,
            "wing_area_m2": wing_area,
            "wing_span_m": span,
            "aspect_ratio": aspect_ratio,
        })
        model.mark_generated()
        return model

    def update_model(self, model: ParametricModel, updates: dict[str, Any]) -> ParametricModel:
        model.update_parameters(updates)
        self._propagate_parameter_changes(model, updates)
        return model

    def _propagate_parameter_changes(self, model: ParametricModel, updates: dict[str, Any]) -> None:
        if "wing_span_m" in updates or "aspect_ratio" in updates:
            span = model.parameters.get("wing_span_m", 0)
            ar = model.parameters.get("aspect_ratio", 8.0)
            if span > 0 and ar > 0:
                wing_area = (span ** 2) / ar
                model.parameters["wing_area_m2"] = wing_area
                root_chord = (2 * wing_area) / (span * (1 + model.parameters.get("taper_ratio", 0.5)))
                model.parameters["root_chord_m"] = root_chord
        if "payload_kg" in updates:
            payload = float(updates["payload_kg"])
            mtow = payload * 2.5
            model.parameters["mtow_estimate_kg"] = mtow