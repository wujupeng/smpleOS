from enum import Enum


class PhysicsType(str, Enum):
    FEA = "FEA"
    CFD = "CFD"
    Thermodynamics = "Thermodynamics"
    MultiBodyDynamics = "MultiBodyDynamics"
    Electromagnetics = "Electromagnetics"


class HierarchyLevel(str, Enum):
    FullAircraft = "FullAircraft"
    System = "System"
    Component = "Component"
    Detail = "Detail"


class FidelityLevel(str, Enum):
    Low = "Low"
    Mid = "Mid"
    High = "High"


class SolverType(str, Enum):
    OpenFOAM = "OpenFOAM"
    FEniCS = "FEniCS"
    Custom = "Custom"


class SimulationStatus(str, Enum):
    Queued = "Queued"
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"


class ReductionMethod(str, Enum):
    POD = "POD"
    SVD = "SVD"
    NeuralNetwork = "NeuralNetwork"


class ValidationStatus(str, Enum):
    Pending = "Pending"
    Passed = "Passed"
    Failed = "Failed"


class ModelStatus(str, Enum):
    Draft = "Draft"
    Validated = "Validated"
    Deployed = "Deployed"
    Deprecated = "Deprecated"


class CalibrationStatus(str, Enum):
    Pending = "Pending"
    InProgress = "InProgress"
    Completed = "Completed"
    Failed = "Failed"


class HealthStatus(str, Enum):
    Healthy = "Healthy"
    Warning = "Warning"
    Critical = "Critical"


COMPATIBILITY_RULES: dict[str, list[str]] = {
    "FEA": ["FullAircraft", "System", "Component", "Detail"],
    "CFD": ["FullAircraft", "System", "Component"],
    "Thermodynamics": ["System", "Component", "Detail"],
    "MultiBodyDynamics": ["FullAircraft", "System"],
    "Electromagnetics": ["System", "Component", "Detail"],
}

FIDELITY_COMPATIBILITY: dict[str, list[str]] = {
    "FullAircraft": ["Low", "Mid"],
    "System": ["Low", "Mid", "High"],
    "Component": ["Low", "Mid", "High"],
    "Detail": ["Mid", "High"],
}