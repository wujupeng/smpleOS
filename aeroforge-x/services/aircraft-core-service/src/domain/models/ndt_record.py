from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NDTRecord:
    ndt_record_id: str = ""
    material_lot_id: str = ""
    test_type: str = ""
    result: str = ""
    inspector: str = ""
    test_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ndt_record_id": self.ndt_record_id,
            "material_lot_id": self.material_lot_id,
            "test_type": self.test_type,
            "result": self.result,
            "inspector": self.inspector,
            "test_date": self.test_date,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> NDTRecord:
        return cls(
            ndt_record_id=str(row["ndt_record_id"]),
            material_lot_id=row["material_lot_id"],
            test_type=row["test_type"],
            result=row["result"],
            inspector=row["inspector"],
            test_date=str(row["test_date"]) if row.get("test_date") else None,
            notes=row.get("notes"),
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
        )