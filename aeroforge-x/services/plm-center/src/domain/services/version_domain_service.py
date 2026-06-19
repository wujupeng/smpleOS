from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aeroforge_common.utils.helpers import generate_code


class Version:
    def __init__(
        self,
        object_id: str,
        major: int = 1,
        minor: int = 0,
        change_summary: str = "",
        created_by: str = "",
        snapshot: dict[str, Any] | None = None,
    ) -> None:
        self.version_id = generate_code("VER")
        self.object_id = object_id
        self.major = major
        self.minor = minor
        self.change_summary = change_summary
        self.created_by = created_by
        self.snapshot = snapshot or {}
        self.created_at: datetime = datetime.now(timezone.utc)

    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "object_id": self.object_id,
            "major": self.major,
            "minor": self.minor,
            "version_string": self.version_string,
            "change_summary": self.change_summary,
            "created_by": self.created_by,
            "snapshot": self.snapshot,
            "created_at": self.created_at.isoformat(),
        }


class VersionDomainService:
    def create_version(self, object_id: str, change_summary: str, created_by: str, snapshot: dict[str, Any], current_major: int = 0, current_minor: int = 0) -> Version:
        if change_summary and any(kw in change_summary.lower() for kw in ["重大", "breaking", "major"]):
            major = current_major + 1
            minor = 0
        else:
            major = current_major
            minor = current_minor + 1
        return Version(
            object_id=object_id,
            major=major,
            minor=minor,
            change_summary=change_summary,
            created_by=created_by,
            snapshot=snapshot,
        )

    def compare_versions(self, v1: Version, v2: Version) -> dict[str, Any]:
        diff: dict[str, Any] = {"added": {}, "removed": {}, "changed": {}}
        s1 = v1.snapshot
        s2 = v2.snapshot
        all_keys = set(list(s1.keys()) + list(s2.keys()))
        for key in all_keys:
            in_v1 = key in s1
            in_v2 = key in s2
            if in_v1 and not in_v2:
                diff["removed"][key] = s1[key]
            elif not in_v1 and in_v2:
                diff["added"][key] = s2[key]
            elif s1[key] != s2[key]:
                diff["changed"][key] = {"from": s1[key], "to": s2[key]}
        return diff