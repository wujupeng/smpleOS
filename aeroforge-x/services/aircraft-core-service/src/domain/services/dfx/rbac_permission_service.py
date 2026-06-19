"""AeroForge-X v6.0 RBACPermissionService

Role-Based Access Control for v6.0 operations:
- Configuration baseline operations (ConfigAdmin)
- Certification evidence management (CertEngineer)
- Supplier data access (SupplierQualityEngineer)
- Shop floor control commands (ProductionEngineer + SafetyEngineer)

REQ-DFX-V6-005
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    CONFIG_ADMIN = "ConfigAdmin"
    CERT_ENGINEER = "CertEngineer"
    SUPPLIER_QUALITY_ENGINEER = "SupplierQualityEngineer"
    PRODUCTION_ENGINEER = "ProductionEngineer"
    SAFETY_ENGINEER = "SafetyEngineer"
    VIEWER = "Viewer"


class Permission(str, Enum):
    BASELINE_CREATE = "baseline:create"
    BASELINE_MODIFY = "baseline:modify"
    BASELINE_VIEW = "baseline:view"
    EVIDENCE_MANAGE = "evidence:manage"
    EVIDENCE_VIEW = "evidence:view"
    SUPPLIER_DATA_ACCESS = "supplier:data_access"
    SUPPLIER_DATA_VIEW = "supplier:data_view"
    SHOP_FLOOR_COMMAND = "shop_floor:command"
    SHOP_FLOOR_VIEW = "shop_floor:view"
    CONFIG_CHANGE_APPROVE = "config_change:approve"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.CONFIG_ADMIN: [
        Permission.BASELINE_CREATE,
        Permission.BASELINE_MODIFY,
        Permission.BASELINE_VIEW,
        Permission.CONFIG_CHANGE_APPROVE,
    ],
    Role.CERT_ENGINEER: [
        Permission.EVIDENCE_MANAGE,
        Permission.EVIDENCE_VIEW,
        Permission.BASELINE_VIEW,
    ],
    Role.SUPPLIER_QUALITY_ENGINEER: [
        Permission.SUPPLIER_DATA_ACCESS,
        Permission.SUPPLIER_DATA_VIEW,
        Permission.EVIDENCE_VIEW,
    ],
    Role.PRODUCTION_ENGINEER: [
        Permission.SHOP_FLOOR_COMMAND,
        Permission.SHOP_FLOOR_VIEW,
    ],
    Role.SAFETY_ENGINEER: [
        Permission.SHOP_FLOOR_COMMAND,
        Permission.SHOP_FLOOR_VIEW,
    ],
    Role.VIEWER: [
        Permission.BASELINE_VIEW,
        Permission.EVIDENCE_VIEW,
        Permission.SUPPLIER_DATA_VIEW,
        Permission.SHOP_FLOOR_VIEW,
    ],
}

DUAL_AUTHORIZATION_PERMISSIONS = {Permission.SHOP_FLOOR_COMMAND}
DUAL_AUTHORIZATION_ROLES = {Role.PRODUCTION_ENGINEER, Role.SAFETY_ENGINEER}


@dataclass
class User:
    user_id: str
    username: str
    roles: list[Role] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "roles": [r.value for r in self.roles],
        }


@dataclass
class AccessCheckResult:
    user_id: str
    permission: Permission
    granted: bool
    reason: str = ""
    requires_dual_auth: bool = False
    dual_auth_satisfied: bool = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "permission": self.permission.value,
            "granted": self.granted,
            "reason": self.reason,
            "requires_dual_auth": self.requires_dual_auth,
            "dual_auth_satisfied": self.dual_auth_satisfied,
        }


@dataclass
class DualAuthorizationSession:
    session_id: str
    permission: Permission
    resource_id: str
    production_engineer_id: str = ""
    safety_engineer_id: str = ""
    production_authorized: bool = False
    safety_authorized: bool = False
    fully_authorized: bool = False

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "permission": self.permission.value,
            "resource_id": self.resource_id,
            "production_engineer_id": self.production_engineer_id,
            "safety_engineer_id": self.safety_engineer_id,
            "production_authorized": self.production_authorized,
            "safety_authorized": self.safety_authorized,
            "fully_authorized": self.fully_authorized,
        }


class RBACPermissionService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._users: dict[str, User] = {}
        self._dual_auth_sessions: dict[str, DualAuthorizationSession] = {}

    def registerUser(self, user: User) -> User:
        self._users[user.user_id] = user
        return user

    def checkPermission(self, user_id: str, permission: Permission) -> AccessCheckResult:
        user = self._users.get(user_id)
        if user is None:
            return AccessCheckResult(
                user_id=user_id,
                permission=permission,
                granted=False,
                reason="User not found",
            )

        user_permissions = set()
        for role in user.roles:
            user_permissions.update(ROLE_PERMISSIONS.get(role, []))

        if permission not in user_permissions:
            return AccessCheckResult(
                user_id=user_id,
                permission=permission,
                granted=False,
                reason=f"User lacks permission: {permission.value}",
            )

        requires_dual = permission in DUAL_AUTHORIZATION_PERMISSIONS
        if requires_dual:
            has_production = Role.PRODUCTION_ENGINEER in user.roles
            has_safety = Role.SAFETY_ENGINEER in user.roles
            dual_satisfied = has_production and has_safety

            return AccessCheckResult(
                user_id=user_id,
                permission=permission,
                granted=False,
                reason="Dual authorization required",
                requires_dual_auth=True,
                dual_auth_satisfied=dual_satisfied,
            )

        return AccessCheckResult(
            user_id=user_id,
            permission=permission,
            granted=True,
        )

    def checkDualAuthorization(
        self, production_user_id: str, safety_user_id: str, permission: Permission
    ) -> AccessCheckResult:
        prod_user = self._users.get(production_user_id)
        safety_user = self._users.get(safety_user_id)

        if prod_user is None or safety_user is None:
            return AccessCheckResult(
                user_id=f"{production_user_id}+{safety_user_id}",
                permission=permission,
                granted=False,
                reason="One or both users not found",
                requires_dual_auth=True,
                dual_auth_satisfied=False,
            )

        prod_has_role = Role.PRODUCTION_ENGINEER in prod_user.roles
        safety_has_role = Role.SAFETY_ENGINEER in safety_user.roles

        if not prod_has_role or not safety_has_role:
            return AccessCheckResult(
                user_id=f"{production_user_id}+{safety_user_id}",
                permission=permission,
                granted=False,
                reason="Dual authorization requires ProductionEngineer + SafetyEngineer",
                requires_dual_auth=True,
                dual_auth_satisfied=False,
            )

        return AccessCheckResult(
            user_id=f"{production_user_id}+{safety_user_id}",
            permission=permission,
            granted=True,
            requires_dual_auth=True,
            dual_auth_satisfied=True,
        )

    def createDualAuthSession(
        self, permission: Permission, resource_id: str
    ) -> DualAuthorizationSession:
        session = DualAuthorizationSession(
            session_id=f"DA-{uuid.uuid4().hex[:8]}",
            permission=permission,
            resource_id=resource_id,
        )
        self._dual_auth_sessions[session.session_id] = session
        return session

    def authorizeDualAuthSession(
        self,
        session_id: str,
        user_id: str,
        role: Role,
    ) -> DualAuthorizationSession:
        session = self._dual_auth_sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if role == Role.PRODUCTION_ENGINEER:
            session.production_engineer_id = user_id
            session.production_authorized = True
        elif role == Role.SAFETY_ENGINEER:
            session.safety_engineer_id = user_id
            session.safety_authorized = True

        session.fully_authorized = (
            session.production_authorized and session.safety_authorized
        )
        return session

    def getUser(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def getUserPermissions(self, user_id: str) -> list[Permission]:
        user = self._users.get(user_id)
        if user is None:
            return []
        perms = set()
        for role in user.roles:
            perms.update(ROLE_PERMISSIONS.get(role, []))
        return list(perms)