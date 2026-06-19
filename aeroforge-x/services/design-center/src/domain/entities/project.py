from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from aeroforge_common.domain.base import DomainEvent


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class AircraftType(str, Enum):
    FIXED_WING = "fixed_wing"
    GLIDER = "glider"
    EVTOL = "evtol"
    UAV = "uav"


class ProjectMemberRole(str, Enum):
    OWNER = "owner"
    LEAD = "lead"
    MEMBER = "member"
    OBSERVER = "observer"


@dataclass
class ProjectMember:
    user_id: str
    role: ProjectMemberRole = ProjectMemberRole.MEMBER
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "joined_at": self.joined_at,
        }


@dataclass
class ProjectSettings:
    design_rule_set: str = "default"
    material_scope: list[str] = field(default_factory=lambda: ["aluminum", "carbon_fiber", "steel"])
    certification_standards: list[str] = field(default_factory=lambda: ["CCAR-23"])
    design_margin: float = 1.5
    max_operating_speed_kmh: float = 300.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "design_rule_set": self.design_rule_set,
            "material_scope": self.material_scope,
            "certification_standards": self.certification_standards,
            "design_margin": self.design_margin,
            "max_operating_speed_kmh": self.max_operating_speed_kmh,
        }


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    code: str = ""
    description: str = ""
    tenant_id: str = ""
    aircraft_type: AircraftType = AircraftType.FIXED_WING
    status: ProjectStatus = ProjectStatus.PLANNING
    spec_id: str = ""
    current_baseline_id: str = ""
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    members: list[ProjectMember] = field(default_factory=list)
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""
    domain_events: list[DomainEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "aircraft_type": self.aircraft_type.value,
            "status": self.status.value,
            "spec_id": self.spec_id,
            "current_baseline_id": self.current_baseline_id,
            "settings": self.settings.to_dict(),
            "members": [m.to_dict() for m in self.members],
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def activate(self) -> None:
        if self.status not in (ProjectStatus.PLANNING, ProjectStatus.ON_HOLD):
            raise ValueError(f"Cannot activate project in {self.status.value} status")
        self.status = ProjectStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="project.activated",
            aggregate_id=self.id,
            payload={"project_id": self.id, "tenant_id": self.tenant_id},
        ))

    def put_on_hold(self, reason: str = "") -> None:
        if self.status != ProjectStatus.ACTIVE:
            raise ValueError(f"Cannot put on hold a project in {self.status.value} status")
        self.status = ProjectStatus.ON_HOLD
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="project.on_hold",
            aggregate_id=self.id,
            payload={"project_id": self.id, "reason": reason},
        ))

    def complete(self) -> None:
        if self.status != ProjectStatus.ACTIVE:
            raise ValueError(f"Cannot complete a project in {self.status.value} status")
        self.status = ProjectStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="project.completed",
            aggregate_id=self.id,
            payload={"project_id": self.id},
        ))

    def archive(self) -> None:
        if self.status in (ProjectStatus.ACTIVE, ProjectStatus.PLANNING):
            raise ValueError("Cannot archive an active or planning project. Complete it first.")
        self.status = ProjectStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.add_domain_event(DomainEvent(
            event_type="project.archived",
            aggregate_id=self.id,
            payload={"project_id": self.id},
        ))

    def add_member(self, user_id: str, role: ProjectMemberRole = ProjectMemberRole.MEMBER) -> None:
        if any(m.user_id == user_id for m in self.members):
            raise ValueError(f"User {user_id} is already a member")
        self.members.append(ProjectMember(user_id=user_id, role=role))
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def remove_member(self, user_id: str) -> None:
        owner_members = [m for m in self.members if m.role == ProjectMemberRole.OWNER]
        if len(owner_members) == 1 and owner_members[0].user_id == user_id:
            raise ValueError("Cannot remove the last owner")
        self.members = [m for m in self.members if m.user_id != user_id]
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def check_access(self, user_id: str, required_role: ProjectMemberRole | None = None) -> bool:
        member = next((m for m in self.members if m.user_id == user_id), None)
        if member is None:
            return False
        if required_role is None:
            return True
        role_hierarchy = {
            ProjectMemberRole.OWNER: 4,
            ProjectMemberRole.LEAD: 3,
            ProjectMemberRole.MEMBER: 2,
            ProjectMemberRole.OBSERVER: 1,
        }
        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)

    def update_settings(self, settings: dict[str, Any]) -> None:
        if "design_rule_set" in settings:
            self.settings.design_rule_set = settings["design_rule_set"]
        if "material_scope" in settings:
            self.settings.material_scope = settings["material_scope"]
        if "certification_standards" in settings:
            self.settings.certification_standards = settings["certification_standards"]
        if "design_margin" in settings:
            self.settings.design_margin = settings["design_margin"]
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_domain_event(self, event: DomainEvent) -> None:
        self.domain_events.append(event)