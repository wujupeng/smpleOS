from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CorrectiveActionRequest:
    car_id: str = ""
    ndt_record_id: str = ""
    description: str = ""
    status: str = "open"
    responsible_person: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "ndt_record_id": self.ndt_record_id,
            "description": self.description,
            "status": self.status,
            "responsible_person": self.responsible_person,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
        }

    @classmethod
    def from_row(cls, row) -> CorrectiveActionRequest:
        return cls(
            car_id=str(row["car_id"]),
            ndt_record_id=str(row["ndt_record_id"]),
            description=row["description"],
            status=row["status"],
            responsible_person=row["responsible_person"],
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else None,
            closed_at=row["closed_at"].isoformat() if row.get("closed_at") else None,
        )