from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ComplianceRequirement:
    requirement_id: str = ""
    regulation: str = ""
    description: str = ""
    compliance_status: str = "pending"
    responsible_person: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "regulation": self.regulation,
            "description": self.description,
            "compliance_status": self.compliance_status,
            "responsible_person": self.responsible_person,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> ComplianceRequirement:
        return cls(
            requirement_id=row["requirement_id"],
            regulation=row["regulation"],
            description=row["description"],
            compliance_status=row["compliance_status"],
            responsible_person=row.get("responsible_person"),
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else None,
        )