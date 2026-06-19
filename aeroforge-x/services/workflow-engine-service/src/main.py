from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.infrastructure.database import close_connections
from src.infrastructure.event_bus import event_bus
from src.api.v2.workflow_definition_controller import router as definition_router
from src.api.v2.workflow_instance_controller import router as instance_router
from src.api.v2.event_trigger_controller import router as trigger_router
from src.api.v2.human_task_controller import router as human_task_router
from src.api.v6.config_change_controller import router as v6_config_change_router
from src.api.v6.cert_evidence_controller import router as v6_cert_evidence_router
from src.api.v6.supplier_car_controller import router as v6_supplier_car_router
from src.api.v6.shop_floor_event_controller import router as v6_shop_floor_event_router
from src.api.v6.cross_program_controller import router as v6_cross_program_router
from src.api.v6.dfx_controller import router as v6_dfx_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    yield
    await event_bus.close()
    await close_connections()


app = FastAPI(
    title="AeroForge-X Workflow Engine Service",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(definition_router, prefix="/api/v2/workflow-engine", tags=["WorkflowDefinition"])
app.include_router(instance_router, prefix="/api/v2/workflow-engine", tags=["WorkflowInstance"])
app.include_router(trigger_router, prefix="/api/v2/workflow-engine", tags=["EventTrigger"])
app.include_router(human_task_router, prefix="/api/v2/workflow-engine", tags=["HumanTask"])

app.include_router(v6_config_change_router)
app.include_router(v6_cert_evidence_router)
app.include_router(v6_supplier_car_router)
app.include_router(v6_shop_floor_event_router)
app.include_router(v6_cross_program_router)
app.include_router(v6_dfx_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "workflow-engine-service", "version": "6.1.0"}

@app.get("/api/v6/workflow-engine/health")
async def v6_health_check():
    return {"status": "healthy", "service": "workflow-engine-service", "version": "6.1.0"}