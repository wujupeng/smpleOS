from __future__ import annotations

import logging

from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.twin_controller import router as twin_router
from .api.predictive_controller import router as predictive_router
from .api.simulation_controller import router as simulation_router
from .api.twin_fusion_controller import router as fusion_router
from .api.twin_loop_controller import router as loop_router
from .api.multi_fidelity_controller import router as mf_router
from .api.v1.twin_v1_controller import router as twin_v1_router
from .api.v1.fleet_twin_controller import router as fleet_twin_router

logger = logging.getLogger(__name__)

app = FastAPI(title="AeroForge-X Digital Twin Center", version="1.0.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(twin_router)
app.include_router(predictive_router)
app.include_router(simulation_router)
app.include_router(fusion_router)
app.include_router(loop_router)
app.include_router(mf_router)
app.include_router(twin_v1_router, prefix="/api/v1", tags=["Twin V1"])
app.include_router(fleet_twin_router, prefix="/api/v1", tags=["Fleet Twin"])


@app.get("/health")
async def health():
    return {"status": "ok"}