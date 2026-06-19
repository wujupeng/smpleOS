from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.bom_controller import router as bom_router
from .api.mbom_controller import router as mbom_router
from .api.sbom_controller import router as sbom_router

app = FastAPI(title="AeroForge-X BOM Center", version="0.2.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(bom_router)
app.include_router(mbom_router)
app.include_router(sbom_router)


@app.get("/health")
async def health():
    return {"status": "ok"}