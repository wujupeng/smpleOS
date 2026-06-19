from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import AeroForgeRole, ROLE_PERMISSIONS

logger = logging.getLogger(__name__)


class Resource(str, Enum):
    SPEC = "specs"
    MODEL = "models"
    RULE = "rules"
    BASELINE = "baselines"
    CHANGE = "changes"
    EBOM = "ebom"
    MBOM = "mbom"
    SBOM = "sbom"
    WORK_ORDER = "work_orders"
    STATION = "stations"
    INSPECTION = "inspections"
    CAPA = "capa"
    TWIN = "twins"
    CFD = "cfd"
    FEA = "fea"
    FLUTTER = "flutter"
    THERMAL = "thermal"
    MULTIPHYSICS = "multiphysics"
    PROCESS_ROUTE = "process_routes"
    TENANT = "tenants"
    PROJECT = "projects"
    AI_ENGINE = "ai_engine"
    SUPPLIER = "suppliers"
    REPORT = "reports"


class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    SUBMIT = "submit"
    EXECUTE = "execute"
    VERIFY = "verify"
    FREEZE = "freeze"
    DISPATCH = "dispatch"
    SYNC = "sync"
    EXPORT = "export"


class Scope(str, Enum):
    OWN = "own"
    PROJECT = "project"
    TENANT = "tenant"
    SYSTEM = "system"


@dataclass
class Permission:
    resource: str
    action: str
    scope: Scope = Scope.TENANT

    def __hash__(self) -> int:
        return hash((self.resource, self.action, self.scope))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return False
        return self.resource == other.resource and self.action == other.action and self.scope == other.scope

    def matches(self, resource: str, action: str, scope: Scope | None = None) -> bool:
        if self.resource != resource or self.action != action:
            return False
        if scope and self.scope != Scope.SYSTEM:
            scope_order = {Scope.OWN: 1, Scope.PROJECT: 2, Scope.TENANT: 3, Scope.SYSTEM: 4}
            return scope_order.get(self.scope, 0) >= scope_order.get(scope, 0)
        return True

    def to_dict(self) -> dict[str, str]:
        return {"resource": self.resource, "action": self.action, "scope": self.scope.value}


@dataclass
class Policy:
    policy_id: str
    name: str
    description: str
    conditions: dict[str, Any] = field(default_factory=dict)
    effect: str = "allow"

    def evaluate(self, context: dict[str, Any]) -> bool:
        for key, expected in self.conditions.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "effect": self.effect,
        }


EXTENDED_ROLES: dict[str, dict[str, Any]] = {
    **ROLE_PERMISSIONS,
    AeroForgeRole.CHIEF_DESIGNER.value: {
        **ROLE_PERMISSIONS.get(AeroForgeRole.CHIEF_DESIGNER.value, []),
        "tenant_admin": False,
    },
    "tenant_admin": [
        "tenants:create", "tenants:read", "tenants:update",
        "tenants:suspend", "tenants:activate",
        "projects:create", "projects:read", "projects:update", "projects:delete",
        "tenant-users:create", "tenant-users:read", "tenant-users:update", "tenant-users:delete",
    ],
    "data_analyst": [
        "reports:create", "reports:read", "reports:export",
        "spc:read", "spc:export",
        "analytics:read",
    ],
    "supply_chain_manager": [
        "suppliers:create", "suppliers:read", "suppliers:update",
        "purchase-orders:create", "purchase-orders:read", "purchase-orders:update",
        "inventory:read", "inventory:update",
    ],
}


ROLE_PERMISSIONS_MAP: dict[str, list[Permission]] = {}

for role_name, perms in EXTENDED_ROLES.items():
    if isinstance(perms, list):
        permission_list = []
        for p in perms:
            parts = p.split(":")
            if len(parts) == 2:
                permission_list.append(Permission(resource=parts[0], action=parts[1], scope=Scope.TENANT))
        ROLE_PERMISSIONS_MAP[role_name] = permission_list


@dataclass
class PermissionCheckResult:
    allowed: bool
    reason: str = ""
    matched_permissions: list[Permission] = field(default_factory=list)
    matched_policies: list[Policy] = field(default_factory=list)


class PermissionChecker:
    def __init__(self) -> None:
        self._policies: list[Policy] = []
        self._role_permissions = ROLE_PERMISSIONS_MAP

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def check(
        self,
        user_roles: list[str],
        resource: str,
        action: str,
        scope: Scope = Scope.TENANT,
        context: dict[str, Any] | None = None,
    ) -> PermissionCheckResult:
        matched_perms: list[Permission] = []
        for role in user_roles:
            perms = self._role_permissions.get(role, [])
            for perm in perms:
                if perm.matches(resource, action, scope):
                    matched_perms.append(perm)

        if matched_perms:
            context = context or {}
            for policy in self._policies:
                if policy.evaluate(context):
                    if policy.effect == "deny":
                        return PermissionCheckResult(
                            allowed=False,
                            reason=f"Denied by policy: {policy.name}",
                            matched_permissions=matched_perms,
                            matched_policies=[policy],
                        )
            return PermissionCheckResult(
                allowed=True,
                reason="Permission granted",
                matched_permissions=matched_perms,
            )

        return PermissionCheckResult(
            allowed=False,
            reason=f"No permission found for {resource}:{action}",
        )

    def check_tenant_access(
        self,
        user_roles: list[str],
        resource: str,
        action: str,
        user_tenant_id: str,
        target_tenant_id: str,
    ) -> PermissionCheckResult:
        if user_tenant_id != target_tenant_id:
            is_system_admin = "tenant_admin" in user_roles
            if not is_system_admin:
                return PermissionCheckResult(
                    allowed=False,
                    reason="Cross-tenant access denied",
                )
        return self.check(user_roles, resource, action, Scope.TENANT)

    def get_permissions_for_roles(self, roles: list[str]) -> list[Permission]:
        permissions: set[Permission] = set()
        for role in roles:
            perms = self._role_permissions.get(role, [])
            permissions.update(perms)
        return list(permissions)


DEFAULT_POLICIES: list[Policy] = [
    Policy(
        policy_id="POL-001",
        name="frozen_baseline_deny",
        description="禁止修改冻结基线",
        conditions={"baseline_status": "frozen"},
        effect="deny",
    ),
    Policy(
        policy_id="POL-002",
        name="suspended_tenant_deny",
        description="暂停租户禁止操作",
        conditions={"tenant_status": "suspended"},
        effect="deny",
    ),
    Policy(
        policy_id="POL-003",
        name="safety_critical_approval",
        description="安全关键件变更需总工程师批准",
        conditions={"is_safety_critical": True, "has_chief_approval": False},
        effect="deny",
    ),
]