from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class CARClosedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "CARClosed"
    car_id: str = ""
    closed_by: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())