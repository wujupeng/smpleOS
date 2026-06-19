from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.domain.enums import BaselineType


class AircraftObjectVersion(BaseModel):
    version_id: str
    object_id: str
    version_number: int
    snapshot: dict[str, Any]
    change_summary: str
    author: str
    baseline_type: BaselineType = BaselineType.None_
    is_frozen: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def freeze(self) -> None:
        self.is_frozen = True

    def set_baseline_type(self, baseline_type: BaselineType) -> None:
        self.baseline_type = baseline_type
        if baseline_type in (BaselineType.Frozen, BaselineType.Released):
            self.is_frozen = True