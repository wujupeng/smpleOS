from __future__ import annotations

import math
from typing import Any

from src.domain.entities.v1.airframe_model import (
    AirframeModel,
    FuselageParams,
    WingParams,
    TailParams,
    LandingGearParams,
)


class AirframeGenService:
    def generate_airframe(self, spec_params: dict[str, Any]) -> AirframeModel:
        payload = float(spec_params.get("payload_kg", 10))
        mtow = payload * 2.5
        cruise_speed = float(spec_params.get("cruise_speed_kmh", 100))
        range_km = float(spec_params.get("range_km", 100))

        wing_loading = self._estimate_wing_loading(spec_params)
        wing_area = mtow / wing_loading
        aspect_ratio = float(spec_params.get("aspect_ratio", self._default_aspect_ratio(spec_params)))
        span = math.sqrt(wing_area * aspect_ratio)
        taper_ratio = float(spec_params.get("taper_ratio", 0.5))
        sweep_angle = float(spec_params.get("sweep_angle_deg", 2.0))
        root_chord = (2 * wing_area) / (span * (1 + taper_ratio))
        tip_chord = root_chord * taper_ratio

        fuselage_length = span * 0.7
        fuselage_diameter = fuselage_length / 8.0

        h_tail_volume = 0.5
        v_tail_volume = 0.04
        h_tail_arm = fuselage_length * 0.45
        v_tail_arm = fuselage_length * 0.45
        h_tail_area = h_tail_volume * wing_area * (root_chord / h_tail_arm)
        v_tail_area = v_tail_volume * wing_area * (span / v_tail_arm)

        airframe = AirframeModel(
            fuselage_params=FuselageParams(
                length_m=round(fuselage_length, 3),
                diameter_m=round(fuselage_diameter, 3),
                fineness_ratio=round(fuselage_length / fuselage_diameter, 2) if fuselage_diameter > 0 else 0,
                nose_cone_ratio=0.3,
                tail_cone_ratio=0.25,
            ),
            wing_params=WingParams(
                span_m=round(span, 3),
                aspect_ratio=round(aspect_ratio, 2),
                area_m2=round(wing_area, 4),
                taper_ratio=round(taper_ratio, 2),
                sweep_angle_deg=round(sweep_angle, 1),
                root_chord_m=round(root_chord, 4),
                tip_chord_m=round(tip_chord, 4),
                incidence_angle_deg=2.0,
                dihedral_angle_deg=3.0,
            ),
            tail_params=TailParams(
                h_tail_area_m2=round(h_tail_area, 4),
                h_tail_arm_m=round(h_tail_arm, 3),
                v_tail_area_m2=round(v_tail_area, 4),
                v_tail_arm_m=round(v_tail_arm, 3),
                h_tail_volume_coeff=h_tail_volume,
                v_tail_volume_coeff=v_tail_volume,
            ),
            landing_gear_params=LandingGearParams(
                type_="tricycle",
                main_gear_position="wing",
                wheel_track_m=round(span * 0.15, 3),
                wheel_base_m=round(fuselage_length * 0.3, 3),
                tire_diameter_m=0.2,
            ),
        )
        airframe.mark_generated()
        return airframe

    def _estimate_wing_loading(self, spec_params: dict[str, Any]) -> float:
        aircraft_type = spec_params.get("aircraft_type", "fixed_wing")
        if aircraft_type == "evtol":
            return 80.0
        elif aircraft_type == "glider":
            return 30.0
        elif aircraft_type == "uav":
            return 60.0
        return 150.0

    def _default_aspect_ratio(self, spec_params: dict[str, Any]) -> float:
        aircraft_type = spec_params.get("aircraft_type", "fixed_wing")
        if aircraft_type == "glider":
            return 20.0
        elif aircraft_type == "evtol":
            return 6.0
        elif aircraft_type == "uav":
            return 10.0
        return 8.0