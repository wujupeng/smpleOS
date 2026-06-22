from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Evidence:
    evidence_id: str = ""
    requirement_id: str = ""
    file_id: str = ""
    file_name: str = ""
    bucket: str = "aeroforge-cert-evidence"
    content_type: str = ""
    file_size: int = 0
    upload_timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "requirement_id": self.requirement_id,
            "file_id": self.file_id,
            "file_name": self.file_name,
            "bucket": self.bucket,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "upload_timestamp": self.upload_timestamp,
        }

    @classmethod
    def from_row(cls, row) -> Evidence:
        return cls(
            evidence_id=str(row["evidence_id"]),
            requirement_id=row["requirement_id"],
            file_id=str(row["file_id"]),
            file_name=row["file_name"],
            bucket=row["bucket"],
            content_type=row["content_type"],
            file_size=row["file_size"],
            upload_timestamp=row["upload_timestamp"].isoformat() if row.get("upload_timestamp") else None,
        )