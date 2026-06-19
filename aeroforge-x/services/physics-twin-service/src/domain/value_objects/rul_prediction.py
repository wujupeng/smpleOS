from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RULPrediction(BaseModel):
    component_id: str
    rul_value: float
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    predicted_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = 1.0