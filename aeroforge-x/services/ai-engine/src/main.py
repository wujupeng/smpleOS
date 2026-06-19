from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.infrastructure.database import engine
from src.infrastructure.event_bus import event_bus

from .api.aerogpt_controller import router as aerogpt_router
from .api.optimization_controller import router as optimization_router
from .api.topology_controller import router as topology_router
from .api.v1.ai_v1_controller import router as ai_v1_router


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})


app = FastAPI(title="AeroForge-X AI Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(aerogpt_router)
app.include_router(optimization_router)
app.include_router(topology_router)
app.include_router(ai_v1_router, prefix="/api/v1", tags=["AI Engine V1"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-engine", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    await event_bus.connect()


@app.on_event("shutdown")
async def shutdown():
    await event_bus.close()
    await engine.dispose()
