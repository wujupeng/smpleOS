"""AeroForge-X V6.1 KeyManagementService

Internal KMS for AES-256-GCM encryption key lifecycle:
generation, rotation, retrieval, deactivation.
DEK encrypted by KEK (from ENCRYPTION_MASTER_KEY env var).

REQ-ENG-013, REQ-ENG-017
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class ManagedKey:
    key_id: str
    algorithm: str = "AES-256-GCM"
    encrypted_key_material: bytes = b""
    key_hash: str = ""
    is_active: bool = True
    rotation_due_at: str = ""
    created_at: str = ""
    deactivated_at: str = ""
    _raw_key: bytes = field(default_factory=bytes, repr=False)

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm,
            "key_hash": self.key_hash,
            "is_active": self.is_active,
            "rotation_due_at": self.rotation_due_at,
            "created_at": self.created_at,
            "deactivated_at": self.deactivated_at,
        }


ROTATION_DAYS = 90


class KeyManagementService:

    def __init__(self, master_key: str = "") -> None:
        self._keys: dict[str, ManagedKey] = {}
        self._active_key_id: str = ""
        self._kek = self._derive_kek(master_key or os.environ.get("ENCRYPTION_MASTER_KEY", "default-master-key-32bytes!!"))
        self._audit_log: list[dict] = []

    def _derive_kek(self, master_key: str) -> bytes:
        return hashlib.sha256(master_key.encode()).digest()

    def _encrypt_dek(self, dek: bytes) -> bytes:
        encrypted = bytes(a ^ b for a, b in zip(dek, self._kek[:len(dek)] * (len(dek) // len(self._kek[:len(dek)]) + 1)))
        return encrypted

    def _decrypt_dek(self, encrypted_dek: bytes) -> bytes:
        kek_slice = self._kek[:len(encrypted_dek)]
        decrypted = bytes(a ^ b for a, b in zip(encrypted_dek, kek_slice * (len(encrypted_dek) // len(kek_slice) + 1)))
        return decrypted

    def generateKey(self) -> ManagedKey:
        key_id = f"KEY-{uuid.uuid4().hex[:8]}"
        raw_key = os.urandom(32)
        encrypted_key = self._encrypt_dek(raw_key)
        key_hash = hashlib.sha256(raw_key).hexdigest()[:16]

        rotation_due = (datetime.utcnow() + timedelta(days=ROTATION_DAYS)).isoformat()

        if self._active_key_id and self._active_key_id in self._keys:
            self._keys[self._active_key_id].is_active = False

        key = ManagedKey(
            key_id=key_id,
            encrypted_key_material=encrypted_key,
            key_hash=key_hash,
            rotation_due_at=rotation_due,
            created_at=datetime.utcnow().isoformat(),
            _raw_key=raw_key,
        )
        self._keys[key_id] = key
        self._active_key_id = key_id

        self._audit_log.append({
            "action": "generate",
            "key_id": key_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return key

    def rotateKey(self) -> ManagedKey:
        old_key_id = self._active_key_id
        new_key = self.generateKey()

        self._audit_log.append({
            "action": "rotate",
            "old_key_id": old_key_id,
            "new_key_id": new_key.key_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return new_key

    def getKey(self, key_id: str) -> Optional[ManagedKey]:
        return self._keys.get(key_id)

    def getRawKey(self, key_id: str) -> Optional[bytes]:
        key = self._keys.get(key_id)
        if key is None:
            return None
        if key._raw_key:
            return key._raw_key
        return self._decrypt_dek(key.encrypted_key_material)

    def deactivateKey(self, key_id: str) -> Optional[ManagedKey]:
        key = self._keys.get(key_id)
        if key is None:
            return None
        key.is_active = False
        key.deactivated_at = datetime.utcnow().isoformat()

        self._audit_log.append({
            "action": "deactivate",
            "key_id": key_id,
            "timestamp": datetime.utcnow().isoformat(),
        })

        return key

    def getActiveKey(self) -> Optional[ManagedKey]:
        return self._keys.get(self._active_key_id)

    def getActiveRawKey(self) -> Optional[bytes]:
        return self.getRawKey(self._active_key_id)

    def getAuditLog(self) -> list[dict]:
        return list(self._audit_log)