from fastapi import FastAPI

from aeroforge_common.domain.exception_handlers import register_exception_handlers
from aeroforge_common.auth.middleware import auth_middleware

from .api.data_lake_controller import router as datalake_router

app = FastAPI(title="AeroForge-X Data Lake", version="4.0.0")
register_exception_handlers(app)
app.middleware("http")(auth_middleware)
app.include_router(datalake_router)


@app.get("/health")
async def health():
    return {"status": "ok"}