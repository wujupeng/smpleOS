from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.infrastructure.database import engine
from src.infrastructure.event_bus import event_bus
from src.api.stability_controller import router as stability_router
from src.api.flight_dynamics_controller import router as flight_dynamics_router
from src.api.control_synthesis_controller import router as control_synthesis_router
from src.api.flight_envelope_controller import router as flight_envelope_router


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})


app = FastAPI(title="AeroForge-X Verification Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(stability_router, prefix="/api/v1/verification/stability", tags=["Stability"])
app.include_router(flight_dynamics_router, prefix="/api/v1/verification/flight-dynamics", tags=["Flight Dynamics"])
app.include_router(control_synthesis_router, prefix="/api/v1/verification/control-synthesis", tags=["Control Synthesis"])
app.include_router(flight_envelope_router, prefix="/api/v1/verification/flight-envelope", tags=["Flight Envelope"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "verification-center", "version": "1.0.0"}


@app.on_event("startup")
async def startup():
    await event_bus.connect()


@app.on_event("shutdown")
async def shutdown():
    await event_bus.close()
    await engine.dispose()