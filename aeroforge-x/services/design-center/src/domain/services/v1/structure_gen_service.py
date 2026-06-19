from __future__ import annotations

import math
from typing import Any

from src.domain.entities.v1.structure_model import StructureModel, StructureComponentType, StructureStatus


class StructureGenService:
    def generate_structure(self, airframe_params: dict[str, Any]) -> list[StructureModel]:
        structures: list[StructureModel] = []
        wing_span = float(airframe_params.get("wing_span_m", 2.0))
        root_chord = float(airframe_params.get("root_chord_m", 0.3))
        fuselage_length = float(airframe_params.get("fuselage_length_m", 1.5))

        spar = self._generate_spar(wing_span, root_chord)
        structures.append(spar)

        rib_count = max(3, int(wing_span / 0.3))
        rib_positions = [round(i * wing_span / (rib_count + 1), 3) for i in range(1, rib_count + 1)]
        for i, pos in enumerate(rib_positions):
            rib = self._generate_rib(pos, root_chord * (1 - pos / wing_span * 0.5), i + 1)
            structures.append(rib)

        frame_count = max(2, int(fuselage_length / 0.4))
        for i in range(frame_count):
            frame = self._generate_frame(i + 1, fuselage_length / (frame_count + 1) * (i + 1))
            structures.append(frame)

        for s in structures:
            s.mark_generated()
        return structures

    def _generate_spar(self, wing_span: float, root_chord: float) -> StructureModel:
        spar_height = root_chord * 0.12
        spar_thickness = root_chord * 0.02
        return StructureModel(
            component_type=StructureComponentType.SPAR,
            material="carbon_fiber_composite",
            geometry={
                "type": "I_beam",
                "length_m": round(wing_span * 0.95, 3),
                "height_m": round(spar_height, 4),
                "thickness_m": round(spar_thickness, 4),
                "position": "wing_main_spar",
                "bounding_box": {
                    "min_x": -wing_span * 0.475,
                    "max_x": wing_span * 0.475,
                    "min_y": -spar_height / 2,
                    "max_y": spar_height / 2,
                    "min_z": -spar_thickness / 2,
                    "max_z": spar_thickness / 2,
                },
            },
        )

    def _generate_rib(self, position_m: float, chord_m: float, index: int) -> StructureModel:
        rib_height = chord_m * 0.15
        return StructureModel(
            component_type=StructureComponentType.RIB,
            material="carbon_fiber_composite",
            geometry={
                "type": "airfoil_rib",
                "chord_m": round(chord_m, 4),
                "height_m": round(rib_height, 4),
                "position_m": round(position_m, 3),
                "thickness_m": 0.002,
                "index": index,
                "bounding_box": {
                    "min_x": position_m - 0.001,
                    "max_x": position_m + 0.001,
                    "min_y": -rib_height / 2,
                    "max_y": rib_height / 2,
                    "min_z": -chord_m / 2,
                    "max_z": chord_m / 2,
                },
            },
        )

    def _generate_frame(self, index: int, position_m: float) -> StructureModel:
        return StructureModel(
            component_type=StructureComponentType.FRAME,
            material="aluminum_6061_t6",
            geometry={
                "type": "circular_frame",
                "position_m": round(position_m, 3),
                "thickness_m": 0.002,
                "index": index,
                "bounding_box": {
                    "min_x": position_m - 0.001,
                    "max_x": position_m + 0.001,
                    "min_y": -0.1,
                    "max_y": 0.1,
                    "min_z": -0.1,
                    "max_z": 0.1,
                },
            },
        )