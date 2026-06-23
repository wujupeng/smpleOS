from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SemanticVersion:
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> SemanticVersion:
        parts = version_str.strip().lstrip("v").split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_str}, expected major.minor.patch")
        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))


def is_backward_compatible(old: SemanticVersion, new: SemanticVersion) -> bool:
    if new.major != old.major:
        return False
    return True