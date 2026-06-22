from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CARCreatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "CARCreated"
    car_id: str = ""
    ndt_record_id: str = ""
    description: str = ""
    status: str = "open"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())