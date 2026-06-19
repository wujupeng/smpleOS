from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.plm_controller import router as plm_router
from .api.change_controller import router as change_router

app = FastAPI(title="AeroForge-X PLM Center", version="0.2.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(plm_router)
app.include_router(change_router)


@app.get("/health")
async def health():
    return {"status": "ok"}