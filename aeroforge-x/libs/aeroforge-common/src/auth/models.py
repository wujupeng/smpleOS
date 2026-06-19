from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic_settings import BaseSettings


class KeycloakSettings(BaseSettings):
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "aeroforge-x"
    keycloak_client_id: str = "aeroforge-api"
    keycloak_client_secret: str = ""
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "admin"

    model_config = {"env_prefix": ""}


class AeroForgeRole(str, Enum):
    CHIEF_DESIGNER = "chief_designer"
    STRUCTURAL_ENGINEER = "structural_engineer"
    AERODYNAMIC_ENGINEER = "aerodynamic_engineer"
    PROCESS_ENGINEER = "process_engineer"
    QUALITY_ENGINEER = "quality_engineer"
    PRODUCTION_MANAGER = "production_manager"
    AIRWORTHINESS_ENGINEER = "airworthiness_engineer"
    MAINTENANCE_ENGINEER = "maintenance_engineer"


ROLE_PERMISSIONS: dict[str, list[str]] = {
    AeroForgeRole.CHIEF_DESIGNER: [
        "specs:create", "specs:read", "specs:update", "specs:confirm",
        "models:generate", "models:read",
        "baselines:create", "baselines:freeze", "baselines:read",
        "ecr:approve",
    ],
    AeroForgeRole.STRUCTURAL_ENGINEER: [
        "specs:read", "models:read",
        "structures:generate", "structures:read",
        "fea:submit", "fea:read",
    ],
    AeroForgeRole.AERODYNAMIC_ENGINEER: [
        "specs:read", "models:read",
        "cfd:submit", "cfd:read",
    ],
    AeroForgeRole.PROCESS_ENGINEER: [
        "specs:read", "models:read",
        "bom:read", "mbom:transform",
        "process-routes:create", "process-routes:read",
    ],
    AeroForgeRole.QUALITY_ENGINEER: [
        "inspection:create", "inspection:read", "inspection:execute",
        "capa:create", "capa:read", "capa:verify",
    ],
    AeroForgeRole.PRODUCTION_MANAGER: [
        "work-orders:create", "work-orders:read", "work-orders:dispatch",
        "stations:read", "stations:schedule",
        "serial-numbers:assign", "serial-numbers:read",
    ],
    AeroForgeRole.AIRWORTHINESS_ENGINEER: [
        "specs:read", "models:read",
        "rules:validate", "rules:read",
        "certification:read", "certification:review",
    ],
    AeroForgeRole.MAINTENANCE_ENGINEER: [
        "trace:read",
        "twin:read", "twin:sync",
        "maintenance:create", "maintenance:read",
    ],
}


@dataclass
class AuthUser:
    user_id: str
    username: str
    roles: list[str]
    permissions: list[str]
    tenant_id: str = ""
    tenant_code: str = ""

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles