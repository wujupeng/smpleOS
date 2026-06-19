from __future__ import annotations

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase
from src.domain.schemas.enums import EngineType


class TurbofanParams(AircraftSchemaBase):
    bypass_ratio: float = Field(gt=0, description="Bypass ratio (>=1 for turbofan)")
    fan_pressure_ratio: float = Field(gt=1, description="Fan pressure ratio")
    sfc: float = Field(gt=0, description="Specific fuel consumption in kg/(N·h)")

    @model_validator(mode="after")
    def validate_turbofan(self) -> TurbofanParams:
        if self.bypass_ratio < 1:
            raise ValueError("Turbofan bypass_ratio must be >= 1")
        return self


class TurbopropParams(AircraftSchemaBase):
    propeller_efficiency: float = Field(gt=0, le=1.0, description="Propeller efficiency")
    shaft_power: float = Field(gt=0, description="Shaft power in kW")
    sfc: float = Field(gt=0, description="Specific fuel consumption in kg/(kW·h)")


class ElectricParams(AircraftSchemaBase):
    motor_kv: float = Field(gt=0, description="Motor KV rating in RPM/V")
    battery_capacity: float = Field(gt=0, description="Battery capacity in Ah")
    battery_voltage: float = Field(gt=0, description="Nominal battery voltage in V")
    max_current: float = Field(gt=0, description="Maximum continuous current in A")


class HybridParams(AircraftSchemaBase):
    thermal_power: float = Field(gt=0, description="Thermal engine power in kW")
    electric_power: float = Field(gt=0, description="Electric motor power in kW")
    battery_capacity: float = Field(gt=0, description="Battery capacity in Ah")
    battery_voltage: float = Field(gt=0, description="Nominal battery voltage in V")


class AircraftPropulsion(AircraftSchemaBase):
    engine_type: EngineType = Field(description="Type of propulsion engine")
    max_thrust: float = Field(gt=0, description="Maximum thrust in N")
    type_specific_params: TurbofanParams | TurbopropParams | ElectricParams | HybridParams | None = Field(
        default=None, description="Engine-type-specific parameters"
    )
    structure_ref: str | None = Field(default=None, description="Reference to AircraftStructure schema instance ID")
    geometry_ref: str | None = Field(default=None, description="Reference to AircraftGeometry schema instance ID")

    @model_validator(mode="after")
    def validate_engine_type_params(self) -> AircraftPropulsion:
        if self.engine_type == EngineType.Turbofan:
            if self.type_specific_params is None or not isinstance(self.type_specific_params, TurbofanParams):
                raise ValueError("Turbofan engine requires TurbofanParams")
        elif self.engine_type == EngineType.Turboprop:
            if self.type_specific_params is None or not isinstance(self.type_specific_params, TurbopropParams):
                raise ValueError("Turboprop engine requires TurbopropParams")
        elif self.engine_type == EngineType.Electric:
            if self.type_specific_params is None or not isinstance(self.type_specific_params, ElectricParams):
                raise ValueError("Electric engine requires ElectricParams")
        elif self.engine_type == EngineType.Hybrid:
            if self.type_specific_params is None or not isinstance(self.type_specific_params, HybridParams):
                raise ValueError("Hybrid engine requires HybridParams")
        return self

    @model_validator(mode="after")
    def validate_physical_constraints(self) -> AircraftPropulsion:
        if self.type_specific_params is not None and hasattr(self.type_specific_params, "sfc"):
            if self.type_specific_params.sfc <= 0:
                raise ValueError("SFC must be positive")
        return self