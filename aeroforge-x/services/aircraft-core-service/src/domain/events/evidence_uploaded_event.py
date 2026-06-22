from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EvidenceUploadedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "EvidenceUploaded"
    evidence_id: str = ""
    requirement_id: str = ""
    file_id: str = ""
    file_name: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())