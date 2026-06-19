from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class AircraftSchemaBase(BaseModel):
    schema_version: int = Field(default=1, ge=1, description="Schema definition version")
    schema_id: str = Field(default="", description="Unique schema instance identifier")

    def validate_all(self) -> dict[str, Any]:
        try:
            self.model_validate(self.model_dump())
            return {"valid": True, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["__schema_type__"] = self.__class__.__name__
        data["__schema_version__"] = self.schema_version
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AircraftSchemaBase:
        cleaned = {k: v for k, v in data.items() if not k.startswith("__")}
        return cls(**cleaned)

    model_config = {"extra": "allow"}