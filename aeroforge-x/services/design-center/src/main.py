from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.domain.responses import ApiResponse, PagedResponse, AsyncTaskResponse
from aeroforge_common.auth.middleware import auth_middleware

from .api.spec_controller import router as spec_router
from .api.project_controller import router as project_router
from .api.v1.design_controller import router as design_v1_router
from .domain.services.aircraft_type_config import AircraftTypeConfig
from .domain.services.model_domain_service import ParametricModelGenerator
from .domain.services.design_rule_engine import DesignRuleEngine

app = FastAPI(title="AeroForge-X Design Center", version="1.0.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)

app.include_router(spec_router)
app.include_router(project_router)
app.include_router(design_v1_router, prefix="/api/v1/design", tags=["Design v1.0"])

_type_config = AircraftTypeConfig()
_model_generator = ParametricModelGenerator()
_rule_engine = DesignRuleEngine()


class TypeRecommendRequest(BaseModel):
    payload_kg: float = Field(..., gt=0)
    range_km: float = Field(..., gt=0)
    cruise_speed_kmh: float = Field(..., gt=0)
    power_type: str = "electric"
    vtol: bool = False
    crew: bool = True


class ModelGenerateRequest(BaseModel):
    spec_id: str
    aircraft_type: str = "fixed_wing"
    payload_kg: float = 120.0
    range_km: float = 200.0
    cruise_speed_kmh: float = 120.0
    template: dict[str, Any] | None = None


class RuleValidateRequest(BaseModel):
    model_params: dict[str, Any]
    changed_params: list[str] | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/aircraft-type/recommend", response_model=ApiResponse[dict])
async def recommend_aircraft_type(body: TypeRecommendRequest):
    result = _type_config.recommend(body.model_dump())
    return ApiResponse(data=result)


@app.get("/api/v1/aircraft-type/{aircraft_type}/template", response_model=ApiResponse[dict])
async def get_type_template(aircraft_type: str):
    template = _type_config.get_template(aircraft_type)
    return ApiResponse(data=template)


@app.post("/api/v1/models/generate", response_model=AsyncTaskResponse)
async def generate_model(body: ModelGenerateRequest):
    params = body.model_dump()
    if body.template:
        params["template"] = body.template
    else:
        template = _type_config.get_template(body.aircraft_type)
        params["template"] = template
    model = _model_generator.generate(params)
    return AsyncTaskResponse(
        message="Model generated successfully",
        task_id=params["spec_id"],
        status="completed",
    )


@app.get("/api/v1/models/{model_id}", response_model=ApiResponse[dict])
async def get_model(model_id: str):
    return ApiResponse(data={"id": model_id, "status": "completed"})


@app.get("/api/v1/models/{model_id}/status", response_model=ApiResponse[dict])
async def get_model_status(model_id: str):
    return ApiResponse(data={"id": model_id, "status": "completed"})


@app.post("/api/v1/rules/validate", response_model=ApiResponse[dict])
async def validate_rules(body: RuleValidateRequest):
    if body.changed_params:
        violations = _rule_engine.validate_incremental(body.model_params, body.changed_params)
    else:
        violations = _rule_engine.validate(body.model_params)
    return ApiResponse(data={"violations": violations})
