from __future__ import annotations

from pydantic import Field, model_validator

from src.domain.schemas.base import AircraftSchemaBase
from src.domain.schemas.enums import ControlLawType


class FlightControlParams(AircraftSchemaBase):
    control_law_type: ControlLawType = Field(default=ControlLawType.PID, description="Control law type")
    elevator_limit: float = Field(gt=0, le=30.0, description="Elevator deflection limit in degrees")
    aileron_limit: float = Field(gt=0, le=30.0, description="Aileron deflection limit in degrees")
    rudder_limit: float = Field(gt=0, le=30.0, description="Rudder deflection limit in degrees")
    sas_pitch_gain: float = Field(default=0.0, ge=0, description="SAS pitch damping gain")
    sas_roll_gain: float = Field(default=0.0, ge=0, description="SAS roll damping gain")
    sas_yaw_gain: float = Field(default=0.0, ge=0, description="SAS yaw damping gain")

    @model_validator(mode="after")
    def validate_control_limits(self) -> FlightControlParams:
        if self.elevator_limit > 25:
            import warnings
            warnings.warn("Elevator limit exceeds typical 25° range", stacklevel=2)
        if self.aileron_limit > 25:
            import warnings
            warnings.warn("Aileron limit exceeds typical 25° range", stacklevel=2)
        return self


class NavigationParams(AircraftSchemaBase):
    gps_accuracy: float = Field(gt=0, description="GPS position accuracy in meters")
    imu_drift: float = Field(gt=0, description="IMU drift rate in °/hour")


class CommunicationParams(AircraftSchemaBase):
    comm_frequency: float = Field(gt=0, description="Communication frequency in MHz")
    comm_power: float = Field(gt=0, description="Communication transmit power in W")


class AircraftAvionics(AircraftSchemaBase):
    flight_control: FlightControlParams = Field(description="Flight control parameters")
    navigation: NavigationParams | None = Field(default=None, description="Navigation parameters")
    communication: CommunicationParams | None = Field(default=None, description="Communication parameters")
    propulsion_ref: str | None = Field(default=None, description="Reference to AircraftPropulsion schema instance ID")
    envelope_ref: str | None = Field(default=None, description="Reference to AircraftFlightEnvelope schema instance ID")

    certification_warnings: list[str] = Field(default_factory=list, description="Certification compliance warnings")

    @model_validator(mode="after")
    def check_certification_compliance(self) -> AircraftAvionics:
        warnings_list = []
        fc = self.flight_control
        if fc.elevator_limit > 25:
            warnings_list.append(f"Elevator limit {fc.elevator_limit}° exceeds FAR-25 typical range")
        if fc.aileron_limit > 25:
            warnings_list.append(f"Aileron limit {fc.aileron_limit}° exceeds FAR-25 typical range")
        if fc.rudder_limit > 25:
            warnings_list.append(f"Rudder limit {fc.rudder_limit}° exceeds FAR-25 typical range")
        self.certification_warnings = warnings_list
        return self