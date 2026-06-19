from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.enums import FidelityLevel


class ActiveModelRef(BaseModel):
    model_id: str
    fidelity_level: FidelityLevel
    is_active: bool = True
    deployed_at: datetime = Field(default_factory=datetime.utcnow)