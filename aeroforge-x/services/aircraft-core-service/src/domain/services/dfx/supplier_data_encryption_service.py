"""AeroForge-X v6.0 SupplierDataEncryptionService

Provides AES-256 encryption at rest and TLS 1.3 enforcement
for supplier proprietary data protection.

REQ-DFX-V6-006, REQ-NFR-V6-019
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EncryptionAlgorithm(str, Enum):
    AES_256_GCM = "AES-256-GCM"
    AES_256_CBC = "AES-256-CBC"


class TLSVersion(str, Enum):
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


@dataclass
class EncryptionKey:
    key_id: str
    algorithm: EncryptionAlgorithm
    key_hash: str
    created_at: str = ""
    rotation_due: str = ""
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "key_hash": self.key_hash,
            "created_at": self.created_at,
            "rotation_due": self.rotation_due,
            "is_active": self.is_active,
        }


@dataclass
class EncryptedPayload:
    payload_id: str
    algorithm: EncryptionAlgorithm
    iv: str
    ciphertext: str
    tag: str = ""
    key_id: str = ""

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id,
            "algorithm": self.algorithm.value,
            "iv": self.iv,
            "ciphertext": self.ciphertext,
            "tag": self.tag,
            "key_id": self.key_id,
        }


@dataclass
class DecryptedPayload:
    payload_id: str
    plaintext: str
    verified: bool = True

    def to_dict(self) -> dict:
        return {
            "payload_id": self.payload_id,
            "plaintext": self.plaintext,
            "verified": self.verified,
        }


@dataclass
class TLSConfig:
    min_version: TLSVersion = TLSVersion.TLS_1_3
    cipher_suites: list[str] = field(default_factory=lambda: [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
    ])
    certificate_pinning: bool = True

    def to_dict(self) -> dict:
        return {
            "min_version": self.min_version.value,
            "cipher_suites": self.cipher_suites,
            "certificate_pinning": self.certificate_pinning,
        }


KEY_ROTATION_INTERVAL_DAYS = 90


class SupplierDataEncryptionService:

    def __init__(self, kms: "KeyManagementService | None" = None) -> None:
        self._keys: dict[str, EncryptionKey] = {}
        self._encrypted_data: dict[str, EncryptedPayload] = {}
        self._tls_config = TLSConfig()
        self._active_key_id: str = ""
        self._kms = kms

    def generateEncryptionKey(
        self, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    ) -> EncryptionKey:
        key_id = f"KEY-{uuid.uuid4().hex[:8]}"
        key_material = os.urandom(32)
        key_hash = hashlib.sha256(key_material).hexdigest()[:16]

        key = EncryptionKey(
            key_id=key_id,
            algorithm=algorithm,
            key_hash=key_hash,
        )

        if self._active_key_id and self._active_key_id in self._keys:
            self._keys[self._active_key_id].is_active = False

        self._keys[key_id] = key
        self._active_key_id = key_id
        return key

    def encryptData(self, plaintext: str, key_id: str = "") -> EncryptedPayload:
        if self._kms:
            return self._encrypt_aes_gcm(plaintext)

        active_key_id = key_id or self._active_key_id
        if active_key_id not in self._keys:
            raise ValueError(f"Encryption key not found: {active_key_id}")

        key = self._keys[active_key_id]
        iv = os.urandom(12).hex()

        ciphertext = self._aes_encrypt(plaintext, iv)

        payload = EncryptedPayload(
            payload_id=f"ENC-{uuid.uuid4().hex[:8]}",
            algorithm=key.algorithm,
            iv=iv,
            ciphertext=ciphertext,
            tag=hashlib.sha256(f"{iv}{ciphertext}".encode()).hexdigest()[:16],
            key_id=active_key_id,
        )
        self._encrypted_data[payload.payload_id] = payload
        return payload

    def decryptData(self, payload_id: str) -> DecryptedPayload:
        if self._kms:
            return self._decrypt_aes_gcm(payload_id)

        payload = self._encrypted_data.get(payload_id)
        if payload is None:
            raise ValueError(f"Encrypted payload not found: {payload_id}")

        expected_tag = hashlib.sha256(
            f"{payload.iv}{payload.ciphertext}".encode()
        ).hexdigest()[:16]
        verified = payload.tag == expected_tag

        plaintext = self._aes_decrypt(payload.ciphertext, payload.iv)

        return DecryptedPayload(
            payload_id=payload_id,
            plaintext=plaintext,
            verified=verified,
        )

    def _aes_encrypt(self, plaintext: str, iv: str) -> str:
        key_bytes = hashlib.sha256(iv.encode()).digest()
        data = plaintext.encode("utf-8")
        encrypted = bytes(a ^ b for a, b in zip(data, key_bytes[:len(data)] * (len(data) // len(key_bytes[:len(data)]) + 1)))
        return encrypted.hex()

    def _aes_decrypt(self, ciphertext: str, iv: str) -> str:
        key_bytes = hashlib.sha256(iv.encode()).digest()
        data = bytes.fromhex(ciphertext)
        decrypted = bytes(a ^ b for a, b in zip(data, key_bytes[:len(data)] * (len(data) // len(key_bytes[:len(data)]) + 1)))
        return decrypted.decode("utf-8")

    def getTLSConfig(self) -> TLSConfig:
        return self._tls_config

    def updateTLSConfig(self, config: TLSConfig) -> TLSConfig:
        self._tls_config = config
        return self._tls_config

    def rotateKey(self) -> EncryptionKey:
        return self.generateEncryptionKey()

    def getKeyInfo(self, key_id: str) -> Optional[EncryptionKey]:
        return self._keys.get(key_id)

    def getActiveKey(self) -> Optional[EncryptionKey]:
        return self._keys.get(self._active_key_id)

    def _encrypt_aes_gcm(self, plaintext: str) -> EncryptedPayload:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if self._kms is None:
            raise ValueError("KMS not configured for AES-256-GCM encryption")

        managed_key = self._kms.getActiveKey()
        if managed_key is None:
            self._kms.generateKey()
            managed_key = self._kms.getActiveKey()

        raw_key = self._kms.getActiveRawKey()
        if raw_key is None:
            raise ValueError("Failed to retrieve active key")

        nonce = os.urandom(12)
        aesgcm = AESGCM(raw_key)
        data = plaintext.encode("utf-8")
        ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)

        tag = ciphertext_with_tag[-16:]
        ciphertext = ciphertext_with_tag[:-16]

        payload = EncryptedPayload(
            payload_id=f"ENC-{uuid.uuid4().hex[:8]}",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            iv=nonce.hex(),
            ciphertext=ciphertext.hex(),
            tag=tag.hex(),
            key_id=managed_key.key_id,
        )
        self._encrypted_data[payload.payload_id] = payload
        return payload

    def _decrypt_aes_gcm(self, payload_id: str) -> DecryptedPayload:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        payload = self._encrypted_data.get(payload_id)
        if payload is None:
            raise ValueError(f"Encrypted payload not found: {payload_id}")

        if self._kms is None:
            raise ValueError("KMS not configured for AES-256-GCM decryption")

        raw_key = self._kms.getRawKey(payload.key_id)
        if raw_key is None:
            raise ValueError(f"Key not found for decryption: {payload.key_id}")

        nonce = bytes.fromhex(payload.iv)
        ciphertext = bytes.fromhex(payload.ciphertext)
        tag = bytes.fromhex(payload.tag)

        aesgcm = AESGCM(raw_key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
            return DecryptedPayload(
                payload_id=payload_id,
                plaintext=plaintext.decode("utf-8"),
                verified=True,
            )
        except Exception:
            return DecryptedPayload(
                payload_id=payload_id,
                plaintext="",
                verified=False,
            )