from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from src.infrastructure.database import close_connections
from src.infrastructure.event_bus import event_bus
from src.infrastructure.nats_consumer import register_config_consumer
from src.api.v2.physics_model_controller import router as model_router
from src.api.v2.simulation_controller import router as simulation_router
from src.api.v2.reduced_model_controller import router as rom_router
from src.api.v2.twin_runtime_controller import router as runtime_router
from src.api.v2.calibration_controller import router as calibration_router
from src.api.v6.shop_floor_controller import router as v6_shop_floor_router
from src.api.v6.digital_twin_controller import router as v6_digital_twin_router
from src.api.v6.uq_mdo7d_controller import router as v6_uq_mdo_router
from src.api.v6.dataset_controller import router as v6_dataset_router
from src.api.v6.dfx_controller import router as v6_dfx_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    await register_config_consumer(event_bus)
    yield
    await event_bus.close()
    await close_connections()


app = FastAPI(
    title="AeroForge-X Physics Twin Service",
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(model_router, prefix="/api/v2/physics-twin", tags=["PhysicsModel"])
app.include_router(simulation_router, prefix="/api/v2/physics-twin", tags=["PhysicsSimulation"])
app.include_router(rom_router, prefix="/api/v2/physics-twin", tags=["ReducedOrderModel"])
app.include_router(runtime_router, prefix="/api/v2/physics-twin", tags=["DigitalTwinRuntime"])
app.include_router(calibration_router, prefix="/api/v2/physics-twin", tags=["TwinCalibration"])

app.include_router(v6_shop_floor_router)
app.include_router(v6_digital_twin_router)
app.include_router(v6_uq_mdo_router)
app.include_router(v6_dataset_router)
app.include_router(v6_dfx_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "physics-twin-service", "version": "6.1.0"}

@app.get("/api/v6/physics-twin/health")
async def v6_health_check():
    return {"status": "healthy", "service": "physics-twin-service", "version": "6.1.0"}