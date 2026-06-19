from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase


class WingSubSchema(AircraftSchemaBase):
    naca_number: str | None = Field(default=None, description="NACA airfoil designation")
    twist_angle: float = Field(default=0.0, ge=-10.0, le=10.0, description="Wing twist angle in degrees")
    control_surface_type: str | None = Field(default=None, description="Control surface type: aileron/flap/spoiler")


class FuselageSubSchema(AircraftSchemaBase):
    length: float = Field(gt=0, description="Fuselage length in meters")
    diameter: float = Field(gt=0, description="Fuselage maximum diameter in meters")
    fineness_ratio: float = Field(default=0.0, ge=0, description="Length/diameter ratio")

    @model_validator(mode="after")
    def compute_fineness_ratio(self) -> FuselageSubSchema:
        if self.fineness_ratio == 0 and self.diameter > 0:
            self.fineness_ratio = round(self.length / self.diameter, 4)
        return self


class TailSubSchema(AircraftSchemaBase):
    tail_type: str = Field(default="conventional", description="Tail type: conventional/T-tail/V-tail/canard")
    tail_area: float = Field(gt=0, description="Horizontal tail area in m²")
    tail_arm: float = Field(gt=0, description="Tail moment arm in meters")


class NacelleSubSchema(AircraftSchemaBase):
    nacelle_length: float = Field(gt=0, description="Nacelle length in meters")
    nacelle_diameter: float = Field(gt=0, description="Nacelle maximum diameter in meters")


class AircraftGeometry(AircraftSchemaBase):
    wingspan: float = Field(gt=0, description="Wing span tip-to-tip in meters")
    chord_length: float = Field(gt=0, description="Mean aerodynamic chord in meters")
    sweep_angle: float = Field(ge=-45.0, le=75.0, description="Quarter-chord sweep angle in degrees")
    taper_ratio: float = Field(gt=0, le=1.0, description="Tip chord / root chord ratio")
    thickness_ratio: float = Field(gt=0, le=0.5, description="Max thickness / chord ratio")
    wing_area: float = Field(gt=0, description="Reference wing planform area in m²")
    dihedral_angle: float = Field(default=0.0, ge=-15.0, le=15.0, description="Wing dihedral angle in degrees")
    incidence_angle: float = Field(default=0.0, ge=-10.0, le=10.0, description="Wing incidence angle in degrees")
    wing_sub_schema: WingSubSchema | None = Field(default=None, description="Wing detailed parameters")
    fuselage_sub_schema: FuselageSubSchema | None = Field(default=None, description="Fuselage parameters")
    tail_sub_schema: TailSubSchema | None = Field(default=None, description="Tail parameters")
    nacelle_sub_schema: NacelleSubSchema | None = Field(default=None, description="Nacelle parameters")

    aspect_ratio: float = Field(default=0.0, ge=0, description="Wingspan²/wing_area (derived)")

    @model_validator(mode="after")
    def compute_derived_params(self) -> AircraftGeometry:
        if self.aspect_ratio == 0 and self.wing_area > 0:
            self.aspect_ratio = round(self.wingspan ** 2 / self.wing_area, 4)
        return self

    @model_validator(mode="after")
    def validate_ordering_constraints(self) -> AircraftGeometry:
        if self.chord_length > self.wingspan:
            raise ValueError("chord_length cannot exceed wingspan")
        if self.taper_ratio > 1.0:
            raise ValueError("taper_ratio cannot exceed 1.0 (tip chord ≤ root chord)")
        return self