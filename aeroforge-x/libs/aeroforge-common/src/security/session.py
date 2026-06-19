from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclass
class SessionConfig:
    absolute_timeout_minutes: int = 480
    idle_timeout_minutes: int = 30
    max_concurrent_sessions: int = 5
    remember_me_timeout_minutes: int = 43200
    enforce_single_device: bool = False


@dataclass
class SessionInfo:
    session_id: str
    user_id: str
    tenant_id: str
    ip_address: str
    user_agent: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    terminated_by: str | None = None
    terminated_reason: str | None = None
    remember_me: bool = False
    device_fingerprint: str = ""

    def is_expired(self, config: SessionConfig) -> bool:
        now = datetime.now(timezone.utc)
        if self.status in (SessionStatus.TERMINATED, SessionStatus.EXPIRED):
            return True

        absolute_limit = self.created_at + timedelta(minutes=config.absolute_timeout_minutes)
        if self.remember_me:
            absolute_limit = self.created_at + timedelta(minutes=config.remember_me_timeout_minutes)
        if now > absolute_limit:
            return True

        idle_limit = self.last_activity + timedelta(minutes=config.idle_timeout_minutes)
        if now > idle_limit:
            return True

        return False

    def touch(self) -> None:
        self.last_activity = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "terminated_by": self.terminated_by,
            "terminated_reason": self.terminated_reason,
            "remember_me": self.remember_me,
            "device_fingerprint": self.device_fingerprint,
        }


class SessionSecurityService:
    def __init__(self, config: SessionConfig | None = None) -> None:
        self.config = config or SessionConfig()
        self._sessions: dict[str, SessionInfo] = {}
        self._user_sessions: dict[str, list[str]] = {}

    def create_session(
        self,
        user_id: str,
        tenant_id: str,
        ip_address: str = "",
        user_agent: str = "",
        remember_me: bool = False,
        device_fingerprint: str = "",
    ) -> SessionInfo:
        self._enforce_concurrent_limit(user_id)

        session_id = secrets.token_urlsafe(32)
        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            remember_me=remember_me,
            device_fingerprint=device_fingerprint,
        )

        if remember_me:
            session.expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.remember_me_timeout_minutes
            )
        else:
            session.expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.absolute_timeout_minutes
            )

        self._sessions[session_id] = session
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)

        logger.info("Session created: user=%s session=%s", user_id, session_id[:8])
        return session

    def validate_session(self, session_id: str) -> SessionInfo | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired(self.config):
            self._expire_session(session_id)
            return None

        session.touch()
        return session

    def terminate_session(self, session_id: str, terminated_by: str = "", reason: str = "") -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False

        session.status = SessionStatus.TERMINATED
        session.terminated_by = terminated_by
        session.terminated_reason = reason
        logger.info("Session terminated: session=%s by=%s reason=%s", session_id[:8], terminated_by, reason)
        return True

    def force_logout_user(self, user_id: str, admin_id: str = "", reason: str = "admin_force_logout") -> int:
        session_ids = self._user_sessions.get(user_id, [])
        count = 0
        for sid in session_ids:
            session = self._sessions.get(sid)
            if session and session.status == SessionStatus.ACTIVE:
                session.status = SessionStatus.TERMINATED
                session.terminated_by = admin_id
                session.terminated_reason = reason
                count += 1
        logger.info("Force logout user=%s sessions=%d by=%s", user_id, count, admin_id)
        return count

    def get_user_sessions(self, user_id: str) -> list[SessionInfo]:
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        for sid in session_ids:
            session = self._sessions.get(sid)
            if session and session.status == SessionStatus.ACTIVE:
                if not session.is_expired(self.config):
                    sessions.append(session)
                else:
                    self._expire_session(sid)
        return sessions

    def get_active_session_count(self, user_id: str) -> int:
        return len(self.get_user_sessions(user_id))

    def cleanup_expired_sessions(self) -> int:
        expired = []
        for sid, session in self._sessions.items():
            if session.is_expired(self.config) or session.status in (SessionStatus.EXPIRED, SessionStatus.TERMINATED):
                expired.append(sid)

        for sid in expired:
            self._expire_session(sid)

        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
        return len(expired)

    def check_suspicious_activity(self, user_id: str, ip_address: str) -> dict[str, Any]:
        sessions = self.get_user_sessions(user_id)
        active_ips = set(s.ip_address for s in sessions if s.ip_address)
        suspicious = len(active_ips) > 3
        new_device = ip_address not in active_ips and len(active_ips) > 0

        return {
            "user_id": user_id,
            "suspicious": suspicious,
            "new_device_detected": new_device,
            "active_ip_count": len(active_ips),
            "active_session_count": len(sessions),
            "recommendation": "require_reauth" if suspicious else "none",
        }

    def _enforce_concurrent_limit(self, user_id: str) -> None:
        sessions = self.get_user_sessions(user_id)
        while len(sessions) >= self.config.max_concurrent_sessions:
            oldest = min(sessions, key=lambda s: s.created_at)
            self.terminate_session(oldest.session_id, reason="concurrent_limit_exceeded")
            sessions = self.get_user_sessions(user_id)

    def _expire_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session and session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.EXPIRED