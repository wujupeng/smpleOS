from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any


@dataclass
class BOMLine:
    line_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_line_id: str | None = None
    part_number: str = ""
    part_name: str = ""
    quantity: float = 1.0
    unit: str = "ea"
    material_ref: str | None = None
    sort_order: int = 0
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "parent_line_id": self.parent_line_id,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "sort_order": self.sort_order,
        }


@dataclass
class EBOM:
    bom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bom_number: str = ""
    product_id: str = ""
    version: int = 1
    status: str = "draft"
    lines: list[BOMLine] = field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_line(self, line: BOMLine) -> None:
        self.lines.append(line)
        self.updated_at = datetime.now(timezone.utc)

    def remove_line(self, line_id: str) -> None:
        self.lines = [l for l in self.lines if l.line_id != line_id]
        self.updated_at = datetime.now(timezone.utc)

    def get_tree(self) -> list[dict]:
        return [l.to_dict() for l in self.lines]

    def to_dict(self) -> dict:
        return {
            "bom_id": self.bom_id,
            "bom_number": self.bom_number,
            "product_id": self.product_id,
            "version": self.version,
            "status": self.status,
            "line_count": len(self.lines),
        }


@dataclass
class MBOM:
    bom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bom_number: str = ""
    product_id: str = ""
    ebom_ref: str | None = None
    version: int = 1
    status: str = "draft"
    lines: list[BOMLine] = field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_line(self, line: BOMLine) -> None:
        self.lines.append(line)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "bom_id": self.bom_id,
            "bom_number": self.bom_number,
            "product_id": self.product_id,
            "ebom_ref": self.ebom_ref,
            "version": self.version,
            "status": self.status,
            "line_count": len(self.lines),
        }


@dataclass
class SBOM:
    bom_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bom_number: str = ""
    product_id: str = ""
    ebom_ref: str | None = None
    version: int = 1
    status: str = "draft"
    lines: list[BOMLine] = field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_line(self, line: BOMLine) -> None:
        self.lines.append(line)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "bom_id": self.bom_id,
            "bom_number": self.bom_number,
            "product_id": self.product_id,
            "ebom_ref": self.ebom_ref,
            "version": self.version,
            "status": self.status,
            "line_count": len(self.lines),
        }