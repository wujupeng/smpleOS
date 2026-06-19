from __future__ import annotations

from typing import Any

from ..value_objects import AircraftType


RECOMMENDATION_RULES: list[dict[str, Any]] = [
    {
        "conditions": {"power_type": "electric", "vtol": True},
        "recommended_type": AircraftType.EVTOL,
        "reason": "电动+垂直起降需求 → 推荐eVTOL类型",
    },
    {
        "conditions": {"cruise_speed_kmh_max": 150, "payload_kg_max": 200},
        "recommended_type": AircraftType.GLIDER,
        "reason": "低巡航速度+轻载荷 → 推荐滑翔机类型",
    },
    {
        "conditions": {"payload_kg_max": 50, "crew": 0},
        "recommended_type": AircraftType.UAV,
        "reason": "小型+无人 → 推荐无人机类型",
    },
]

TYPE_TEMPLATES: dict[str, dict[str, Any]] = {
    AircraftType.FIXED_WING: {
        "default_params": {
            "aspect_ratio": 12,
            "wing_sweep_deg": 3,
            "taper_ratio": 0.5,
            "airfoil_type": "NACA 4415",
            "fuselage_fineness_ratio": 8,
        },
        "typical_range_km": [100, 3000],
        "typical_payload_kg": [50, 5000],
    },
    AircraftType.EVTOL: {
        "default_params": {
            "aspect_ratio": 6,
            "wing_sweep_deg": 0,
            "taper_ratio": 0.8,
            "airfoil_type": "NACA 0012",
            "fuselage_fineness_ratio": 5,
            "rotor_count": 4,
            "rotor_diameter_m": 2.0,
        },
        "typical_range_km": [30, 300],
        "typical_payload_kg": [50, 600],
    },
    AircraftType.GLIDER: {
        "default_params": {
            "aspect_ratio": 20,
            "wing_sweep_deg": 0,
            "taper_ratio": 0.4,
            "airfoil_type": "Wortmann FX 67-K-170",
            "fuselage_fineness_ratio": 12,
        },
        "typical_range_km": [50, 1000],
        "typical_payload_kg": [50, 200],
    },
    AircraftType.UAV: {
        "default_params": {
            "aspect_ratio": 10,
            "wing_sweep_deg": 5,
            "taper_ratio": 0.6,
            "airfoil_type": "NACA 2412",
            "fuselage_fineness_ratio": 6,
        },
        "typical_range_km": [10, 500],
        "typical_payload_kg": [1, 50],
    },
}


class AircraftTypeConfig:
    def recommend(self, params: dict[str, Any]) -> dict[str, Any]:
        power_type = params.get("power_type", "")
        cruise_speed = params.get("cruise_speed_kmh", 0)
        payload = params.get("payload_kg", 0)
        vtol = params.get("vtol", False)

        if power_type == "electric" and vtol:
            recommended = AircraftType.EVTOL
            reason = "电动+垂直起降需求 → 推荐eVTOL类型"
        elif cruise_speed <= 150 and payload <= 200:
            recommended = AircraftType.GLIDER
            reason = "低巡航速度+轻载荷 → 推荐滑翔机类型"
        elif payload <= 50 and not params.get("crew", True):
            recommended = AircraftType.UAV
            reason = "小型+无人 → 推荐无人机类型"
        else:
            recommended = AircraftType.FIXED_WING
            reason = "默认推荐固定翼类型"

        template = TYPE_TEMPLATES.get(recommended, TYPE_TEMPLATES[AircraftType.FIXED_WING])

        return {
            "recommended_type": recommended,
            "reason": reason,
            "template": template,
        }

    def get_template(self, aircraft_type: str) -> dict[str, Any]:
        return TYPE_TEMPLATES.get(aircraft_type, TYPE_TEMPLATES[AircraftType.FIXED_WING])