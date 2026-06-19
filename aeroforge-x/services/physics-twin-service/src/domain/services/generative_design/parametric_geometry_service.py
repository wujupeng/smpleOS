"""AeroForge-X v5.0 ParametricGeometryService

Generates parametric 3D aircraft geometry via OpenVSP integration,
supports STEP/IGES/OpenVSP export and manufacturing constraint validation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DesignParameters:
    wing_span: float
    wing_area: float
    wing_aspect_ratio: float
    wing_sweep_angle: float
    wing_taper_ratio: float
    fuselage_length: float
    fuselage_diameter: float
    horizontal_tail_area: Optional[float] = None
    vertical_tail_area: Optional[float] = None
    engine_count: int = 2
    engine_thrust: float = 25000.0

    def to_dict(self) -> dict:
        return {
            "wing_span": self.wing_span,
            "wing_area": self.wing_area,
            "wing_aspect_ratio": self.wing_aspect_ratio,
            "wing_sweep_angle": self.wing_sweep_angle,
            "wing_taper_ratio": self.wing_taper_ratio,
            "fuselage_length": self.fuselage_length,
            "fuselage_diameter": self.fuselage_diameter,
            "horizontal_tail_area": self.horizontal_tail_area,
            "vertical_tail_area": self.vertical_tail_area,
            "engine_count": self.engine_count,
            "engine_thrust": self.engine_thrust,
        }


@dataclass(frozen=True)
class ManufacturingViolation:
    violation_type: str
    parameter: str
    current_value: float
    required_value: float
    message: str


@dataclass(frozen=True)
class ManufacturingCheckResult:
    passed: bool
    violations: list[ManufacturingViolation]
    nearest_feasible_geometry: Optional[str] = None


@dataclass
class AircraftGeometry:
    geometry_id: str
    parameters: DesignParameters
    topology_hash: str
    export_formats: list[str] = field(default_factory=lambda: ["STEP", "IGES", "OpenVSP"])
    minio_ref: str = ""
    manufacturing_check: Optional[ManufacturingCheckResult] = None
    requirement_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "geometry_id": self.geometry_id,
            "topology_hash": self.topology_hash,
            "export_formats": self.export_formats,
            "minio_ref": self.minio_ref,
            "parameters": self.parameters.to_dict(),
        }


_MIN_FEATURE_SIZE_MM = 0.5
_MIN_DRAFT_ANGLE_DEG = 1.0
_MIN_WALL_THICKNESS_MM = 1.0


class ParametricGeometryService:

    def __init__(self, openvsp_endpoint: str = "http://openvsp:5000") -> None:
        self._openvsp_endpoint = openvsp_endpoint
        self._geometries: dict[str, AircraftGeometry] = {}

    def generate_geometry(
        self,
        parameters: DesignParameters,
        requirement_id: Optional[str] = None,
    ) -> AircraftGeometry:
        topology_hash = self._compute_topology_hash(parameters)
        geometry_id = f"GEO-{uuid.uuid4().hex[:8].upper()}"

        minio_ref = f"aeroforge/geometries/{geometry_id}"

        geometry = AircraftGeometry(
            geometry_id=geometry_id,
            parameters=parameters,
            topology_hash=topology_hash,
            minio_ref=minio_ref,
            requirement_id=requirement_id,
        )

        mfg_check = self.validate_manufacturing_constraints(geometry)
        geometry.manufacturing_check = mfg_check

        self._geometries[geometry_id] = geometry
        return geometry

    def regenerate_geometry(
        self,
        geometry_id: str,
        parameters: DesignParameters,
    ) -> AircraftGeometry:
        existing = self._geometries.get(geometry_id)
        if existing is None:
            raise ValueError(f"Geometry {geometry_id} not found")

        new_hash = self._compute_topology_hash(parameters)

        geometry = AircraftGeometry(
            geometry_id=geometry_id,
            parameters=parameters,
            topology_hash=new_hash,
            export_formats=existing.export_formats,
            minio_ref=f"aeroforge/geometries/{geometry_id}",
            requirement_id=existing.requirement_id,
        )

        mfg_check = self.validate_manufacturing_constraints(geometry)
        geometry.manufacturing_check = mfg_check

        self._geometries[geometry_id] = geometry
        return geometry

    def export_geometry(self, geometry_id: str, format: str) -> str:
        geometry = self._geometries.get(geometry_id)
        if geometry is None:
            raise ValueError(f"Geometry {geometry_id} not found")

        fmt = format.upper()
        if fmt not in geometry.export_formats:
            raise ValueError(f"Format {format} not available for geometry {geometry_id}")

        return f"{geometry.minio_ref}/model.{fmt.lower()}"

    def validate_manufacturing_constraints(
        self, geometry: AircraftGeometry
    ) -> ManufacturingCheckResult:
        violations: list[ManufacturingViolation] = []
        params = geometry.parameters

        wing_thickness_root = (params.wing_area / params.wing_span) * params.wing_taper_ratio * 0.12 * 1000
        if wing_thickness_root < _MIN_WALL_THICKNESS_MM:
            violations.append(ManufacturingViolation(
                violation_type="MinWallThickness",
                parameter="wing_root_thickness",
                current_value=wing_thickness_root,
                required_value=_MIN_WALL_THICKNESS_MM,
                message=f"Wing root thickness {wing_thickness_root:.2f}mm below minimum {_MIN_WALL_THICKNESS_MM}mm",
            ))

        if params.wing_sweep_angle > 0 and params.wing_sweep_angle < _MIN_DRAFT_ANGLE_DEG:
            violations.append(ManufacturingViolation(
                violation_type="MinDraftAngle",
                parameter="wing_sweep_angle",
                current_value=params.wing_sweep_angle,
                required_value=_MIN_DRAFT_ANGLE_DEG,
                message=f"Wing sweep angle insufficient for draft requirements",
            ))

        skin_thickness = (params.fuselage_diameter / 200.0) * 1000
        if skin_thickness < _MIN_FEATURE_SIZE_MM:
            violations.append(ManufacturingViolation(
                violation_type="MinFeatureSize",
                parameter="fuselage_skin_thickness",
                current_value=skin_thickness,
                required_value=_MIN_FEATURE_SIZE_MM,
                message=f"Fuselage skin thickness {skin_thickness:.3f}mm below minimum {_MIN_FEATURE_SIZE_MM}mm",
            ))

        nearest_feasible = None
        if violations:
            nearest_feasible = self._find_nearest_feasible(params)

        return ManufacturingCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            nearest_feasible_geometry=nearest_feasible,
        )

    def get_geometry(self, geometry_id: str) -> Optional[AircraftGeometry]:
        return self._geometries.get(geometry_id)

    def _compute_topology_hash(self, parameters: DesignParameters) -> str:
        param_str = json.dumps(parameters.to_dict(), sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()

    def _find_nearest_feasible(self, params: DesignParameters) -> Optional[str]:
        adjusted = DesignParameters(
            wing_span=params.wing_span,
            wing_area=max(params.wing_area, params.wing_span * _MIN_WALL_THICKNESS_MM / 0.12 / 1000 / params.wing_taper_ratio) if params.wing_taper_ratio > 0 else params.wing_area,
            wing_aspect_ratio=params.wing_aspect_ratio,
            wing_sweep_angle=max(params.wing_sweep_angle, _MIN_DRAFT_ANGLE_DEG),
            wing_taper_ratio=params.wing_taper_ratio,
            fuselage_length=params.fuselage_length,
            fuselage_diameter=params.fuselage_diameter,
            horizontal_tail_area=params.horizontal_tail_area,
            vertical_tail_area=params.vertical_tail_area,
            engine_count=params.engine_count,
            engine_thrust=params.engine_thrust,
        )
        nearest = self.generate_geometry(adjusted)
        return nearest.geometry_id