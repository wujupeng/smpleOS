from enum import Enum


class AircraftType(str, Enum):
    FIXED_WING = "fixed_wing"
    GLIDER = "glider"
    EVTOL = "evtol"
    UAV = "uav"


class SpecStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CONFIRMED = "confirmed"
    FROZEN = "frozen"
    REJECTED = "rejected"

    def can_transition_to(self, target: "SpecStatus") -> bool:
        transitions = {
            SpecStatus.DRAFT: {SpecStatus.SUBMITTED, SpecStatus.REJECTED},
            SpecStatus.SUBMITTED: {SpecStatus.APPROVED, SpecStatus.REJECTED},
            SpecStatus.APPROVED: {SpecStatus.CONFIRMED, SpecStatus.REJECTED},
            SpecStatus.CONFIRMED: {SpecStatus.FROZEN},
            SpecStatus.FROZEN: set(),
            SpecStatus.REJECTED: {SpecStatus.DRAFT},
        }
        return target in transitions.get(self, set())


class PowerType(str, Enum):
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    GASOLINE = "gasoline"
    DIESEL = "diesel"


class ParameterCategory(str, Enum):
    PERFORMANCE = "performance"
    STRUCTURAL = "structural"
    AERODYNAMIC = "aerodynamic"
    PROPULSION = "propulsion"
    AVIONICS = "avionics"
    ENVIRONMENTAL = "environmental"
    OPERATIONAL = "operational"
    CERTIFICATION = "certification"


class ParameterPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TraceType(str, Enum):
    SATISFIES = "satisfies"
    VERIFIES = "verifies"
    DERIVES = "derives"
    TRACES_TO = "traces_to"
    IMPLEMENTED_BY = "implemented_by"


class TraceSourceType(str, Enum):
    SPEC = "spec"
    REQUIREMENT = "requirement"
    DESIGN_OBJECT = "design_object"
    TEST_CASE = "test_case"
    CERTIFICATION_ITEM = "certification_item"