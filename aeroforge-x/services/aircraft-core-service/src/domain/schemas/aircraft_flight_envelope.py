from __future__ import annotations

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase


class AircraftFlightEnvelope(AircraftSchemaBase):
    V_s: float = Field(gt=0, description="Stall speed in m/s (KEAS)")
    V_A: float = Field(gt=0, description="Maneuvering speed in m/s")
    V_C: float = Field(gt=0, description="Design cruising speed in m/s")
    V_D: float = Field(gt=0, description="Design diving speed in m/s")
    h_max: float = Field(gt=0, description="Maximum operating altitude in meters")
    n_min: float = Field(default=-1.0, description="Minimum load factor (negative for pull-down)")
    n_max: float = Field(default=3.5, gt=0, description="Maximum positive load factor")
    CG_fwd: float = Field(description="Forward CG limit in meters from reference datum")
    CG_aft: float = Field(description="Aft CG limit in meters from reference datum")
    geometry_ref: str | None = Field(default=None, description="Reference to AircraftGeometry schema instance ID")
    propulsion_ref: str | None = Field(default=None, description="Reference to AircraftPropulsion schema instance ID")

    @model_validator(mode="after")
    def validate_speed_ordering(self) -> AircraftFlightEnvelope:
        if not (self.V_s < self.V_A <= self.V_C <= self.V_D):
            raise ValueError(f"Speed ordering violated: V_s({self.V_s}) < V_A({self.V_A}) <= V_C({self.V_C}) <= V_D({self.V_D})")
        return self

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> AircraftFlightEnvelope:
        if self.n_min >= self.n_max:
            raise ValueError(f"n_min({self.n_min}) must be less than n_max({self.n_max})")
        if self.V_A < self.V_s * 1.1:
            import warnings
            warnings.warn(f"V_A({self.V_A}) is close to V_s({self.V_s}), insufficient margin", stacklevel=2)
        return self

    @model_validator(mode="after")
    def validate_cg_range(self) -> AircraftFlightEnvelope:
        if self.CG_fwd >= self.CG_aft:
            raise ValueError(f"CG_fwd({self.CG_fwd}) must be less than CG_aft({self.CG_aft})")
        return self