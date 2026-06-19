from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.compliance_controller import router as compliance_router
from .api.qms_controller import router as qms_router
from .api.spc_controller import router as spc_router

app = FastAPI(title="AeroForge-X QMS Service", version="0.1.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(qms_router)
app.include_router(spc_router)
app.include_router(compliance_router)


@app.get("/health")
async def health():
    return {"status": "ok"}