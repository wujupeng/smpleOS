from __future__ import annotations

from fastapi import APIRouter

from src.infrastructure.graph_client import graph_client

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Configuration Identity Graph"])


@router.get("/config-identity-graphs/{aircraft_type}")
async def get_identity_graph(aircraft_type: str):
    result = await graph_client.query_identity_graph(aircraft_type)
    if not result.get("neo4j_available", False):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Neo4j is not available")
    return result