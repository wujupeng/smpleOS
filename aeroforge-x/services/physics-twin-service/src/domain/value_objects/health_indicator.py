from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.enums import HealthStatus


class HealthIndicator(BaseModel):
    component_id: str
    score: int = 100
    status: HealthStatus = HealthStatus.Healthy
    computed_at: datetime = Field(default_factory=datetime.utcnow)