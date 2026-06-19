from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class HandlerInput(BaseModel):
    model_id: str = ""
    rule_set_id: str = ""
    parameters: dict[str, Any] = {}

    model_config = {"extra": "allow"}


class HandlerOutput(BaseModel):
    status: str = "completed"
    result: dict[str, Any] = {}
    errors: list[str] = []
    schema_refs_used: list[str] = []

    model_config = {"extra": "allow"}


class ActivityHandlerV3(ABC):

    @abstractmethod
    def execute(self, input_data: HandlerInput) -> HandlerOutput:
        pass

    def compensate(self, input_data: HandlerInput) -> None:
        pass

    @abstractmethod
    def get_handler_name(self) -> str:
        pass

    def get_schema_references(self) -> list[str]:
        return []

    def validate_input(self, input_data: HandlerInput) -> list[str]:
        return []