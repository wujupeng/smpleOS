from __future__ import annotations

import json
import math
from typing import Any

from ..value_objects import AircraftType


class FuselageGenerator:
    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        length_m = params.get("fuselage_length_m", 8.0)
        diameter_m = params.get("fuselage_diameter_m", 1.2)
        fineness_ratio = params.get("fineness_ratio", length_m / max(diameter_m, 0.1))
        nose_cone_ratio = params.get("nose_cone_ratio", 0.3)
        tail_cone_ratio = params.get("tail_cone_ratio", 0.25)

        return {
            "type": "fuselage",
            "parameters": {
                "length_m": round(length_m, 3),
                "diameter_m": round(diameter_m, 3),
                "fineness_ratio": round(fineness_ratio, 2),
                "nose_cone_ratio": round(nose_cone_ratio, 2),
                "tail_cone_ratio": round(tail_cone_ratio, 2),
            },
            "geometry": {
                "nose_length_m": round(length_m * nose_cone_ratio, 3),
                "cylinder_length_m": round(length_m * (1 - nose_cone_ratio - tail_cone_ratio), 3),
                "tail_length_m": round(length_m * tail_cone_ratio, 3),
            },
        }


class WingGenerator:
    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        wingspan_m = params.get("wingspan_m", 15.0)
        aspect_ratio = params.get("aspect_ratio", 12.0)
        wing_area_m2 = (wingspan_m ** 2) / aspect_ratio
        taper_ratio = params.get("taper_ratio", 0.5)
        sweep_deg = params.get("wing_sweep_deg", 3.0)
        root_chord_m = 2 * wing_area_m2 / (wingspan_m * (1 + taper_ratio))
        tip_chord_m = root_chord_m * taper_ratio

        return {
            "type": "wing",
            "parameters": {
                "wingspan_m": round(wingspan_m, 3),
                "aspect_ratio": round(aspect_ratio, 2),
                "wing_area_m2": round(wing_area_m2, 3),
                "taper_ratio": round(taper_ratio, 2),
                "sweep_deg": round(sweep_deg, 2),
                "root_chord_m": round(root_chord_m, 3),
                "tip_chord_m": round(tip_chord_m, 3),
            },
            "geometry": {
                "dihedral_deg": 3.0,
                "incidence_deg": 2.0,
                "airfoil_root": params.get("airfoil_type", "NACA 4415"),
                "airfoil_tip": params.get("airfoil_type", "NACA 4415"),
            },
        }


class TailGenerator:
    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        wing_area_m2 = params.get("wing_area_m2", 20.0)
        fuselage_length_m = params.get("fuselage_length_m", 8.0)
        wingspan_m = params.get("wingspan_m", 15.0)

        h_tail_volume = params.get("h_tail_volume_coeff", 0.5)
        v_tail_volume = params.get("v_tail_volume_coeff", 0.04)

        h_tail_arm = fuselage_length_m * 0.45
        v_tail_arm = fuselage_length_m * 0.45

        h_tail_area = h_tail_volume * wing_area_m2 * (wingspan_m / h_tail_arm) if h_tail_arm > 0 else 2.0
        v_tail_area = v_tail_volume * wing_area_m2 * (wingspan_m / v_tail_arm) if v_tail_arm > 0 else 1.5

        return {
            "type": "tail",
            "parameters": {
                "h_tail_area_m2": round(h_tail_area, 3),
                "v_tail_area_m2": round(v_tail_area, 3),
                "h_tail_arm_m": round(h_tail_arm, 3),
                "v_tail_arm_m": round(v_tail_arm, 3),
            },
            "geometry": {
                "h_tail_aspect_ratio": 4.0,
                "v_tail_aspect_ratio": 2.0,
                "h_tail_sweep_deg": 5.0,
                "v_tail_sweep_deg": 15.0,
            },
        }


class AssemblyEngine:
    def assemble(self, fuselage: dict, wing: dict, tail: dict) -> dict[str, Any]:
        return {
            "type": "aircraft_assembly",
            "components": {
                "fuselage": fuselage,
                "wing": wing,
                "tail": tail,
            },
            "assembly_offsets": {
                "wing": {"x": 0.0, "y": 0.0, "z": 0.3},
                "h_tail": {"x": fuselage["parameters"]["length_m"] * 0.7, "y": 0.0, "z": 0.2},
                "v_tail": {"x": fuselage["parameters"]["length_m"] * 0.7, "y": 0.0, "z": 0.5},
            },
        }


class ParametricModelGenerator:
    def __init__(self) -> None:
        self._fuselage_gen = FuselageGenerator()
        self._wing_gen = WingGenerator()
        self._tail_gen = TailGenerator()
        self._assembly_engine = AssemblyEngine()

    def generate(self, spec_params: dict[str, Any]) -> dict[str, Any]:
        payload_kg = spec_params.get("payload_kg", 120)
        range_km = spec_params.get("range_km", 200)
        cruise_speed = spec_params.get("cruise_speed_kmh", 120)

        mtow_estimate = payload_kg * 2.5
        wing_loading = mtow_estimate * 9.81 / 100.0
        wing_area = mtow_estimate * 9.81 / (wing_loading * 9.81) if wing_loading > 0 else 20.0

        fuselage_length = max(4.0, mtow_estimate / 200.0 * 6)
        fuselage_diameter = max(0.8, mtow_estimate / 500.0 * 1.5)

        template = spec_params.get("template", {})
        default_params = template.get("default_params", {})

        aspect_ratio = default_params.get("aspect_ratio", 12)
        wingspan = math.sqrt(wing_area * aspect_ratio)

        fuselage_params = {
            "fuselage_length_m": fuselage_length,
            "fuselage_diameter_m": fuselage_diameter,
            "fineness_ratio": fuselage_length / max(fuselage_diameter, 0.1),
            **default_params,
        }

        wing_params = {
            "wingspan_m": wingspan,
            "aspect_ratio": aspect_ratio,
            "wing_area_m2": wing_area,
            "taper_ratio": default_params.get("taper_ratio", 0.5),
            "wing_sweep_deg": default_params.get("wing_sweep_deg", 3.0),
            "airfoil_type": default_params.get("airfoil_type", "NACA 4415"),
        }

        tail_params = {
            "wing_area_m2": wing_area,
            "fuselage_length_m": fuselage_length,
            "wingspan_m": wingspan,
        }

        fuselage = self._fuselage_gen.generate(fuselage_params)
        wing = self._wing_gen.generate(wing_params)
        tail = self._tail_gen.generate(tail_params)
        assembly = self._assembly_engine.assemble(fuselage, wing, tail)

        return {
            "model_type": spec_params.get("aircraft_type", "fixed_wing"),
            "mtow_estimate_kg": round(mtow_estimate, 1),
            "wing_area_m2": round(wing_area, 3),
            "wingspan_m": round(wingspan, 3),
            "fuselage_length_m": round(fuselage_length, 3),
            "assembly": assembly,
        }