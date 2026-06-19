from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aeroforge_common.domain.responses import ApiResponse

from ..domain.entities.openfoam_advanced import (
    ParametricStudy, AdjointOptimization, AeroDatabase,
)
from ..domain.services.openfoam_advanced_service import OpenFOAMAdvancedService

router = APIRouter(prefix="/api/v1/cae/cfd", tags=["OpenFOAM Advanced"])

_service = OpenFOAMAdvancedService()
_parametric_studies: dict[str, ParametricStudy] = {}
_adjoint_opts: dict[str, AdjointOptimization] = {}
_aero_databases: dict[str, AeroDatabase] = {}


class SweepRangeRequest(BaseModel):
    parameter: str
    start: float
    end: float
    step: float
    unit: str = ""


class ParametricStudyRequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    sweep_ranges: list[SweepRangeRequest]
    solver: str = "simpleFoam"
    turbulence_model: str = "kOmegaSST"
    max_parallel: int = Field(default=4, ge=1, le=16)


class AdjointOptRequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    objective_function: str = "minimize_drag"
    max_iterations: int = Field(default=20, ge=1, le=100)
    convergence_tolerance: float = Field(default=1e-4, gt=0)
    step_size: float = Field(default=0.01, gt=0, le=1.0)


class AeroDatabaseRequest(BaseModel):
    model_id: str
    project_id: str = "default"
    tenant_id: str = "default"
    alpha_range: SweepRangeRequest | None = None
    mach_range: SweepRangeRequest | None = None
    beta_range: SweepRangeRequest | None = None


@router.post("/parametric-study", response_model=ApiResponse[dict])
async def create_parametric_study(body: ParametricStudyRequest):
    study = _service.run_parametric_study(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        sweep_ranges=[sr.model_dump() for sr in body.sweep_ranges],
        solver=body.solver,
        turbulence_model=body.turbulence_model,
        max_parallel=body.max_parallel,
    )
    _parametric_studies[study.id] = study
    return ApiResponse(data=study.to_dict())


@router.get("/parametric-study/{study_id}", response_model=ApiResponse[dict])
async def get_parametric_study(study_id: str):
    study = _parametric_studies.get(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Parametric study not found")
    return ApiResponse(data=study.to_dict())


@router.get("/parametric-studies", response_model=ApiResponse[dict])
async def list_parametric_studies(project_id: str | None = None):
    studies = list(_parametric_studies.values())
    if project_id:
        studies = [s for s in studies if s.project_id == project_id]
    return ApiResponse(data={
        "studies": [s.to_dict() for s in studies],
        "total": len(studies),
    })


@router.post("/adjoint-optimization", response_model=ApiResponse[dict])
async def create_adjoint_optimization(body: AdjointOptRequest):
    opt = _service.run_adjoint_optimization(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        objective_function=body.objective_function,
        max_iterations=body.max_iterations,
        convergence_tolerance=body.convergence_tolerance,
        step_size=body.step_size,
    )
    _adjoint_opts[opt.id] = opt
    return ApiResponse(data=opt.to_dict())


@router.get("/adjoint-optimization/{opt_id}", response_model=ApiResponse[dict])
async def get_adjoint_optimization(opt_id: str):
    opt = _adjoint_opts.get(opt_id)
    if not opt:
        raise HTTPException(status_code=404, detail="Adjoint optimization not found")
    return ApiResponse(data=opt.to_dict())


@router.post("/aero-database", response_model=ApiResponse[dict])
async def create_aero_database(body: AeroDatabaseRequest):
    db = _service.generate_aero_database(
        model_id=body.model_id,
        project_id=body.project_id,
        tenant_id=body.tenant_id,
        alpha_range=body.alpha_range.model_dump() if body.alpha_range else None,
        mach_range=body.mach_range.model_dump() if body.mach_range else None,
        beta_range=body.beta_range.model_dump() if body.beta_range else None,
    )
    _aero_databases[db.id] = db
    return ApiResponse(data=db.to_dict())


@router.get("/aero-database/{db_id}", response_model=ApiResponse[dict])
async def get_aero_database(db_id: str):
    db = _aero_databases.get(db_id)
    if not db:
        raise HTTPException(status_code=404, detail="Aero database not found")
    return ApiResponse(data=db.to_dict())