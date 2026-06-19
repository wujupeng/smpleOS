import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.knowledge_controller import router as knowledge_router
from .api.knowledge_graph_controller import router as kg_router
from .api.knowledge_analysis_controller import router as analysis_router
from .infrastructure.neo4j_client import Neo4jClient
from .infrastructure.database import Database
from .infrastructure.minio_client import MinioClient
from .infrastructure.event_bus import EventBus


neo4j_client = Neo4jClient()
database = Database()
minio_client = MinioClient()
event_bus = EventBus()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await neo4j_client.connect()
    await minio_client.connect()
    await event_bus.connect()
    yield
    await event_bus.disconnect()
    await neo4j_client.disconnect()
    await database.disconnect()


app = FastAPI(
    title="AeroForge-X Knowledge Center",
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

app.include_router(knowledge_router)
app.include_router(kg_router)
app.include_router(analysis_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "neo4j": neo4j_client.is_connected(),
        "database": database.is_connected(),
        "nats": event_bus.is_connected(),
    }
