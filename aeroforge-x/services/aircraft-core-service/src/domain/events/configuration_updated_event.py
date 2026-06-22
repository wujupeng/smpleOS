from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class ConfigurationUpdatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "ConfigurationUpdated"
    configuration_id: str = ""
    block_id: str = ""
    aircraft_type: str = ""
    change_type: ChangeType = ChangeType.UPDATED
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())