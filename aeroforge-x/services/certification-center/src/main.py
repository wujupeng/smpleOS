from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.infrastructure.database import engine
from src.infrastructure.event_bus import event_bus

from .api.certification_controller import router as cert_router
from .api.v1.cert_v1_controller import router as cert_v1_router


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})


app = FastAPI(title="AeroForge-X Certification Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(cert_router)
app.include_router(cert_v1_router, prefix="/api/v1", tags=["Certification V1"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "certification-center", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    await event_bus.connect()


@app.on_event("shutdown")
async def shutdown():
    await event_bus.close()
    await engine.dispose()
