from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MaterialLot:
    lot_id: str = ""
    material_code: str = ""
    material_name: str = ""
    supplier_id: str = ""
    manufacture_date: Optional[str] = None
    received_date: Optional[str] = None
    certificate_no: str = ""
    status: str = "received"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "material_code": self.material_code,
            "material_name": self.material_name,
            "supplier_id": self.supplier_id,
            "manufacture_date": self.manufacture_date,
            "received_date": self.received_date,
            "certificate_no": self.certificate_no,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> MaterialLot:
        return cls(
            lot_id=row["lot_id"],
            material_code=row["material_code"],
            material_name=row["material_name"],
            supplier_id=row["supplier_id"],
            manufacture_date=str(row["manufacture_date"]) if row.get("manufacture_date") else None,
            received_date=str(row["received_date"]) if row.get("received_date") else None,
            certificate_no=row["certificate_no"],
            status=row["status"],
            created_at=row["created_at"].isoformat() if row.get("created_at") else None,
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else None,
        )