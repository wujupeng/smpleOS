from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.mes_controller import router as mes_router
from .api.process_route_controller import router as route_router
from .api.scheduling_controller import router as scheduling_router
from .api.adaptive_scheduling_controller import router as adaptive_router
from .api.quality_prediction_controller import router as quality_pred_router
from .api.process_optimization_controller import router as process_opt_router

app = FastAPI(title="AeroForge-X MES Center", version="0.2.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(mes_router)
app.include_router(route_router)
app.include_router(scheduling_router)
app.include_router(adaptive_router)
app.include_router(quality_pred_router)
app.include_router(process_opt_router)


@app.get("/health")
async def health():
    return {"status": "ok"}