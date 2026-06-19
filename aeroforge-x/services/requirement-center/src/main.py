from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.database import engine
from src.infrastructure.event_bus import event_bus
from src.api.requirement_controller import router as requirement_router


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": str(exc)})


app = FastAPI(title="AeroForge-X Requirement Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(requirement_router, prefix="/api/v1/requirement", tags=["Requirement"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "requirement-center", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    await event_bus.connect()


@app.on_event("shutdown")
async def shutdown():
    await event_bus.close()
    await engine.dispose()