from __future__ import annotations

import math
import time as _time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.domain.enums import FidelityLevel
from src.domain.plugins.interfaces import (
    ControlOutput,
    ControlState,
    IPhysicsModelPlugin,
    StabilityCheck,
)


class FlightMode(str, Enum):
    Takeoff = "Takeoff"
    Climb = "Climb"
    Cruise = "Cruise"
    Approach = "Approach"
    Landing = "Landing"
    GoAround = "GoAround"


class AutopilotSubMode(str, Enum):
    RotationAndClimb = "RotationAndClimb"
    AltitudeAndHeadingHold = "AltitudeAndHeadingHold"
    AltitudeAndSpeedHold = "AltitudeAndSpeedHold"
    ILSApproach = "ILSApproach"
    FlareAndRollout = "FlareAndRollout"
    ClimbAndHeadingHold = "ClimbAndHeadingHold"


LEGAL_TRANSITIONS: dict[FlightMode, list[FlightMode]] = {
    FlightMode.Takeoff: [FlightMode.Climb],
    FlightMode.Climb: [FlightMode.Cruise],
    FlightMode.Cruise: [FlightMode.Approach],
    FlightMode.Approach: [FlightMode.Landing, FlightMode.GoAround],
    FlightMode.Landing: [],
    FlightMode.GoAround: [FlightMode.Climb],
}

AUTOPILOT_MODE_MAP: dict[FlightMode, AutopilotSubMode] = {
    FlightMode.Takeoff: AutopilotSubMode.RotationAndClimb,
    FlightMode.Climb: AutopilotSubMode.AltitudeAndHeadingHold,
    FlightMode.Cruise: AutopilotSubMode.AltitudeAndSpeedHold,
    FlightMode.Approach: AutopilotSubMode.ILSApproach,
    FlightMode.Landing: AutopilotSubMode.FlareAndRollout,
    FlightMode.GoAround: AutopilotSubMode.ClimbAndHeadingHold,
}


@dataclass
class ControlLawParams:
    pid_kp: float = 1.0
    pid_ki: float = 0.1
    pid_kd: float = 0.01
    sas_pitch_gain: float = 1.0
    sas_roll_gain: float = 1.0
    sas_yaw_gain: float = 1.0
    autopilot_sub_mode: AutopilotSubMode = AutopilotSubMode.AltitudeAndSpeedHold


DEFAULT_CONTROL_LAWS: dict[FlightMode, ControlLawParams] = {
    FlightMode.Takeoff: ControlLawParams(pid_kp=2.0, pid_ki=0.2, pid_kd=0.05, sas_pitch_gain=1.5, sas_roll_gain=1.0, sas_yaw_gain=1.2, autopilot_sub_mode=AutopilotSubMode.RotationAndClimb),
    FlightMode.Climb: ControlLawParams(pid_kp=1.5, pid_ki=0.15, pid_kd=0.03, sas_pitch_gain=1.2, sas_roll_gain=1.0, sas_yaw_gain=1.0, autopilot_sub_mode=AutopilotSubMode.AltitudeAndHeadingHold),
    FlightMode.Cruise: ControlLawParams(pid_kp=1.0, pid_ki=0.1, pid_kd=0.01, sas_pitch_gain=1.0, sas_roll_gain=1.0, sas_yaw_gain=1.0, autopilot_sub_mode=AutopilotSubMode.AltitudeAndSpeedHold),
    FlightMode.Approach: ControlLawParams(pid_kp=1.8, pid_ki=0.18, pid_kd=0.04, sas_pitch_gain=1.3, sas_roll_gain=1.2, sas_yaw_gain=1.1, autopilot_sub_mode=AutopilotSubMode.ILSApproach),
    FlightMode.Landing: ControlLawParams(pid_kp=2.5, pid_ki=0.25, pid_kd=0.06, sas_pitch_gain=1.8, sas_roll_gain=1.5, sas_yaw_gain=1.3, autopilot_sub_mode=AutopilotSubMode.FlareAndRollout),
    FlightMode.GoAround: ControlLawParams(pid_kp=2.0, pid_ki=0.2, pid_kd=0.05, sas_pitch_gain=1.5, sas_roll_gain=1.2, sas_yaw_gain=1.2, autopilot_sub_mode=AutopilotSubMode.ClimbAndHeadingHold),
}


@dataclass
class ModeTransitionRecord:
    from_mode: FlightMode
    to_mode: FlightMode
    timestamp: float
    transition_type: str = "Normal"
    is_rejected: bool = False
    rejection_reason: str | None = None


@dataclass
class TransitionResult:
    success: bool
    from_mode: FlightMode
    to_mode: FlightMode
    message: str
    is_emergency: bool = False


@dataclass
class OverrideCommand:
    command_type: str = "none"
    target_value: float = 0.0
    message: str = ""


@dataclass
class ProtectionResult:
    is_within_envelope: bool
    violations: list[str] = field(default_factory=list)
    override: OverrideCommand | None = None


@dataclass
class FMMState:
    current_mode: FlightMode = FlightMode.Takeoff
    control_law: ControlLawParams = field(default_factory=lambda: DEFAULT_CONTROL_LAWS[FlightMode.Takeoff])
    is_blending: bool = False
    blend_progress: float = 0.0
    bms_status: str = "Normal"
    protection_active: bool = False


class FlightModeFSM:

    def __init__(self, initial_mode: FlightMode = FlightMode.Takeoff, emergency_override_enabled: bool = True):
        self.current_mode = initial_mode
        self.emergency_override_enabled = emergency_override_enabled
        self.mode_history: list[ModeTransitionRecord] = []

    def validate_transition(self, source: FlightMode, target: FlightMode) -> bool:
        if target == FlightMode.GoAround and self.emergency_override_enabled:
            return True
        legal_targets = LEGAL_TRANSITIONS.get(source, [])
        return target in legal_targets

    def check_flight_state(self, target_mode: FlightMode, altitude: float, airspeed: float, gear_down: bool = False) -> tuple[bool, str]:
        if target_mode == FlightMode.Climb:
            if altitude < 50:
                return False, f"Altitude {altitude:.0f}m below safe altitude (50m)"
            if airspeed < 30:
                return False, f"Airspeed {airspeed:.1f}m/s below V2 (30m/s)"
        elif target_mode == FlightMode.Cruise:
            if altitude < 500:
                return False, f"Altitude {altitude:.0f}m below cruise altitude (500m)"
        elif target_mode == FlightMode.Approach:
            if airspeed > 80:
                return False, f"Airspeed {airspeed:.1f}m/s above approach limit (80m/s)"
            if altitude > 3000:
                return False, f"Altitude {altitude:.0f}m above approach limit (3000m)"
        elif target_mode == FlightMode.Landing:
            if not gear_down:
                return False, "Landing gear not deployed"
            if airspeed > 70:
                return False, f"Airspeed {airspeed:.1f}m/s above landing limit (70m/s)"
        return True, ""

    def execute_transition(self, target: FlightMode, transition_type: str = "Normal") -> TransitionResult:
        source = self.current_mode

        if not self.validate_transition(source, target):
            record = ModeTransitionRecord(
                from_mode=source, to_mode=target,
                timestamp=_time.time(), transition_type=transition_type,
                is_rejected=True, rejection_reason=f"Illegal transition: {source.value}→{target.value}",
            )
            self.mode_history.append(record)
            return TransitionResult(
                success=False, from_mode=source, to_mode=target,
                message=f"Illegal transition: {source.value}→{target.value}",
            )

        self.current_mode = target
        record = ModeTransitionRecord(
            from_mode=source, to_mode=target,
            timestamp=_time.time(), transition_type=transition_type,
        )
        self.mode_history.append(record)

        return TransitionResult(
            success=True, from_mode=source, to_mode=target,
            message=f"Transition: {source.value}→{target.value}",
            is_emergency=transition_type == "Emergency",
        )

    def get_legal_transitions(self) -> list[tuple[FlightMode, FlightMode]]:
        result = []
        for source, targets in LEGAL_TRANSITIONS.items():
            for target in targets:
                result.append((source, target))
        if self.emergency_override_enabled:
            for mode in FlightMode:
                if mode != FlightMode.GoAround:
                    result.append((mode, FlightMode.GoAround))
        return result


class ControlLawScheduler:

    def __init__(self, schedule_table: dict[FlightMode, ControlLawParams] | None = None):
        self.schedule_table = schedule_table or dict(DEFAULT_CONTROL_LAWS)
        self.gain_scheduling_tables: dict[FlightMode, dict[str, list[tuple[float, float]]]] = {}

    def get_params(self, mode: FlightMode) -> ControlLawParams:
        return self.schedule_table.get(mode, ControlLawParams())

    def get_scheduled_params(self, mode: FlightMode, flight_condition: dict[str, float]) -> ControlLawParams:
        base_params = self.get_params(mode)
        schedule = self.gain_scheduling_tables.get(mode)
        if schedule is None:
            return base_params

        airspeed = flight_condition.get("airspeed", 50.0)
        altitude = flight_condition.get("altitude", 1000.0)

        result = ControlLawParams(
            pid_kp=base_params.pid_kp,
            pid_ki=base_params.pid_ki,
            pid_kd=base_params.pid_kd,
            sas_pitch_gain=base_params.sas_pitch_gain,
            sas_roll_gain=base_params.sas_roll_gain,
            sas_yaw_gain=base_params.sas_yaw_gain,
            autopilot_sub_mode=base_params.autopilot_sub_mode,
        )

        if "pid_kp" in schedule:
            result.pid_kp = self._interpolate_schedule(schedule["pid_kp"], airspeed)
        if "sas_pitch_gain" in schedule:
            result.sas_pitch_gain = self._interpolate_schedule(schedule["sas_pitch_gain"], airspeed)

        return result

    def get_autopilot_mode(self, mode: FlightMode) -> AutopilotSubMode:
        return AUTOPILOT_MODE_MAP.get(mode, AutopilotSubMode.AltitudeAndSpeedHold)

    @staticmethod
    def _interpolate_schedule(table: list[tuple[float, float]], x: float) -> float:
        if not table:
            return 0.0
        sorted_table = sorted(table, key=lambda t: t[0])
        if x <= sorted_table[0][0]:
            return sorted_table[0][1]
        if x >= sorted_table[-1][0]:
            return sorted_table[-1][1]
        for i in range(len(sorted_table) - 1):
            x0, y0 = sorted_table[i]
            x1, y1 = sorted_table[i + 1]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0) if x1 != x0 else 0
                return y0 + t * (y1 - y0)
        return sorted_table[-1][1]


class ParameterBlender:

    def __init__(self, blending_time: float = 5.0):
        self.blending_time = blending_time
        self.is_blending = False
        self.blend_progress = 0.0
        self.source_params: ControlLawParams | None = None
        self.target_params: ControlLawParams | None = None
        self._elapsed = 0.0

    def start_blending(self, source: ControlLawParams, target: ControlLawParams) -> None:
        self.source_params = source
        self.target_params = target
        self.is_blending = True
        self.blend_progress = 0.0
        self._elapsed = 0.0

    def step(self, dt: float) -> ControlLawParams:
        if not self.is_blending or self.source_params is None or self.target_params is None:
            return self.target_params or ControlLawParams()

        self._elapsed += dt
        self.blend_progress = min(self._elapsed / self.blending_time, 1.0)
        alpha = self.blend_progress

        blended = ControlLawParams(
            pid_kp=(1 - alpha) * self.source_params.pid_kp + alpha * self.target_params.pid_kp,
            pid_ki=(1 - alpha) * self.source_params.pid_ki + alpha * self.target_params.pid_ki,
            pid_kd=(1 - alpha) * self.source_params.pid_kd + alpha * self.target_params.pid_kd,
            sas_pitch_gain=(1 - alpha) * self.source_params.sas_pitch_gain + alpha * self.target_params.sas_pitch_gain,
            sas_roll_gain=(1 - alpha) * self.source_params.sas_roll_gain + alpha * self.target_params.sas_roll_gain,
            sas_yaw_gain=(1 - alpha) * self.source_params.sas_yaw_gain + alpha * self.target_params.sas_yaw_gain,
            autopilot_sub_mode=self.target_params.autopilot_sub_mode if alpha >= 0.5 else self.source_params.autopilot_sub_mode,
        )

        if self.blend_progress >= 1.0:
            self.is_blending = False

        return blended

    def is_complete(self) -> bool:
        return not self.is_blending

    def abort_blending(self) -> None:
        self.is_blending = False
        self.blend_progress = 1.0


class EnvelopeProtector:

    def __init__(
        self,
        v_d: float = 100.0,
        n_min: float = -1.5,
        n_max: float = 3.5,
        h_max: float = 15000.0,
    ):
        self.v_d = v_d
        self.n_min = n_min
        self.n_max = n_max
        self.h_max = h_max
        self.protection_active = False
        self.override_command: OverrideCommand | None = None

    def check_envelope(self, airspeed: float, load_factor: float, altitude: float) -> ProtectionResult:
        violations: list[str] = []

        if airspeed > self.v_d:
            violations.append(f"Overspeed: V={airspeed:.1f}m/s > V_D={self.v_d}m/s")

        if load_factor < self.n_min:
            violations.append(f"Underload: n={load_factor:.2f} < n_min={self.n_min}")

        if load_factor > self.n_max:
            violations.append(f"Overload: n={load_factor:.2f} > n_max={self.n_max}")

        if altitude > self.h_max:
            violations.append(f"Over-altitude: h={altitude:.0f}m > h_max={self.h_max}m")

        self.protection_active = len(violations) > 0
        override = self.compute_override(airspeed, load_factor, altitude) if violations else None

        return ProtectionResult(
            is_within_envelope=len(violations) == 0,
            violations=violations,
            override=override,
        )

    def compute_override(self, airspeed: float, load_factor: float, altitude: float) -> OverrideCommand:
        if airspeed > self.v_d:
            return OverrideCommand(command_type="speed_limit", target_value=self.v_d * 0.95, message="Reduce speed to V_D limit")
        if load_factor > self.n_max:
            return OverrideCommand(command_type="load_limit", target_value=self.n_max * 0.95, message="Reduce load factor")
        if load_factor < self.n_min:
            return OverrideCommand(command_type="load_limit", target_value=self.n_min * 0.95, message="Increase load factor")
        if altitude > self.h_max:
            return OverrideCommand(command_type="altitude_limit", target_value=self.h_max * 0.98, message="Descend to max altitude")
        return OverrideCommand()


class FlightModeManager(IPhysicsModelPlugin):

    def __init__(self, fidelity: str = "Low"):
        self.fidelity = fidelity
        self.fmm_id: str = ""
        self.fsm = FlightModeFSM()
        self.scheduler = ControlLawScheduler()
        self.blender = ParameterBlender()
        self.protector = EnvelopeProtector()
        self._state = ControlState()
        self._fmm_state = FMMState()
        self._time = 0.0
        self._params: dict[str, Any] = {}

    def initialize(self, params: dict[str, Any]) -> None:
        self._params = params
        self.fmm_id = params.get("fmm_id", "FMM-001")
        self.fidelity = params.get("fidelity", self.fidelity)

        self.fsm = FlightModeFSM(
            initial_mode=FlightMode(params.get("initial_mode", "Takeoff")),
            emergency_override_enabled=params.get("emergency_override_enabled", True),
        )

        self.blender = ParameterBlender(
            blending_time=params.get("blending_time", 5.0),
        )

        self.protector = EnvelopeProtector(
            v_d=params.get("v_d", 100.0),
            n_min=params.get("n_min", -1.5),
            n_max=params.get("n_max", 3.5),
            h_max=params.get("h_max", 15000.0),
        )

        self._fmm_state = FMMState(
            current_mode=self.fsm.current_mode,
            control_law=self.scheduler.get_params(self.fsm.current_mode),
        )

        self._state = ControlState(
            autopilot_mode=self.scheduler.get_autopilot_mode(self.fsm.current_mode).value,
        )
        self._time = 0.0

    def step(self, dt: float, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        inputs = inputs or {}

        if self.blender.is_blending:
            blended = self.blender.step(dt)
            self._fmm_state.control_law = blended
            self._fmm_state.is_blending = True
            self._fmm_state.blend_progress = self.blender.blend_progress
        else:
            flight_condition = {
                "airspeed": inputs.get("airspeed", 50.0),
                "altitude": inputs.get("altitude", 1000.0),
            }
            self._fmm_state.control_law = self.scheduler.get_scheduled_params(
                self.fsm.current_mode, flight_condition
            )
            self._fmm_state.is_blending = False

        airspeed = inputs.get("airspeed", 50.0)
        load_factor = inputs.get("load_factor", 1.0)
        altitude = inputs.get("altitude", 1000.0)

        protection = self.protector.check_envelope(airspeed, load_factor, altitude)
        self._fmm_state.protection_active = protection.protection_active

        elevator = inputs.get("elevator_cmd", 0.0)
        aileron = inputs.get("aileron_cmd", 0.0)
        rudder = inputs.get("rudder_cmd", 0.0)
        throttle = inputs.get("throttle_cmd", 0.5)

        if protection.override is not None:
            if protection.override.command_type == "speed_limit":
                throttle = min(throttle, 0.5)
            elif protection.override.command_type == "load_limit":
                elevator *= 0.5

        cl = self._fmm_state.control_law
        elevator_cmd = elevator * cl.pid_kp
        aileron_cmd = aileron * cl.sas_roll_gain
        rudder_cmd = rudder * cl.sas_yaw_gain

        self._state = ControlState(
            elevator_cmd=elevator_cmd,
            aileron_cmd=aileron_cmd,
            rudder_cmd=rudder_cmd,
            throttle_cmd=throttle,
            autopilot_mode=cl.autopilot_sub_mode.value,
        )

        self._time += dt

        result = ControlOutput(
            state=self._state,
            tracking_error=[0.0, 0.0, 0.0],
            fidelity=self.fidelity,
        ).model_dump()

        result["fmm_state"] = {
            "current_mode": self._fmm_state.current_mode.value,
            "is_blending": self._fmm_state.is_blending,
            "blend_progress": self._fmm_state.blend_progress,
            "protection_active": self._fmm_state.protection_active,
            "control_law": {
                "pid_kp": cl.pid_kp,
                "pid_ki": cl.pid_ki,
                "pid_kd": cl.pid_kd,
                "sas_pitch_gain": cl.sas_pitch_gain,
                "sas_roll_gain": cl.sas_roll_gain,
                "sas_yaw_gain": cl.sas_yaw_gain,
                "autopilot_sub_mode": cl.autopilot_sub_mode.value,
            },
        }
        return result

    def request_mode_transition(self, target_mode: FlightMode, flight_state: dict[str, Any] | None = None) -> TransitionResult:
        flight_state = flight_state or {}
        altitude = flight_state.get("altitude", 1000.0)
        airspeed = flight_state.get("airspeed", 50.0)
        gear_down = flight_state.get("gear_down", False)

        if not self.fsm.validate_transition(self.fsm.current_mode, target_mode):
            return TransitionResult(
                success=False, from_mode=self.fsm.current_mode, to_mode=target_mode,
                message=f"Invalid transition: {self.fsm.current_mode.value}→{target_mode.value}",
            )

        valid, reason = self.fsm.check_flight_state(target_mode, altitude, airspeed, gear_down)
        if not valid:
            return TransitionResult(
                success=False, from_mode=self.fsm.current_mode, to_mode=target_mode,
                message=f"Flight state check failed: {reason}",
            )

        source_params = self.scheduler.get_params(self.fsm.current_mode)
        result = self.fsm.execute_transition(target_mode)

        if result.success:
            target_params = self.scheduler.get_params(target_mode)
            self.blender.start_blending(source_params, target_params)
            self._fmm_state.current_mode = target_mode

        return result

    def emergency_override(self) -> TransitionResult:
        source_params = self.scheduler.get_params(self.fsm.current_mode)
        result = self.fsm.execute_transition(FlightMode.GoAround, transition_type="Emergency")

        if result.success:
            target_params = self.scheduler.get_params(FlightMode.GoAround)
            self.blender.start_blending(source_params, target_params)
            self._fmm_state.current_mode = FlightMode.GoAround

        return result

    def get_current_mode(self) -> FlightMode:
        return self.fsm.current_mode

    def get_control_law_params(self) -> ControlLawParams:
        return self._fmm_state.control_law

    def get_state(self) -> dict[str, Any]:
        return {
            "fmm_id": self.fmm_id,
            "current_mode": self.fsm.current_mode.value,
            "is_blending": self._fmm_state.is_blending,
            "blend_progress": self._fmm_state.blend_progress,
            "protection_active": self._fmm_state.protection_active,
            "control_state": self._state.model_dump(),
            "time": self._time,
        }

    def reset(self) -> None:
        self.fsm = FlightModeFSM()
        self.blender = ParameterBlender()
        self._state = ControlState()
        self._fmm_state = FMMState()
        self._time = 0.0

    def get_supported_fidelities(self) -> list[str]:
        return [FidelityLevel.Low.value, FidelityLevel.Mid.value, FidelityLevel.High.value]

    def get_schema_references(self) -> list[str]:
        return ["AircraftAvionics", "AircraftFlightEnvelope"]

    def validate_numerical_stability(self) -> StabilityCheck:
        cl = self._fmm_state.control_law
        if cl.pid_kp < 0 or cl.pid_ki < 0 or cl.pid_kd < 0:
            return StabilityCheck(is_stable=False, message="Negative PID gains detected")
        return StabilityCheck(is_stable=True, message="Stable")