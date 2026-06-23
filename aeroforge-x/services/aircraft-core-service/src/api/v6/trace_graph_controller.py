from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.domain.services.trace_graph_service import get_trace_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Trace Graph"])


@router.get("/trace/query")
async def trace_query(start_node_id: str, direction: str = "both", max_depth: int = 5, max_nodes: int = 100):
    try:
        svc = await get_trace_graph_service()
        return await svc.trace_query(start_node_id, direction, max_depth, max_nodes)
    except Exception as e:
        logger.error(f"Trace query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/impact/{node_id}")
async def impact_analysis(node_id: str, max_depth: int = 5):
    try:
        svc = await get_trace_graph_service()
        return await svc.impact_analysis(node_id, max_depth)
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/dependencies/{node_id}")
async def dependency_query(node_id: str, max_depth: int = 5):
    try:
        svc = await get_trace_graph_service()
        return await svc.dependency_query(node_id, max_depth)
    except Exception as e:
        logger.error(f"Dependency query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace/rebuild")
async def rebuild_graph():
    try:
        svc = await get_trace_graph_service()
        return await svc.rebuild_graph()
    except Exception as e:
        logger.error(f"Graph rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/statistics")
async def get_trace_statistics():
    try:
        svc = await get_trace_graph_service()
        return await svc.get_statistics()
    except Exception as e:
        logger.error(f"Statistics query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/nodes")
async def list_trace_nodes(node_type: str = None, limit: int = 100, offset: int = 0):
    try:
        from src.infrastructure.repositories.trace_node_repository import TraceNodeRepository
        from src.infrastructure.database import get_pg_pool
        pool = await get_pg_pool()
        repo = TraceNodeRepository(pool)
        nodes = await repo.find_all(limit=limit, offset=offset)
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        return [n.to_dict() for n in nodes]
    except Exception as e:
        logger.error(f"List nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trace/nodes/{node_id}")
async def get_trace_node(node_id: str):
    try:
        svc = await get_trace_graph_service()
        node = svc._cache.get_node(node_id)
        if node:
            return node.to_dict()
        from src.infrastructure.repositories.trace_node_repository import TraceNodeRepository
        from src.infrastructure.database import get_pg_pool
        pool = await get_pg_pool()
        repo = TraceNodeRepository(pool)
        node = await repo.find_by_id(node_id)
        if node is None:
            raise HTTPException(status_code=404, detail=f"Trace node not found: {node_id}")
        return node.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Node query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))