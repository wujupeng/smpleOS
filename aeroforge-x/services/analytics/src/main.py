from fastapi import FastAPI

from .api.analytics_controller import router as analytics_router
from .api.report_controller import router as report_router

app = FastAPI(title="AeroForge-X Analytics", version="0.1.0")
app.include_router(analytics_router)
app.include_router(report_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics"}