from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.domain.responses import ApiResponse, AsyncTaskResponse
from aeroforge_common.auth.middleware import auth_middleware

from .infrastructure.celery_tasks.celery_app import celery_app
from .infrastructure.celery_tasks.cfd_tasks import run_cfd_analysis
from .infrastructure.celery_tasks.fea_tasks import run_fea_analysis
from .infrastructure.celery_tasks.flutter_tasks import run_flutter_analysis
from .infrastructure.celery_tasks.thermal_tasks import run_thermal_analysis
from .infrastructure.celery_tasks.multiphysics_tasks import run_multiphysics_analysis
from .domain.entities.mesh_task import MeshTask, MeshType, MeshTaskStatus
from .domain.services.mesh_domain_service import MeshDomainService
from .domain.services.cae_task_queue_manager import CAETaskQueueManager, TaskPriority, TaskType
from .api.cfd_controller import router as cfd_router
from .api.fea_controller import router as fea_router
from .api.flutter_controller import router as flutter_router
from .api.thermal_controller import router as thermal_router
from .api.multiphysics_controller import router as multiphysics_router
from .api.openfoam_advanced_controller import router as openfoam_advanced_router
from .api.fenics_advanced_controller import router as fenics_advanced_router

logger = logging.getLogger(__name__)

app = FastAPI(title="AeroForge-X CAE Center", version="0.2.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(cfd_router)
app.include_router(fea_router)
app.include_router(flutter_router)
app.include_router(thermal_router)
app.include_router(multiphysics_router)
app.include_router(openfoam_advanced_router)
app.include_router(fenics_advanced_router)

_mesh_service = MeshDomainService()
_mesh_tasks: dict[str, MeshTask] = {}
_queue_manager = CAETaskQueueManager()


class CFDAnalysisRequest(BaseModel):
    model_id: str
    mesh_task_id: str | None = None
    solver: str = "simpleFoam"
    analysis_type: str = "steady"
    n_proc: int = 1
    flight_conditions: dict[str, Any] | None = None
    turbulence_model: str = "kOmegaSST"
    priority: int = Field(default=2, ge=0, le=3)


class FEAAnalysisRequest(BaseModel):
    model_id: str
    mesh_task_id: str | None = None
    problem_type: str = "linear_elasticity"
    n_proc: int = 1
    materials: list[dict[str, Any]] | None = None
    priority: int = Field(default=2, ge=0, le=3)


class FlutterAnalysisRequest(BaseModel):
    model_id: str
    mesh_task_id: str | None = None
    n_modes: int = 10
    speed_range: list[float] = Field(default_factory=lambda: [0.0, 300.0])
    priority: int = Field(default=1, ge=0, le=3)


class ThermalAnalysisRequest(BaseModel):
    model_id: str
    mesh_task_id: str | None = None
    analysis_type: str = "steady_state"
    n_proc: int = 1
    priority: int = Field(default=2, ge=0, le=3)


class MultiphysicsAnalysisRequest(BaseModel):
    model_id: str
    mesh_task_id: str | None = None
    coupling_type: str = "weak"
    coupling_iterations: int = 1
    n_proc: int = 1
    priority: int = Field(default=1, ge=0, le=3)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/cae/workers/status", response_model=ApiResponse[dict])
async def get_workers_status():
    inspect = celery_app.control.inspect()
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    stats = inspect.stats() or {}
    workers = []
    for worker_name, worker_stats in stats.items():
        workers.append({
            "name": worker_name,
            "status": "online",
            "active_tasks": len(active.get(worker_name, [])),
            "reserved_tasks": len(reserved.get(worker_name, [])),
            "uptime": worker_stats.get("uptime", None),
            "pool": worker_stats.get("pool", {}),
        })
    return ApiResponse(data={
        "total_workers": len(workers),
        "workers": workers,
    })


@app.post("/api/v1/cae/cfd/submit", response_model=AsyncTaskResponse)
async def submit_cfd_analysis(body: CFDAnalysisRequest):
    params = body.model_dump()
    priority_map = {0: "urgent", 1: "high", 2: "normal", 3: "low"}
    queue = priority_map.get(body.priority, "cfd")
    result = run_cfd_analysis.apply_async(
        kwargs={"params": params},
        queue=queue,
        priority=body.priority,
    )
    return AsyncTaskResponse(
        message="CFD analysis submitted",
        task_id=result.id,
        status="pending",
    )


@app.post("/api/v1/cae/fea/submit", response_model=AsyncTaskResponse)
async def submit_fea_analysis(body: FEAAnalysisRequest):
    params = body.model_dump()
    result = run_fea_analysis.apply_async(
        kwargs={"params": params},
        queue="fea",
        priority=body.priority,
    )
    return AsyncTaskResponse(
        message="FEA analysis submitted",
        task_id=result.id,
        status="pending",
    )


@app.post("/api/v1/cae/flutter/submit", response_model=AsyncTaskResponse)
async def submit_flutter_analysis(body: FlutterAnalysisRequest):
    params = body.model_dump()
    result = run_flutter_analysis.apply_async(
        kwargs={"params": params},
        queue="flutter",
        priority=body.priority,
    )
    return AsyncTaskResponse(
        message="Flutter analysis submitted",
        task_id=result.id,
        status="pending",
    )


@app.post("/api/v1/cae/thermal/submit", response_model=AsyncTaskResponse)
async def submit_thermal_analysis(body: ThermalAnalysisRequest):
    params = body.model_dump()
    result = run_thermal_analysis.apply_async(
        kwargs={"params": params},
        queue="thermal",
        priority=body.priority,
    )
    return AsyncTaskResponse(
        message="Thermal analysis submitted",
        task_id=result.id,
        status="pending",
    )


@app.post("/api/v1/cae/multiphysics/submit", response_model=AsyncTaskResponse)
async def submit_multiphysics_analysis(body: MultiphysicsAnalysisRequest):
    params = body.model_dump()
    result = run_multiphysics_analysis.apply_async(
        kwargs={"params": params},
        queue="multiphysics",
        priority=body.priority,
    )
    return AsyncTaskResponse(
        message="Multiphysics analysis submitted",
        task_id=result.id,
        status="pending",
    )


@app.get("/api/v1/cae/tasks/{task_id}/status", response_model=ApiResponse[dict])
async def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    response_data: dict[str, Any] = {
        "task_id": task_id,
        "status": result.status,
    }
    if result.ready():
        if result.successful():
            response_data["result"] = result.result
        else:
            response_data["error"] = str(result.result)
    elif result.info and isinstance(result.info, dict):
        response_data["progress"] = result.info
    return ApiResponse(data=response_data)


@app.delete("/api/v1/cae/tasks/{task_id}", response_model=ApiResponse[dict])
async def cancel_task(task_id: str):
    celery_app.control.revoke(task_id, terminate=True)
    return ApiResponse(data={"task_id": task_id, "status": "revoked"})


class MeshGenerateRequest(BaseModel):
    model_id: str
    mesh_type: str = "unstructured"
    target_element_size: float = Field(default=0.01, gt=0)
    params: dict[str, Any] | None = None


class MeshRepairRequest(BaseModel):
    geometry_path: str


@app.post("/api/v1/cae/mesh/generate", response_model=AsyncTaskResponse)
async def generate_mesh(body: MeshGenerateRequest):
    mesh_type = MeshType(body.mesh_type)
    task = MeshTask(
        model_id=body.model_id,
        mesh_type=mesh_type,
        target_element_size=body.target_element_size,
    )
    _mesh_tasks[task.id] = task
    task = _mesh_service.generate_mesh(task, body.params)
    return AsyncTaskResponse(
        message="Mesh generation completed",
        task_id=task.id,
        status=task.status.value,
    )


@app.get("/api/v1/cae/mesh/{task_id}/status", response_model=ApiResponse[dict])
async def get_mesh_status(task_id: str):
    task = _mesh_tasks.get(task_id)
    if task is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mesh task not found")
    return ApiResponse(data=task.to_dict())


@app.get("/api/v1/cae/mesh/{task_id}/quality", response_model=ApiResponse[dict])
async def get_mesh_quality(task_id: str):
    task = _mesh_tasks.get(task_id)
    if task is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mesh task not found")
    if task.mesh_quality is None:
        return ApiResponse(data={"message": "Quality metrics not available"})
    quality_data = {
        "orthogonality_min": task.mesh_quality.orthogonality_min,
        "orthogonality_avg": task.mesh_quality.orthogonality_avg,
        "skewness_max": task.mesh_quality.skewness_max,
        "skewness_avg": task.mesh_quality.skewness_avg,
        "aspect_ratio_max": task.mesh_quality.aspect_ratio_max,
        "aspect_ratio_avg": task.mesh_quality.aspect_ratio_avg,
    }
    return ApiResponse(data=quality_data)


@app.post("/api/v1/cae/mesh/{task_id}/repair", response_model=ApiResponse[dict])
async def repair_geometry(task_id: str, body: MeshRepairRequest):
    result = _mesh_service.repair_geometry(body.geometry_path)
    return ApiResponse(data=result)


class PriorityUpdateRequest(BaseModel):
    priority: int = Field(..., ge=0, le=3)


@app.get("/api/v1/cae/queue", response_model=ApiResponse[dict])
async def get_task_queue():
    queue = _queue_manager.get_queue()
    resource_status = _queue_manager.get_resource_status()
    return ApiResponse(data={
        "queue": queue,
        "total_queued": resource_status.total_tasks_queued,
        "total_running": resource_status.total_tasks_running,
        "available_slots": resource_status.available_slots,
    })


@app.put("/api/v1/cae/tasks/{task_id}/priority", response_model=ApiResponse[dict])
async def update_task_priority(task_id: str, body: PriorityUpdateRequest):
    new_priority = TaskPriority(body.priority)
    entry = _queue_manager.prioritize(task_id, new_priority)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found in queue")
    return ApiResponse(data={
        "task_id": task_id,
        "new_priority": new_priority.name,
    })


@app.delete("/api/v1/cae/queue/{task_id}", response_model=ApiResponse[dict])
async def cancel_queued_task(task_id: str):
    removed = _queue_manager.remove(task_id)
    if not removed:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found in queue")
    return ApiResponse(data={"task_id": task_id, "status": "cancelled"})