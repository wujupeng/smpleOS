from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestSignature:
    timestamp: int
    nonce: str
    signature: str
    tenant_id: str
    user_id: str

    def to_headers(self) -> dict[str, str]:
        return {
            "X-AeroForge-Timestamp": str(self.timestamp),
            "X-AeroForge-Nonce": self.nonce,
            "X-AForge-Signature": self.signature,
            "X-AeroForge-TenantId": self.tenant_id,
            "X-AeroForge-UserId": self.user_id,
        }

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> RequestSignature | None:
        try:
            return cls(
                timestamp=int(headers.get("X-AeroForge-Timestamp", "0")),
                nonce=headers.get("X-AeroForge-Nonce", ""),
                signature=headers.get("X-AForge-Signature", ""),
                tenant_id=headers.get("X-AeroForge-TenantId", ""),
                user_id=headers.get("X-AeroForge-UserId", ""),
            )
        except (ValueError, TypeError):
            return None


class RequestSigningService:
    def __init__(self, signing_secret: str | None = None) -> None:
        self._secret = signing_secret or secrets.token_hex(32)
        self._nonce_cache: dict[str, float] = {}
        self._max_nonce_age = 300

    def sign_request(
        self,
        method: str,
        path: str,
        body: str,
        tenant_id: str,
        user_id: str,
    ) -> RequestSignature:
        timestamp = int(time.time())
        nonce = secrets.token_urlsafe(16)

        payload = f"{method.upper()}|{path}|{timestamp}|{nonce}|{tenant_id}|{user_id}|{body}"
        signature = hmac.new(
            self._secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return RequestSignature(
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    def verify_request(
        self,
        method: str,
        path: str,
        body: str,
        signed: RequestSignature,
        max_skew_seconds: int = 300,
    ) -> dict[str, Any]:
        now = int(time.time())
        if abs(now - signed.timestamp) > max_skew_seconds:
            return {"valid": False, "reason": "timestamp_skew_exceeded"}

        if signed.nonce in self._nonce_cache:
            return {"valid": False, "reason": "nonce_reused"}

        payload = f"{method.upper()}|{path}|{signed.timestamp}|{signed.nonce}|{signed.tenant_id}|{signed.user_id}|{body}"
        expected = hmac.new(
            self._secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signed.signature):
            return {"valid": False, "reason": "signature_mismatch"}

        self._nonce_cache[signed.nonce] = now
        self._cleanup_old_nonces(now)

        return {"valid": True, "tenant_id": signed.tenant_id, "user_id": signed.user_id}

    def _cleanup_old_nonces(self, now: int) -> None:
        expired = [n for n, t in self._nonce_cache.items() if now - t > self._max_nonce_age]
        for n in expired:
            del self._nonce_cache[n]


@dataclass
class ConfirmationToken:
    token_id: str
    operation: str
    resource_type: str
    resource_id: str
    user_id: str
    tenant_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    confirmed: bool = False

    def __post_init__(self) -> None:
        if self.expires_at is None:
            self.expires_at = datetime.now(timezone.utc) + __import__("datetime").timedelta(minutes=5)

    def is_valid(self) -> bool:
        if self.confirmed:
            return False
        now = datetime.now(timezone.utc)
        return now <= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "operation": self.operation,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class ConfirmationService:
    SENSITIVE_OPERATIONS = {
        "delete", "freeze_baseline", "suspend_tenant", "force_logout",
        "reset_password", "change_role", "export_sensitive_data",
        "approve_critical_change", "revoke_certificate",
    }

    def __init__(self) -> None:
        self._tokens: dict[str, ConfirmationToken] = {}

    def request_confirmation(
        self,
        operation: str,
        resource_type: str,
        resource_id: str,
        user_id: str,
        tenant_id: str,
    ) -> ConfirmationToken:
        token_id = secrets.token_urlsafe(24)
        token = ConfirmationToken(
            token_id=token_id,
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        self._tokens[token_id] = token
        logger.info("Confirmation requested: op=%s resource=%s/%s user=%s", operation, resource_type, resource_id, user_id)
        return token

    def confirm(self, token_id: str, user_id: str) -> dict[str, Any]:
        token = self._tokens.get(token_id)
        if token is None:
            return {"confirmed": False, "reason": "token_not_found"}

        if token.user_id != user_id:
            return {"confirmed": False, "reason": "user_mismatch"}

        if not token.is_valid():
            return {"confirmed": False, "reason": "token_expired"}

        token.confirmed = True
        logger.info("Operation confirmed: op=%s resource=%s/%s", token.operation, token.resource_type, token.resource_id)
        return {
            "confirmed": True,
            "operation": token.operation,
            "resource_type": token.resource_type,
            "resource_id": token.resource_id,
        }

    def is_sensitive_operation(self, operation: str) -> bool:
        return operation.lower() in self.SENSITIVE_OPERATIONS

    def cleanup_expired(self) -> int:
        expired = [tid for tid, t in self._tokens.items() if not t.is_valid()]
        for tid in expired:
            del self._tokens[tid]
        return len(expired)


@dataclass
class RateLimitRule:
    name: str
    max_requests: int
    window_seconds: int
    key_prefix: str = ""
    burst_allowance: int = 0


@dataclass
class RateLimitEntry:
    key: str
    tokens: float
    last_refill: float
    max_tokens: float
    refill_rate: float

    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, RateLimitEntry] = {}
        self._rules: dict[str, RateLimitRule] = {}
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self.add_rule(RateLimitRule(name="global", max_requests=1000, window_seconds=60, key_prefix="global"))
        self.add_rule(RateLimitRule(name="per_tenant", max_requests=500, window_seconds=60, key_prefix="tenant"))
        self.add_rule(RateLimitRule(name="per_user", max_requests=200, window_seconds=60, key_prefix="user"))
        self.add_rule(RateLimitRule(name="login", max_requests=10, window_seconds=60, key_prefix="login"))
        self.add_rule(RateLimitRule(name="export", max_requests=5, window_seconds=60, key_prefix="export"))
        self.add_rule(RateLimitRule(name="sensitive", max_requests=20, window_seconds=60, key_prefix="sensitive"))

    def add_rule(self, rule: RateLimitRule) -> None:
        self._rules[rule.name] = rule

    def check_rate(
        self,
        rule_name: str,
        identifier: str,
        tokens: int = 1,
    ) -> dict[str, Any]:
        rule = self._rules.get(rule_name)
        if rule is None:
            return {"allowed": True, "reason": "no_rule"}

        key = f"{rule.key_prefix}:{identifier}"
        entry = self._get_or_create_entry(key, rule)

        allowed = entry.consume(tokens)
        return {
            "allowed": allowed,
            "rule": rule_name,
            "remaining": int(entry.tokens),
            "limit": rule.max_requests,
            "reset_at": int(entry.last_refill + rule.window_seconds),
        }

    def check_request(
        self,
        tenant_id: str,
        user_id: str,
        api_path: str,
        method: str = "GET",
    ) -> dict[str, Any]:
        results = []

        global_check = self.check_rate("global", "all")
        results.append(global_check)

        tenant_check = self.check_rate("per_tenant", tenant_id)
        results.append(tenant_check)

        user_check = self.check_rate("per_user", user_id)
        results.append(user_check)

        if "login" in api_path.lower():
            login_check = self.check_rate("login", user_id)
            results.append(login_check)

        if "export" in api_path.lower():
            export_check = self.check_rate("export", user_id)
            results.append(export_check)

        if method.upper() in ("DELETE", "PUT") and any(kw in api_path.lower() for kw in ("baseline", "tenant", "role")):
            sensitive_check = self.check_rate("sensitive", user_id)
            results.append(sensitive_check)

        blocked = [r for r in results if not r.get("allowed", True)]
        if blocked:
            return blocked[0]

        return {"allowed": True, "checks": len(results)}

    def _get_or_create_entry(self, key: str, rule: RateLimitRule) -> RateLimitEntry:
        if key not in self._entries:
            refill_rate = rule.max_requests / rule.window_seconds
            self._entries[key] = RateLimitEntry(
                key=key,
                tokens=float(rule.max_requests + rule.burst_allowance),
                last_refill=time.time(),
                max_tokens=float(rule.max_requests + rule.burst_allowance),
                refill_rate=refill_rate,
            )
        return self._entries[key]

    def reset(self, key: str | None = None) -> None:
        if key:
            self._entries.pop(key, None)
        else:
            self._entries.clear()