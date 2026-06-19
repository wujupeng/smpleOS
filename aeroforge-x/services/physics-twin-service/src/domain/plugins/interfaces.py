from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import FidelityLevel


class DOF6State(BaseModel):
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="x,y,z position in meters")
    velocity: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="u,v,w velocity in m/s")
    attitude: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="phi,theta,psi in radians")
    angular_rates: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="p,q,r in rad/s")
    acceleration: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="ax,ay,az in m/s²")


class BatteryState(BaseModel):
    soc: float = Field(default=1.0, ge=0, le=1, description="State of charge (0-1)")
    soh: float = Field(default=1.0, ge=0, le=1, description="State of health (0-1)")
    terminal_voltage: float = Field(default=0.0, description="Terminal voltage in V")
    current: float = Field(default=0.0, description="Current in A (positive=discharge)")
    temperature: float = Field(default=25.0, description="Cell temperature in °C")
    v_rc1: float = Field(default=0.0, description="RC1 branch voltage in V")
    v_rc2: float = Field(default=0.0, description="RC2 branch voltage in V")


class ControlState(BaseModel):
    elevator_cmd: float = Field(default=0.0, description="Elevator command in degrees")
    aileron_cmd: float = Field(default=0.0, description="Aileron command in degrees")
    rudder_cmd: float = Field(default=0.0, description="Rudder command in degrees")
    throttle_cmd: float = Field(default=0.0, ge=0, le=1, description="Throttle command (0-1)")
    autopilot_mode: str = Field(default="OFF", description="Autopilot mode")


class DOF6Output(BaseModel):
    state: DOF6State
    forces: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    moments: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    fidelity: str = "Low"


class BatteryOutput(BaseModel):
    state: BatteryState
    power: float = Field(default=0.0, description="Instantaneous power in W")
    energy_consumed: float = Field(default=0.0, description="Cumulative energy consumed in Wh")
    fidelity: str = "Low"


class ControlOutput(BaseModel):
    state: ControlState
    tracking_error: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    fidelity: str = "Low"


class StabilityCheck(BaseModel):
    is_stable: bool = True
    divergence_step: int | None = None
    residual: float = 0.0
    message: str = ""


class IPhysicsModelPlugin(ABC):

    @abstractmethod
    def initialize(self, params: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def get_supported_fidelities(self) -> list[str]:
        pass

    @abstractmethod
    def get_schema_references(self) -> list[str]:
        pass

    def validate_numerical_stability(self) -> StabilityCheck:
        return StabilityCheck(is_stable=True, message="No stability check implemented")