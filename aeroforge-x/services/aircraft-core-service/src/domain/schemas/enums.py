from __future__ import annotations

from enum import Enum


class SchemaType(str, Enum):
    AircraftGeometry = "AircraftGeometry"
    AircraftStructure = "AircraftStructure"
    AircraftPropulsion = "AircraftPropulsion"
    AircraftAvionics = "AircraftAvionics"
    AircraftFlightEnvelope = "AircraftFlightEnvelope"
    AircraftCertification = "AircraftCertification"


class SchemaStatus(str, Enum):
    Draft = "Draft"
    Published = "Published"
    Deprecated = "Deprecated"


class FieldDataType(str, Enum):
    Float = "Float"
    Integer = "Integer"
    String = "String"
    Boolean = "Boolean"
    Object = "Object"
    Array = "Array"


class EngineType(str, Enum):
    Turbofan = "Turbofan"
    Turboprop = "Turboprop"
    Electric = "Electric"
    Hybrid = "Hybrid"
    Piston = "Piston"


class ComplianceStatus(str, Enum):
    Compliant = "Compliant"
    NonCompliant = "NonCompliant"
    Partial = "Partial"
    NotAssessed = "NotAssessed"


class ComplianceMethod(str, Enum):
    MOC0 = "MOC0"
    MOC1 = "MOC1"
    MOC2 = "MOC2"
    MOC3 = "MOC3"
    MOC4 = "MOC4"
    MOC5 = "MOC5"
    MOC6 = "MOC6"
    MOC7 = "MOC7"
    MOC8 = "MOC8"
    MOC9 = "MOC9"


class ControlLawType(str, Enum):
    PID = "PID"
    LQR = "LQR"
    SAS = "SAS"
    Autopilot = "Autopilot"


class AutopilotMode(str, Enum):
    OFF = "OFF"
    ALTITUDE_HOLD = "ALTITUDE_HOLD"
    HEADING_HOLD = "HEADING_HOLD"
    SPEED_HOLD = "SPEED_HOLD"
    NAV = "NAV"
    APPROACH = "APPROACH"


class AttitudeMode(str, Enum):
    Euler = "Euler"
    Quaternion = "Quaternion"