from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from aeroforge_common.security.encryption import (
    BackupEncryptionService,
    ColumnEncryptionService,
    EncryptedValue,
    MinIOEncryptionService,
    MinIOSSEConfig,
)
from aeroforge_common.security.session import (
    SessionConfig,
    SessionSecurityService,
    SessionStatus,
)
from aeroforge_common.security.api_security import (
    ConfirmationService,
    ConfirmationToken,
    RateLimiter,
    RateLimitRule,
    RequestSigningService,
)


class TestColumnEncryption:
    def setup_method(self):
        self.service = ColumnEncryptionService(master_key="test-master-key-12345")

    def test_encrypt_decrypt_field(self):
        encrypted = self.service.encrypt_field("sensitive data", "default")
        assert encrypted != "sensitive data"
        decrypted = self.service.decrypt_field(encrypted)
        assert decrypted == "sensitive data"

    def test_encrypt_with_pii_key(self):
        encrypted = self.service.encrypt_field("PII data", "pii")
        decrypted = self.service.decrypt_field(encrypted)
        assert decrypted == "PII data"

    def test_encrypt_row(self):
        self.service.register_sensitive_fields("users", ["email", "phone"], "pii")
        row = {"id": "1", "name": "Test", "email": "test@example.com", "phone": "123456"}
        encrypted_row = self.service.encrypt_row("users", row)
        assert encrypted_row["name"] == "Test"
        assert encrypted_row["email"] != "test@example.com"

    def test_decrypt_row(self):
        self.service.register_sensitive_fields("users", ["email"], "pii")
        row = {"id": "1", "email": "test@example.com"}
        encrypted_row = self.service.encrypt_row("users", row)
        decrypted_row = self.service.decrypt_row("users", encrypted_row)
        assert decrypted_row["email"] == "test@example.com"

    def test_rotate_key(self):
        original = self.service.encrypt_field("test data", "default")
        new_key_id = self.service.rotate_key("default")
        assert new_key_id != "default"
        decrypted = self.service.decrypt_field(original)
        assert decrypted == "test data"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.service.encrypt_field("test", "nonexistent_key")


class TestMinIOEncryption:
    def test_default_sse_s3(self):
        service = MinIOEncryptionService()
        headers = service.get_encryption_headers("test-bucket")
        assert headers.get("x-amz-server-side-encryption") == "AES256"

    def test_sse_kms(self):
        config = MinIOSSEConfig(sse_type="SSE-KMS", kms_key_id="arn:aws:kms:us-east-1:123:key/abc")
        service = MinIOEncryptionService(config)
        headers = service.get_encryption_headers("test-bucket")
        assert headers.get("x-amz-server-side-encryption") == "aws:kms"
        assert "kms-key-id" in headers.get("x-amz-server-side-encryption-aws-kms-key-id", "").lower() or headers.get("x-amz-server-side-encryption-aws-kms-key-id") == "arn:aws:kms:us-east-1:123:key/abc"

    def test_configure_bucket_encryption(self):
        service = MinIOEncryptionService()
        config = MinIOSSEConfig(sse_type="SSE-KMS", kms_key_id="key-123")
        service.configure_bucket_encryption("my-bucket", config)
        headers = service.get_encryption_headers("my-bucket")
        assert headers.get("x-amz-server-side-encryption") == "aws:kms"


class TestBackupEncryption:
    def test_encrypt_decrypt_backup(self):
        service = BackupEncryptionService(passphrase="backup-secret")
        original = b"This is backup data with important content"
        encrypted = service.encrypt_backup(original)
        assert encrypted != original
        decrypted = service.decrypt_backup(encrypted)
        assert decrypted == original

    def test_different_passphrase_fails(self):
        service1 = BackupEncryptionService(passphrase="secret1")
        service2 = BackupEncryptionService(passphrase="secret2")
        encrypted = service1.encrypt_backup(b"test data")
        with pytest.raises(Exception):
            service2.decrypt_backup(encrypted)


class TestSessionSecurity:
    def setup_method(self):
        self.config = SessionConfig(
            absolute_timeout_minutes=480,
            idle_timeout_minutes=30,
            max_concurrent_sessions=3,
        )
        self.service = SessionSecurityService(self.config)

    def test_create_session(self):
        session = self.service.create_session("u1", "t1", ip_address="192.168.1.1")
        assert session.user_id == "u1"
        assert session.tenant_id == "t1"
        assert session.status == SessionStatus.ACTIVE

    def test_validate_active_session(self):
        session = self.service.create_session("u1", "t1")
        validated = self.service.validate_session(session.session_id)
        assert validated is not None
        assert validated.status == SessionStatus.ACTIVE

    def test_terminate_session(self):
        session = self.service.create_session("u1", "t1")
        result = self.service.terminate_session(session.session_id, reason="user_logout")
        assert result is True
        validated = self.service.validate_session(session.session_id)
        assert validated is None

    def test_force_logout_user(self):
        self.service.create_session("u1", "t1")
        self.service.create_session("u1", "t1")
        count = self.service.force_logout_user("u1", admin_id="admin1")
        assert count == 2

    def test_concurrent_session_limit(self):
        for i in range(5):
            self.service.create_session("u1", "t1")
        sessions = self.service.get_user_sessions("u1")
        assert len(sessions) <= self.config.max_concurrent_sessions

    def test_suspicious_activity_check(self):
        self.service.create_session("u1", "t1", ip_address="1.1.1.1")
        self.service.create_session("u1", "t1", ip_address="2.2.2.2")
        self.service.create_session("u1", "t1", ip_address="3.3.3.3")
        self.service.create_session("u1", "t1", ip_address="4.4.4.4")
        result = self.service.check_suspicious_activity("u1", "5.5.5.5")
        assert result["suspicious"] is True
        assert result["new_device_detected"] is True


class TestRequestSigning:
    def setup_method(self):
        self.service = RequestSigningService(signing_secret="test-secret")

    def test_sign_and_verify(self):
        signed = self.service.sign_request("POST", "/api/v1/projects", '{"name":"test"}', "t1", "u1")
        result = self.service.verify_request("POST", "/api/v1/projects", '{"name":"test"}', signed)
        assert result["valid"] is True

    def test_tampered_body_fails(self):
        signed = self.service.sign_request("POST", "/api/v1/projects", '{"name":"test"}', "t1", "u1")
        result = self.service.verify_request("POST", "/api/v1/projects", '{"name":"tampered"}', signed)
        assert result["valid"] is False

    def test_nonce_reuse_fails(self):
        signed = self.service.sign_request("GET", "/api/v1/projects", "", "t1", "u1")
        self.service.verify_request("GET", "/api/v1/projects", "", signed)
        result = self.service.verify_request("GET", "/api/v1/projects", "", signed)
        assert result["valid"] is False
        assert result["reason"] == "nonce_reused"


class TestConfirmationService:
    def setup_method(self):
        self.service = ConfirmationService()

    def test_request_and_confirm(self):
        token = self.service.request_confirmation("delete", "project", "p1", "u1", "t1")
        result = self.service.confirm(token.token_id, "u1")
        assert result["confirmed"] is True
        assert result["operation"] == "delete"

    def test_wrong_user_fails(self):
        token = self.service.request_confirmation("delete", "project", "p1", "u1", "t1")
        result = self.service.confirm(token.token_id, "u2")
        assert result["confirmed"] is False
        assert result["reason"] == "user_mismatch"

    def test_is_sensitive_operation(self):
        assert self.service.is_sensitive_operation("delete") is True
        assert self.service.is_sensitive_operation("freeze_baseline") is True
        assert self.service.is_sensitive_operation("read") is False


class TestRateLimiter:
    def setup_method(self):
        self.limiter = RateLimiter()

    def test_allow_within_limit(self):
        result = self.limiter.check_rate("per_user", "u1")
        assert result["allowed"] is True

    def test_check_request(self):
        result = self.limiter.check_request("t1", "u1", "/api/v1/projects", "GET")
        assert result["allowed"] is True

    def test_custom_rule(self):
        self.limiter.add_rule(RateLimitRule(name="strict", max_requests=2, window_seconds=60))
        self.limiter.check_rate("strict", "u1")
        self.limiter.check_rate("strict", "u1")
        result = self.limiter.check_rate("strict", "u1")
        assert result["allowed"] is False