from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TraceEdge:
    edge_id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    edge_type: str = ""
    properties: Optional[dict] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "properties": self.properties or {},
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> TraceEdge:
        import json
        props = row.get("properties")
        if isinstance(props, str):
            props = json.loads(props)
        return cls(
            edge_id=str(row["edge_id"]),
            source_node_id=str(row["source_node_id"]),
            target_node_id=str(row["target_node_id"]),
            edge_type=row["edge_type"],
            properties=props if isinstance(props, dict) else {},
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )