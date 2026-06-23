from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from src.infrastructure.database import close_connections, get_pg_pool
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
from src.api.v6.material_controller import router as v6_material_router
from src.api.v6.quality_controller import router as v6_quality_router
from src.api.v6.dt_certification_controller import router as v6_dt_cert_router
from src.api.v6.event_contract_controller import router as v6_event_contract_router
from src.api.v6.identity_controller import router as v6_identity_router
from src.api.v6.trace_graph_controller import router as v6_trace_graph_router
from src.infrastructure.event_contract.schema_registry import schema_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    schema_dir = os.environ.get('EVENT_CONTRACT_SCHEMA_DIR', '/app/event-contract/schema')
    count = schema_registry.load_from_directory(schema_dir)
    logging.getLogger(__name__).info(f"Loaded {count} event schemas from {schema_dir}")
    try:
        from src.domain.services.trace_graph_service import get_trace_graph_service
        tg_svc = await get_trace_graph_service()
        await tg_svc.load_cache_from_db()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Trace graph cache load failed: {e}")
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
app.include_router(v6_material_router)
app.include_router(v6_quality_router)
app.include_router(v6_dt_cert_router)
app.include_router(v6_event_contract_router)
app.include_router(v6_identity_router)
app.include_router(v6_trace_graph_router)


@app.get("/health")
async def health_check():
    from datetime import datetime, timezone
    checks = {}
    try:
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "connected"
    except Exception as e:
        logging.getLogger(__name__).warning(f"PostgreSQL health check failed: {e}")
        checks["postgres"] = "disconnected"

    try:
        if event_bus._nc is not None and event_bus._nc.is_connected:
            checks["nats"] = "connected"
        else:
            checks["nats"] = "disconnected"
    except Exception:
        checks["nats"] = "disconnected"

    try:
        from src.infrastructure.database import get_neo4j_driver
        driver = await get_neo4j_driver()
        if driver is not None:
            await driver.verify_connectivity()
            checks["neo4j"] = "connected"
        else:
            checks["neo4j"] = "degraded"
    except Exception:
        checks["neo4j"] = "degraded"

    try:
        from src.infrastructure.object_storage import object_storage
        client = object_storage._ensure_client()
        if client is not None:
            client.bucket_exists("aeroforge-cert-evidence")
            checks["minio"] = "connected"
        else:
            checks["minio"] = "degraded"
    except Exception:
        checks["minio"] = "degraded"

    status = "healthy" if checks.get("postgres") == "connected" and checks.get("nats") == "connected" else "degraded"
    return {
        "status": status,
        **checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/v6/aircraft-core/health")
async def v6_health_check():
    return await health_check()