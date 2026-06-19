from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_code(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{timestamp}-{short_id}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def validate_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False