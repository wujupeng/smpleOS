from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AirframeStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATED = "validated"
    APPROVED = "approved"
    RELEASED = "released"


@dataclass
class FuselageParams:
    length_m: float = 0.0
    diameter_m: float = 0.0
    fineness_ratio: float = 0.0
    nose_cone_ratio: float = 0.0
    tail_cone_ratio: float = 0.0


@dataclass
class WingParams:
    span_m: float = 0.0
    aspect_ratio: float = 0.0
    area_m2: float = 0.0
    taper_ratio: float = 0.0
    sweep_angle_deg: float = 0.0
    root_chord_m: float = 0.0
    tip_chord_m: float = 0.0
    incidence_angle_deg: float = 0.0
    dihedral_angle_deg: float = 0.0


@dataclass
class TailParams:
    h_tail_area_m2: float = 0.0
    h_tail_arm_m: float = 0.0
    v_tail_area_m2: float = 0.0
    v_tail_arm_m: float = 0.0
    h_tail_volume_coeff: float = 0.0
    v_tail_volume_coeff: float = 0.0


@dataclass
class LandingGearParams:
    type_: str = "tricycle"
    main_gear_position: str = "wing"
    wheel_track_m: float = 0.0
    wheel_base_m: float = 0.0
    tire_diameter_m: float = 0.0


@dataclass
class AirframeModel:
    airframe_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_ref: str | None = None
    fuselage_params: FuselageParams = field(default_factory=FuselageParams)
    wing_params: WingParams = field(default_factory=WingParams)
    tail_params: TailParams = field(default_factory=TailParams)
    landing_gear_params: LandingGearParams = field(default_factory=LandingGearParams)
    geometry_data: dict[str, Any] | None = None
    status: AirframeStatus = AirframeStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    domain_events: list[dict[str, Any]] = field(default_factory=list)

    def mark_generated(self) -> None:
        self.status = AirframeStatus.GENERATED
        self.updated_at = datetime.utcnow()
        self.domain_events.append({
            "event_type": "airframe.generated",
            "airframe_id": self.airframe_id,
        })

    def clear_events(self) -> list[dict[str, Any]]:
        events = self.domain_events.copy()
        self.domain_events.clear()
        return events