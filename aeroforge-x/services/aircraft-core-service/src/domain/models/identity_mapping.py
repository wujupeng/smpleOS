from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IdentityMapping:
    mapping_id: str = ""
    identity_id: str = ""
    domain: str = ""
    domain_id: str = ""
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "identity_id": self.identity_id,
            "domain": self.domain,
            "domain_id": self.domain_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> IdentityMapping:
        return cls(
            mapping_id=str(row["mapping_id"]),
            identity_id=str(row["identity_id"]),
            domain=row["domain"],
            domain_id=row["domain_id"],
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )