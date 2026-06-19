from fastapi import FastAPI

from .api.audit_controller import router as audit_router
from .api.erp_integration_controller import router as erp_router
from .api.i18n_controller import router as i18n_router
from .api.security_controller import router as security_router
from .api.tenant_controller import router as tenant_router

app = FastAPI(title="AeroForge-X Tenant Service", version="0.1.0")
app.include_router(tenant_router)
app.include_router(i18n_router)
app.include_router(audit_router)
app.include_router(security_router)
app.include_router(erp_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tenant-service"}