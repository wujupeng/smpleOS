"""AeroForge-X Unified Configuration UUID

Per Project Manager's directive: establish a single Configuration UUID
that threads through all domains:

    Requirement → EBOM → MBOM → SBOM → CAD → CAE → MDO →
    Simulation → Certification → Supplier → Factory → Fleet

Format: CFG-{YEAR}-{6-digit-sequence}
Example: CFG-2026-000001

This prevents Configuration Drift across v7+ evolution.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfigurationIdentity:
    config_uuid: str
    aircraft_type: str
    block_id: str
    origin: str
    created_at: float = field(default_factory=time.time)
    parent_config_uuid: Optional[str] = None
    status: str = "Active"

    def to_dict(self) -> dict:
        return {
            "config_uuid": self.config_uuid,
            "aircraft_type": self.aircraft_type,
            "block_id": self.block_id,
            "origin": self.origin,
            "created_at": self.created_at,
            "parent_config_uuid": self.parent_config_uuid,
            "status": self.status,
        }


class ConfigurationUUIDGenerator:

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> ConfigurationUUIDGenerator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._counter = 0
                    cls._instance._year = time.strftime("%Y")
        return cls._instance

    def generate(self, aircraft_type: str = "", block_id: str = "", origin: str = "", parent_uuid: str = None) -> ConfigurationIdentity:
        self._counter += 1
        seq = f"{self._counter:06d}"
        config_uuid = f"CFG-{self._year}-{seq}"
        return ConfigurationIdentity(
            config_uuid=config_uuid,
            aircraft_type=aircraft_type,
            block_id=block_id,
            origin=origin,
            parent_config_uuid=parent_uuid,
        )

    @staticmethod
    def validate(config_uuid: str) -> bool:
        parts = config_uuid.split("-")
        if len(parts) != 3:
            return False
        if parts[0] != "CFG":
            return False
        if not parts[1].isdigit() or len(parts[1]) != 4:
            return False
        if not parts[2].isdigit() or len(parts[2]) != 6:
            return False
        return True

    @staticmethod
    def derive_child(parent_uuid: str, origin: str) -> str:
        return f"{parent_uuid}:{origin}"


CONFIG_UUID_GENERATOR = ConfigurationUUIDGenerator()