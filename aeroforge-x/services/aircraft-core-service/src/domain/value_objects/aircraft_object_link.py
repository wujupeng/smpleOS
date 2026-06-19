from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import LinkType


class AircraftObjectLink(BaseModel):
    link_id: str
    source_id: str
    target_id: str
    link_type: LinkType
    propagation_rule: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def involves(self, object_id: str) -> bool:
        return self.source_id == object_id or self.target_id == object_id

    def get_other(self, object_id: str) -> str | None:
        if self.source_id == object_id:
            return self.target_id
        if self.target_id == object_id:
            return self.source_id
        return None