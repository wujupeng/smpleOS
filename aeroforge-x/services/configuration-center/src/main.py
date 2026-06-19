import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.config_controller import router as config_router
from .infrastructure.database import Database
from .infrastructure.event_bus import EventBus


database = Database()
event_bus = EventBus()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await event_bus.connect()
    yield
    await event_bus.disconnect()
    await database.disconnect()


app = FastAPI(
    title="AeroForge-X Configuration Management Center",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "database": database.is_connected(),
        "nats": event_bus.is_connected(),
    }