from enum import Enum


class NodeType(str, Enum):
    REQUIREMENT = "requirement"
    DESIGN = "design"
    STRUCTURE = "structure"
    MATERIAL = "material"
    MANUFACTURING = "manufacturing"
    FLIGHT = "flight"
    MAINTENANCE = "maintenance"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]