from __future__ import annotations

import logging
from typing import Any

from aeroforge_common.domain.base import DomainEvent

from .entities.project import Project, ProjectStatus, AircraftType, ProjectMemberRole

logger = logging.getLogger(__name__)


class ProjectDomainService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._tenant_projects: dict[str, list[str]] = {}

    def create_project(
        self,
        name: str,
        code: str,
        tenant_id: str,
        aircraft_type: AircraftType = AircraftType.FIXED_WING,
        description: str = "",
        created_by: str = "",
        settings: dict[str, Any] | None = None,
    ) -> Project:
        tenant_proj_ids = self._tenant_projects.setdefault(tenant_id, [])
        for pid in tenant_proj_ids:
            existing = self._projects.get(pid)
            if existing and existing.code == code:
                raise ValueError(f"Project code '{code}' already exists in tenant")

        project = Project(
            name=name,
            code=code,
            tenant_id=tenant_id,
            aircraft_type=aircraft_type,
            description=description,
            created_by=created_by,
        )

        if settings:
            project.update_settings(settings)

        if created_by:
            project.add_member(created_by, ProjectMemberRole.OWNER)

        self._projects[project.id] = project
        tenant_proj_ids.append(project.id)

        project.add_domain_event(DomainEvent(
            event_type="project.created",
            aggregate_id=project.id,
            payload={
                "project_id": project.id,
                "tenant_id": tenant_id,
                "name": name,
                "aircraft_type": aircraft_type.value,
            },
        ))

        logger.info("Created project: %s (%s) tenant=%s type=%s", name, code, tenant_id, aircraft_type.value)
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list_projects(
        self,
        tenant_id: str,
        status: ProjectStatus | None = None,
        aircraft_type: AircraftType | None = None,
    ) -> list[Project]:
        proj_ids = self._tenant_projects.get(tenant_id, [])
        projects = [self._projects[pid] for pid in proj_ids if pid in self._projects]
        if status:
            projects = [p for p in projects if p.status == status]
        if aircraft_type:
            projects = [p for p in projects if p.aircraft_type == aircraft_type]
        return projects

    def update_project(self, project_id: str, name: str | None = None, description: str | None = None) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        from datetime import datetime, timezone
        project.updated_at = datetime.now(timezone.utc).isoformat()
        return project

    def archive_project(self, project_id: str) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.archive()
        return project

    def activate_project(self, project_id: str) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.activate()
        return project

    def add_project_member(self, project_id: str, user_id: str, role: str = "member") -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        member_role = ProjectMemberRole(role)
        project.add_member(user_id, member_role)
        return project

    def remove_project_member(self, project_id: str, user_id: str) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.remove_member(user_id)
        return project

    def check_project_access(self, project_id: str, user_id: str, required_role: str | None = None) -> bool:
        project = self.get_project(project_id)
        if project is None:
            return False
        role = ProjectMemberRole(required_role) if required_role else None
        return project.check_access(user_id, role)

    def update_project_settings(self, project_id: str, settings: dict[str, Any]) -> Project | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.update_settings(settings)
        return project