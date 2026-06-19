from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import SourceTag


class AircraftProperty(BaseModel):
    value_id: str
    object_id: str
    property_def_id: str
    value: Any
    unit: str
    source: SourceTag
    source_detail: str = ""
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version_id: str = ""