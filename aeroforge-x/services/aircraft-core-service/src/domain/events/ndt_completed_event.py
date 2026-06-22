from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class NDTCompletedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "NDTCompleted"
    ndt_record_id: str = ""
    material_lot_id: str = ""
    test_type: str = ""
    result: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())