from enum import Enum


class ConfigItemType(str, Enum):
    AIRCRAFT = "aircraft"
    WING = "wing"
    TAIL = "tail"
    FUSELAGE = "fuselage"
    POWERTRAIN = "powertrain"
    FLIGHT_CONTROL = "flight_control"
    AVIONICS = "avionics"
    WIRE_HARNESS = "wire_harness"
    BATTERY = "battery"
    MOTOR = "motor"
    ESC = "esc"
    PROPELLER = "propeller"
    SENSOR = "sensor"
    SOFTWARE = "software"
    HARDWARE = "hardware"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]