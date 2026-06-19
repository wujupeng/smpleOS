from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import DataType, ObjectType, PropertyType


class PropertyDefinition(BaseModel):
    id: str
    name: str
    property_type: PropertyType
    data_type: DataType
    unit: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    applicable_object_types: list[ObjectType] = Field(default_factory=list)
    derivation_formula: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_value(self, value: Any) -> bool:
        if "range" in self.constraints:
            min_val = self.constraints["range"].get("min")
            max_val = self.constraints["range"].get("max")
            if min_val is not None and value < min_val:
                return False
            if max_val is not None and value > max_val:
                return False
        if "allowed_values" in self.constraints:
            if value not in self.constraints["allowed_values"]:
                return False
        if "pattern" in self.constraints:
            import re
            if not re.match(self.constraints["pattern"], str(value)):
                return False
        return True