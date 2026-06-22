from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from src.infrastructure.database import close_connections
from src.infrastructure.event_bus import event_bus
from src.api.v2.aircraft_object_controller import router as aircraft_object_router
from src.api.v2.version_controller import router as version_router
from src.api.v2.link_controller import router as link_router
from src.api.v2.property_controller import router as property_router
from src.api.v6.configuration_controller import router as v6_config_router
from src.api.v6.certification_controller import router as v6_cert_router
from src.api.v6.supplier_controller import router as v6_supplier_router
from src.api.v6.production_dashboard_controller import router as v6_dashboard_router
from src.api.v6.gdt_controller import router as v6_gdt_router
from src.api.v6.dfx_controller import router as v6_dfx_router
from src.api.v6.config_identity_controller import router as v6_identity_router
from src.api.v6.evidence_controller import router as v6_evidence_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    yield
    await event_bus.close()
    await close_connections()


app = FastAPI(
    title="AeroForge-X Aircraft Core Service",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aircraft_object_router, prefix="/api/v2/aircraft-core", tags=["AircraftObject"])
app.include_router(version_router, prefix="/api/v2/aircraft-core", tags=["AircraftObjectVersion"])
app.include_router(link_router, prefix="/api/v2/aircraft-core", tags=["AircraftObjectLink"])
app.include_router(property_router, prefix="/api/v2/aircraft-core", tags=["AircraftProperty"])

app.include_router(v6_config_router)
app.include_router(v6_cert_router)
app.include_router(v6_supplier_router)
app.include_router(v6_dashboard_router)
app.include_router(v6_gdt_router)
app.include_router(v6_dfx_router)
app.include_router(v6_identity_router)
app.include_router(v6_evidence_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aircraft-core-service", "version": "6.1.0"}

@app.get("/api/v6/aircraft-core/health")
async def v6_health_check():
    return {"status": "healthy", "service": "aircraft-core-service", "version": "6.1.0"}