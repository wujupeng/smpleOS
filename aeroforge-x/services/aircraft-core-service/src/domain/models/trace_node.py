from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TraceNode:
    node_id: str = ""
    identity_id: Optional[str] = None
    node_type: str = ""
    label: str = ""
    properties: Optional[dict] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "identity_id": self.identity_id,
            "node_type": self.node_type,
            "label": self.label,
            "properties": self.properties or {},
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> TraceNode:
        import json
        props = row.get("properties")
        if isinstance(props, str):
            props = json.loads(props)
        return cls(
            node_id=str(row["node_id"]),
            identity_id=str(row["identity_id"]) if row.get("identity_id") else None,
            node_type=row["node_type"],
            label=row["label"],
            properties=props if isinstance(props, dict) else {},
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )