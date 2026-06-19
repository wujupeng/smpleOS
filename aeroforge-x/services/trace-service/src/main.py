from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.trace_controller import router as trace_router

app = FastAPI(title="AeroForge-X Trace Service", version="0.1.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(trace_router)


@app.get("/health")
async def health():
    return {"status": "ok"}