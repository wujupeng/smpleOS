from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GraphSnapshot:
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str = ""
    graph_version: int = 0
    name: str = ""
    description: str = ""
    node_count: int = 0
    link_count: int = 0
    checksum: str = ""
    snapshot_data: dict = field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))