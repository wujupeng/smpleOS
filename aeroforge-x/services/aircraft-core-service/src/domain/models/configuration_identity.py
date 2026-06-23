from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfigurationIdentity:
    identity_id: str = ""
    label: str = ""
    node_type: str = ""
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "identity_id": self.identity_id,
            "label": self.label,
            "node_type": self.node_type,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> ConfigurationIdentity:
        return cls(
            identity_id=str(row["identity_id"]),
            label=row["label"],
            node_type=row["node_type"],
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )