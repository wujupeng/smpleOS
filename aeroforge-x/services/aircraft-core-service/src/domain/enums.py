from enum import Enum


class ObjectType(str, Enum):
    Aircraft = "Aircraft"
    System = "System"
    Subsystem = "Subsystem"
    Component = "Component"
    Part = "Part"


class LifecycleState(str, Enum):
    Concept = "Concept"
    Design = "Design"
    Manufacturing = "Manufacturing"
    Test = "Test"
    Operation = "Operation"
    Retirement = "Retirement"


class LinkType(str, Enum):
    Contains = "contains"
    DependsOn = "depends_on"
    TraceTo = "trace_to"
    ChangePropagatesTo = "change_propagates_to"


class PropertyType(str, Enum):
    Geometric = "Geometric"
    Material = "Material"
    Performance = "Performance"
    Certification = "Certification"
    Cost = "Cost"


class SourceTag(str, Enum):
    DesignValue = "DesignValue"
    MeasuredValue = "MeasuredValue"
    InferredValue = "InferredValue"


class BaselineType(str, Enum):
    None_ = "None"
    Frozen = "Frozen"
    Released = "Released"


class DataType(str, Enum):
    Float = "Float"
    Integer = "Integer"
    String = "String"
    Boolean = "Boolean"
    JSON = "JSON"


OBJECT_TYPE_HIERARCHY: dict[ObjectType, list[ObjectType]] = {
    ObjectType.Aircraft: [ObjectType.System],
    ObjectType.System: [ObjectType.Subsystem],
    ObjectType.Subsystem: [ObjectType.Component],
    ObjectType.Component: [ObjectType.Part],
    ObjectType.Part: [],
}

VALID_TRANSITIONS: dict[LifecycleState, list[LifecycleState]] = {
    LifecycleState.Concept: [LifecycleState.Design],
    LifecycleState.Design: [LifecycleState.Manufacturing, LifecycleState.Concept],
    LifecycleState.Manufacturing: [LifecycleState.Test, LifecycleState.Design],
    LifecycleState.Test: [LifecycleState.Operation, LifecycleState.Manufacturing],
    LifecycleState.Operation: [LifecycleState.Retirement],
    LifecycleState.Retirement: [],
}

TRANSITION_VALIDATION_RULES: dict[tuple[LifecycleState, LifecycleState], list[str]] = {
    (LifecycleState.Concept, LifecycleState.Design): ["requirement_associations"],
    (LifecycleState.Design, LifecycleState.Manufacturing): ["design_baseline_frozen"],
    (LifecycleState.Manufacturing, LifecycleState.Test): ["fai_report_submitted"],
    (LifecycleState.Test, LifecycleState.Operation): ["verification_report_approved"],
    (LifecycleState.Operation, LifecycleState.Retirement): ["retirement_approval"],
}