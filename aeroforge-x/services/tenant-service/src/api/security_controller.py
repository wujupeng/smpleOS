from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse
from aeroforge_common.security.api_security import (
    ConfirmationService,
    RateLimiter,
    RequestSigningService,
)
from aeroforge_common.security.encryption import (
    BackupEncryptionConfig,
    BackupEncryptionService,
    ColumnEncryptionService,
    MinIOEncryptionService,
    MinIOSSEConfig,
)
from aeroforge_common.security.session import (
    SessionConfig,
    SessionSecurityService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/security", tags=["Security"])

_encryption_service = ColumnEncryptionService()
_minio_encryption = MinIOEncryptionService()
_backup_encryption = BackupEncryptionService()
_session_service = SessionSecurityService()
_signing_service = RequestSigningService()
_confirmation_service = ConfirmationService()
_rate_limiter = RateLimiter()


# --- Encryption APIs ---

class EncryptFieldRequest(BaseModel):
    plaintext: str = Field(..., min_length=1)
    key_id: str = "default"


class DecryptFieldRequest(BaseModel):
    encrypted_value: str = Field(..., min_length=1)


class RegisterSensitiveFieldsRequest(BaseModel):
    table: str = Field(..., min_length=1)
    fields: list[str]
    key_id: str = "default"


@router.post("/encryption/encrypt", response_model=ApiResponse[dict])
async def encrypt_field(body: EncryptFieldRequest):
    try:
        encrypted = _encryption_service.encrypt_field(body.plaintext, body.key_id)
        return ApiResponse(data={"encrypted": encrypted})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/encryption/decrypt", response_model=ApiResponse[dict])
async def decrypt_field(body: DecryptFieldRequest):
    try:
        decrypted = _encryption_service.decrypt_field(body.encrypted_value)
        return ApiResponse(data={"decrypted": decrypted})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/encryption/register-fields", response_model=ApiResponse[dict])
async def register_sensitive_fields(body: RegisterSensitiveFieldsRequest):
    _encryption_service.register_sensitive_fields(body.table, body.fields, body.key_id)
    return ApiResponse(data={"registered": True, "table": body.table, "fields": body.fields})


@router.post("/encryption/rotate-key/{key_id}", response_model=ApiResponse[dict])
async def rotate_encryption_key(key_id: str):
    try:
        new_key_id = _encryption_service.rotate_key(key_id)
        return ApiResponse(data={"old_key_id": key_id, "new_key_id": new_key_id})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- MinIO SSE APIs ---

class ConfigureBucketEncryptionRequest(BaseModel):
    bucket: str = Field(..., min_length=1)
    sse_type: str = Field(default="SSE-S3", description="SSE-S3 | SSE-KMS")
    kms_key_id: str | None = None


@router.post("/minio/configure-encryption", response_model=ApiResponse[dict])
async def configure_bucket_encryption(body: ConfigureBucketEncryptionRequest):
    config = MinIOSSEConfig(sse_type=body.sse_type, kms_key_id=body.kms_key_id)
    _minio_encryption.configure_bucket_encryption(body.bucket, config)
    return ApiResponse(data={"bucket": body.bucket, "sse_type": body.sse_type})


@router.get("/minio/encryption-headers/{bucket}", response_model=ApiResponse[dict])
async def get_minio_encryption_headers(bucket: str):
    headers = _minio_encryption.get_encryption_headers(bucket)
    return ApiResponse(data={"bucket": bucket, "headers": headers})


# --- Session APIs ---

class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    ip_address: str = ""
    user_agent: str = ""
    remember_me: bool = False
    device_fingerprint: str = ""


class ForceLogoutRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    admin_id: str = ""
    reason: str = "admin_force_logout"


@router.post("/sessions", response_model=ApiResponse[dict])
async def create_session(body: CreateSessionRequest):
    session = _session_service.create_session(
        user_id=body.user_id,
        tenant_id=body.tenant_id,
        ip_address=body.ip_address,
        user_agent=body.user_agent,
        remember_me=body.remember_me,
        device_fingerprint=body.device_fingerprint,
    )
    return ApiResponse(data=session.to_dict())


@router.get("/sessions/{session_id}", response_model=ApiResponse[dict])
async def validate_session(session_id: str):
    session = _session_service.validate_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return ApiResponse(data=session.to_dict())


@router.delete("/sessions/{session_id}", response_model=ApiResponse[dict])
async def terminate_session(session_id: str, terminated_by: str = "", reason: str = "user_logout"):
    success = _session_service.terminate_session(session_id, terminated_by, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return ApiResponse(data={"terminated": True, "session_id": session_id})


@router.post("/sessions/force-logout", response_model=ApiResponse[dict])
async def force_logout_user(body: ForceLogoutRequest):
    count = _session_service.force_logout_user(body.user_id, body.admin_id, body.reason)
    return ApiResponse(data={"user_id": body.user_id, "sessions_terminated": count})


@router.get("/sessions/user/{user_id}", response_model=ApiResponse[dict])
async def get_user_sessions(user_id: str):
    sessions = _session_service.get_user_sessions(user_id)
    return ApiResponse(data={
        "user_id": user_id,
        "active_count": len(sessions),
        "sessions": [s.to_dict() for s in sessions],
    })


@router.get("/sessions/{user_id}/suspicious-check", response_model=ApiResponse[dict])
async def check_suspicious_activity(user_id: str, ip_address: str = ""):
    result = _session_service.check_suspicious_activity(user_id, ip_address)
    return ApiResponse(data=result)


# --- Request Signing APIs ---

class SignRequestModel(BaseModel):
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    body: str = ""
    tenant_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class VerifyRequestModel(BaseModel):
    method: str
    path: str
    body: str = ""
    timestamp: int
    nonce: str
    signature: str
    tenant_id: str
    user_id: str


@router.post("/signing/sign", response_model=ApiResponse[dict])
async def sign_request(body: SignRequestModel):
    from aeroforge_common.security.api_security import RequestSignature
    signed = _signing_service.sign_request(
        method=body.method,
        path=body.path,
        body=body.body,
        tenant_id=body.tenant_id,
        user_id=body.user_id,
    )
    return ApiResponse(data=signed.to_headers())


@router.post("/signing/verify", response_model=ApiResponse[dict])
async def verify_request(body: VerifyRequestModel):
    from aeroforge_common.security.api_security import RequestSignature
    signed = RequestSignature(
        timestamp=body.timestamp,
        nonce=body.nonce,
        signature=body.signature,
        tenant_id=body.tenant_id,
        user_id=body.user_id,
    )
    result = _signing_service.verify_request(
        method=body.method,
        path=body.path,
        body=body.body,
        signed=signed,
    )
    return ApiResponse(data=result)


# --- Confirmation APIs ---

class RequestConfirmationModel(BaseModel):
    operation: str = Field(..., min_length=1)
    resource_type: str = Field(..., min_length=1)
    resource_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)


class ConfirmOperationModel(BaseModel):
    token_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


@router.post("/confirmation/request", response_model=ApiResponse[dict])
async def request_confirmation(body: RequestConfirmationModel):
    token = _confirmation_service.request_confirmation(
        operation=body.operation,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        user_id=body.user_id,
        tenant_id=body.tenant_id,
    )
    return ApiResponse(data=token.to_dict())


@router.post("/confirmation/confirm", response_model=ApiResponse[dict])
async def confirm_operation(body: ConfirmOperationModel):
    result = _confirmation_service.confirm(body.token_id, body.user_id)
    if not result.get("confirmed"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Confirmation failed"))
    return ApiResponse(data=result)


@router.get("/confirmation/sensitive-operations", response_model=ApiResponse[dict])
async def list_sensitive_operations():
    return ApiResponse(data={
        "operations": list(ConfirmationService.SENSITIVE_OPERATIONS),
    })


# --- Rate Limiting APIs ---

class CheckRateLimitModel(BaseModel):
    rule_name: str = Field(..., min_length=1)
    identifier: str = Field(..., min_length=1)


class CheckRequestRateModel(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    api_path: str = Field(..., min_length=1)
    method: str = "GET"


@router.post("/rate-limit/check", response_model=ApiResponse[dict])
async def check_rate_limit(body: CheckRateLimitModel):
    result = _rate_limiter.check_rate(body.rule_name, body.identifier)
    return ApiResponse(data=result)


@router.post("/rate-limit/check-request", response_model=ApiResponse[dict])
async def check_request_rate(body: CheckRequestRateModel):
    result = _rate_limiter.check_request(
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        api_path=body.api_path,
        method=body.method,
    )
    return ApiResponse(data=result)