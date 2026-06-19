from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(str, Enum):
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"


class KeyDerivationFunction(str, Enum):
    PBKDF2 = "pbkdf2"
    ARGON2ID = "argon2id"


@dataclass
class EncryptionKey:
    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: str = ""
    rotated_from: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.created_at:
            from datetime import datetime, timezone
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class EncryptedValue:
    key_id: str
    algorithm: EncryptionAlgorithm
    iv: bytes
    ciphertext: bytes
    tag: bytes | None = None
    version: int = 1

    def to_storage_format(self) -> str:
        parts = [
            self.version.to_bytes(1, "big"),
            self.key_id.encode(),
            b"|",
            self.algorithm.value.encode(),
            b"|",
            base64.b64encode(self.iv),
            b"|",
            base64.b64encode(self.ciphertext),
        ]
        if self.tag:
            parts.extend([b"|", base64.b64encode(self.tag)])
        return base64.b64encode(b"".join(parts)).decode()

    @classmethod
    def from_storage_format(cls, data: str) -> EncryptedValue:
        raw = base64.b64decode(data)
        version = int.from_bytes(raw[:1], "big")
        rest = raw[1:]

        parts = rest.split(b"|")
        key_id = parts[0].decode()
        algorithm = EncryptionAlgorithm(parts[1].decode())
        iv = base64.b64decode(parts[2])
        ciphertext = base64.b64decode(parts[3])
        tag = base64.b64decode(parts[4]) if len(parts) > 4 else None

        return cls(
            key_id=key_id,
            algorithm=algorithm,
            iv=iv,
            ciphertext=ciphertext,
            tag=tag,
            version=version,
        )


class ColumnEncryptionService:
    def __init__(self, master_key: str | None = None) -> None:
        self._keys: dict[str, EncryptionKey] = {}
        self._master_key = master_key or os.environ.get("AEROFORGE_ENCRYPTION_KEY", "")
        if not self._master_key:
            self._master_key = secrets.token_hex(32)
            logger.warning("No master encryption key configured; using generated key (not suitable for production)")

        self._sensitive_fields: dict[str, list[str]] = {}
        self._init_default_keys()

    def _init_default_keys(self) -> None:
        default_key = EncryptionKey(
            key_id="default",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_data=self._derive_key(self._master_key, "default"),
        )
        self._keys[default_key.key_id] = default_key

        pii_key = EncryptionKey(
            key_id="pii",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_data=self._derive_key(self._master_key, "pii"),
        )
        self._keys[pii_key.key_id] = pii_key

        financial_key = EncryptionKey(
            key_id="financial",
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_data=self._derive_key(self._master_key, "financial"),
        )
        self._keys[financial_key.key_id] = financial_key

    def _derive_key(self, master_key: str, purpose: str) -> bytes:
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            master_key.encode(),
            purpose.encode(),
            iterations=100000,
        )
        return derived[:32]

    def register_sensitive_fields(self, table: str, fields: list[str], key_id: str = "default") -> None:
        self._sensitive_fields[table] = fields
        if key_id not in self._keys:
            new_key = EncryptionKey(
                key_id=key_id,
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_data=self._derive_key(self._master_key, key_id),
            )
            self._keys[key_id] = new_key

    def encrypt_field(self, plaintext: str, key_id: str = "default") -> str:
        key = self._keys.get(key_id)
        if key is None:
            raise ValueError(f"Encryption key '{key_id}' not found")

        iv = os.urandom(12)
        ciphertext, tag = self._aes_gcm_encrypt(key.key_data, iv, plaintext.encode())

        encrypted = EncryptedValue(
            key_id=key_id,
            algorithm=key.algorithm,
            iv=iv,
            ciphertext=ciphertext,
            tag=tag,
        )
        return encrypted.to_storage_format()

    def decrypt_field(self, stored_value: str) -> str:
        encrypted = EncryptedValue.from_storage_format(stored_value)
        key = self._keys.get(encrypted.key_id)
        if key is None:
            raise ValueError(f"Encryption key '{encrypted.key_id}' not found")

        plaintext = self._aes_gcm_decrypt(
            key.key_data, encrypted.iv, encrypted.ciphertext, encrypted.tag
        )
        return plaintext.decode()

    def encrypt_row(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        sensitive_fields = self._sensitive_fields.get(table, [])
        if not sensitive_fields:
            return row

        encrypted_row = dict(row)
        for field_name in sensitive_fields:
            if field_name in encrypted_row and encrypted_row[field_name] is not None:
                value = str(encrypted_row[field_name])
                encrypted_row[field_name] = self.encrypt_field(value, key_id="pii")
        return encrypted_row

    def decrypt_row(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        sensitive_fields = self._sensitive_fields.get(table, [])
        if not sensitive_fields:
            return row

        decrypted_row = dict(row)
        for field_name in sensitive_fields:
            if field_name in decrypted_row and decrypted_row[field_name] is not None:
                try:
                    decrypted_row[field_name] = self.decrypt_field(decrypted_row[field_name])
                except Exception:
                    pass
        return decrypted_row

    def rotate_key(self, key_id: str) -> str:
        old_key = self._keys.get(key_id)
        if old_key is None:
            raise ValueError(f"Key '{key_id}' not found")

        new_key_id = f"{key_id}_v{len([k for k in self._keys if k.startswith(key_id)])}"
        new_key = EncryptionKey(
            key_id=new_key_id,
            algorithm=old_key.algorithm,
            key_data=self._derive_key(self._master_key, new_key_id),
            rotated_from=key_id,
        )
        old_key.active = False
        self._keys[new_key_id] = new_key

        logger.info("Rotated encryption key: %s -> %s", key_id, new_key_id)
        return new_key_id

    def _aes_gcm_encrypt(self, key: bytes, iv: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(key)
            ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
            ciphertext = ciphertext_with_tag[:-16]
            tag = ciphertext_with_tag[-16:]
            return ciphertext, tag
        except ImportError:
            return self._simulate_aes_gcm_encrypt(key, iv, plaintext)

    def _aes_gcm_decrypt(self, key: bytes, iv: bytes, ciphertext: bytes, tag: bytes | None) -> bytes:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(key)
            ciphertext_with_tag = ciphertext + (tag or b"")
            return aesgcm.decrypt(iv, ciphertext_with_tag, None)
        except ImportError:
            return self._simulate_aes_gcm_decrypt(key, iv, ciphertext, tag)

    def _simulate_aes_gcm_encrypt(self, key: bytes, iv: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
        xor_key = hashlib.sha256(key + iv).digest()
        extended_key = xor_key * (len(plaintext) // 32 + 1)
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, extended_key[:len(plaintext)]))
        tag = hashlib.sha256(key + iv + ciphertext).digest()[:16]
        return ciphertext, tag

    def _simulate_aes_gcm_decrypt(self, key: bytes, iv: bytes, ciphertext: bytes, tag: bytes | None) -> bytes:
        if tag:
            expected_tag = hashlib.sha256(key + iv + ciphertext).digest()[:16]
            if tag != expected_tag:
                raise ValueError("Authentication tag verification failed")
        xor_key = hashlib.sha256(key + iv).digest()
        extended_key = xor_key * (len(ciphertext) // 32 + 1)
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, extended_key[:len(ciphertext)]))
        return plaintext


@dataclass
class MinIOSSEConfig:
    sse_type: str = "SSE-S3"
    kms_key_id: str | None = None
    bucket_encryption: bool = True


class MinIOEncryptionService:
    def __init__(self, sse_config: MinIOSSEConfig | None = None) -> None:
        self.config = sse_config or MinIOSSEConfig()
        self._bucket_policies: dict[str, MinIOSSEConfig] = {}

    def configure_bucket_encryption(self, bucket: str, config: MinIOSSEConfig | None = None) -> None:
        effective = config or self.config
        self._bucket_policies[bucket] = effective
        logger.info("Configured SSE for bucket %s: type=%s", bucket, effective.sse_type)

    def get_encryption_headers(self, bucket: str) -> dict[str, str]:
        config = self._bucket_policies.get(bucket, self.config)
        headers: dict[str, str] = {}

        if config.sse_type == "SSE-S3":
            headers["x-amz-server-side-encryption"] = "AES256"
        elif config.sse_type == "SSE-KMS":
            headers["x-amz-server-side-encryption"] = "aws:kms"
            if config.kms_key_id:
                headers["x-amz-server-side-encryption-aws-kms-key-id"] = config.kms_key_id

        return headers

    def get_bucket_config(self, bucket: str) -> MinIOSSEConfig:
        return self._bucket_policies.get(bucket, self.config)


@dataclass
class BackupEncryptionConfig:
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_derivation: KeyDerivationFunction = KeyDerivationFunction.PBKDF2
    key_iterations: int = 100000
    compression: bool = True


class BackupEncryptionService:
    def __init__(self, config: BackupEncryptionConfig | None = None, passphrase: str | None = None) -> None:
        self.config = config or BackupEncryptionConfig()
        self._passphrase = passphrase or os.environ.get("AEROFORGE_BACKUP_PASSPHRASE", "")
        if not self._passphrase:
            self._passphrase = secrets.token_hex(32)
            logger.warning("No backup passphrase configured; using generated key")

    def encrypt_backup(self, data: bytes) -> bytes:
        salt = os.urandom(16)
        key = self._derive_backup_key(salt)
        iv = os.urandom(12)

        enc_service = ColumnEncryptionService.__new__(ColumnEncryptionService)
        ciphertext, tag = enc_service._simulate_aes_gcm_encrypt(key, iv, data)

        header = json.dumps({
            "algorithm": self.config.algorithm.value,
            "kdf": self.config.key_derivation.value,
            "iterations": self.config.key_iterations,
            "version": 1,
        }).encode()

        result = (
            len(header).to_bytes(4, "big") +
            header +
            salt +
            iv +
            (tag or b"") +
            ciphertext
        )
        return result

    def decrypt_backup(self, data: bytes) -> bytes:
        header_len = int.from_bytes(data[:4], "big")
        header = json.loads(data[4:4 + header_len])

        offset = 4 + header_len
        salt = data[offset:offset + 16]
        offset += 16
        iv = data[offset:offset + 12]
        offset += 12
        tag = data[offset:offset + 16]
        offset += 16
        ciphertext = data[offset:]

        key = self._derive_backup_key(salt)

        enc_service = ColumnEncryptionService.__new__(ColumnEncryptionService)
        plaintext = enc_service._simulate_aes_gcm_decrypt(key, iv, ciphertext, tag)
        return plaintext

    def _derive_backup_key(self, salt: bytes) -> bytes:
        if self.config.key_derivation == KeyDerivationFunction.PBKDF2:
            return hashlib.pbkdf2_hmac(
                "sha256",
                self._passphrase.encode(),
                salt,
                iterations=self.config.key_iterations,
            )[:32]
        return hashlib.pbkdf2_hmac(
            "sha256",
            self._passphrase.encode(),
            salt,
            iterations=self.config.key_iterations,
        )[:32]