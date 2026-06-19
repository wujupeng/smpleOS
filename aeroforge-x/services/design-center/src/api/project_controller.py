from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.project import AircraftType, ProjectStatus, ProjectMemberRole
from ..domain.entities.aircraft_template import TemplateRepository
from ..domain.services.project_domain_service import ProjectDomainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["Project Management"])

_service = ProjectDomainService()
_template_repo = TemplateRepository()


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_\-]+$")
    tenant_id: str = Field(..., min_length=1)
    aircraft_type: str = Field(default="fixed_wing")
    description: str = ""
    created_by: str = ""
    settings: dict[str, Any] | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class UpdateProjectSettingsRequest(BaseModel):
    design_rule_set: str | None = None
    material_scope: list[str] | None = None
    certification_standards: list[str] | None = None
    design_margin: float | None = None


class AddMemberRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field(default="member")


class CheckAccessRequest(BaseModel):
    user_id: str
    required_role: str | None = None


class ApplyTemplateRequest(BaseModel):
    template_id: str


@router.post("", response_model=ApiResponse[dict])
async def create_project(body: CreateProjectRequest):
    try:
        aircraft_type = AircraftType(body.aircraft_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid aircraft type: {body.aircraft_type}")
    try:
        project = _service.create_project(
            name=body.name,
            code=body.code,
            tenant_id=body.tenant_id,
            aircraft_type=aircraft_type,
            description=body.description,
            created_by=body.created_by,
            settings=body.settings,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return ApiResponse(data=project.to_dict())


@router.get("", response_model=ApiResponse[dict])
async def list_projects(
    tenant_id: str,
    status: str | None = None,
    aircraft_type: str | None = None,
):
    proj_status = ProjectStatus(status) if status else None
    proj_type = AircraftType(aircraft_type) if aircraft_type else None
    projects = _service.list_projects(tenant_id, proj_status, proj_type)
    return ApiResponse(data={
        "total": len(projects),
        "projects": [p.to_dict() for p in projects],
    })


@router.get("/{project_id}", response_model=ApiResponse[dict])
async def get_project(project_id: str):
    project = _service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.put("/{project_id}", response_model=ApiResponse[dict])
async def update_project(project_id: str, body: UpdateProjectRequest):
    project = _service.update_project(project_id, name=body.name, description=body.description)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.put("/{project_id}/settings", response_model=ApiResponse[dict])
async def update_project_settings(project_id: str, body: UpdateProjectSettingsRequest):
    settings = {k: v for k, v in body.model_dump().items() if v is not None}
    project = _service.update_project_settings(project_id, settings)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.post("/{project_id}/activate", response_model=ApiResponse[dict])
async def activate_project(project_id: str):
    project = _service.activate_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.post("/{project_id}/archive", response_model=ApiResponse[dict])
async def archive_project(project_id: str):
    project = _service.archive_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.post("/{project_id}/members", response_model=ApiResponse[dict])
async def add_project_member(project_id: str, body: AddMemberRequest):
    project = _service.add_project_member(project_id, body.user_id, body.role)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.get("/{project_id}/members", response_model=ApiResponse[dict])
async def list_project_members(project_id: str):
    project = _service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data={
        "project_id": project_id,
        "members": [m.to_dict() for m in project.members],
        "total": len(project.members),
    })


@router.delete("/{project_id}/members/{user_id}", response_model=ApiResponse[dict])
async def remove_project_member(project_id: str, user_id: str):
    project = _service.remove_project_member(project_id, user_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=project.to_dict())


@router.post("/{project_id}/check-access", response_model=ApiResponse[dict])
async def check_project_access(project_id: str, body: CheckAccessRequest):
    has_access = _service.check_project_access(project_id, body.user_id, body.required_role)
    return ApiResponse(data={
        "project_id": project_id,
        "user_id": body.user_id,
        "has_access": has_access,
    })


@router.get("/templates/list", response_model=ApiResponse[dict])
async def list_templates(aircraft_type: str | None = None, layout_type: str | None = None):
    templates = _template_repo.list_templates(aircraft_type, layout_type)
    return ApiResponse(data={
        "total": len(templates),
        "templates": [t.to_dict() for t in templates],
    })


@router.get("/templates/{template_id}", response_model=ApiResponse[dict])
async def get_template(template_id: str):
    template = _template_repo.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return ApiResponse(data=template.to_dict())


@router.post("/{project_id}/apply-template", response_model=ApiResponse[dict])
async def apply_template_to_project(project_id: str, body: ApplyTemplateRequest):
    template = _template_repo.get(body.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    project = _service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    settings = {
        "design_rule_set": template.design_rule_set,
        "material_scope": template.material_scope,
        "certification_standards": template.certification_standards,
    }
    settings.update(template.default_settings)
    _service.update_project_settings(project_id, settings)
    updated = _service.get_project(project_id)
    return ApiResponse(data={
        "project": updated.to_dict() if updated else None,
        "applied_template": template.to_dict(),
    })