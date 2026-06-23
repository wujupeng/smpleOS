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


@router.get("/trace/dashboard")
async def get_trace_dashboard():
    try:
        from src.infrastructure.database import get_pg_pool
        pool = await get_pg_pool()

        total_blocks = await pool.fetchval("SELECT COUNT(*) FROM block_configurations")
        blocks_with_material = await pool.fetchval("SELECT COUNT(DISTINCT block_id) FROM dt_block_materials")
        thread_coverage = (blocks_with_material / total_blocks * 100) if total_blocks > 0 else 0.0

        max_depth = 0
        try:
            svc = await get_trace_graph_service()
            nodes = await svc._node_repo.find_all(limit=10000)
            edges = await svc._edge_repo.find_all(limit=10000)
            adj: dict[str, list[str]] = {}
            for e in edges:
                adj.setdefault(e.source_node_id, []).append(e.target_node_id)
            for n in nodes:
                if n.node_id not in adj:
                    continue
                visited = {n.node_id}
                queue = [(n.node_id, 0)]
                while queue:
                    cur, d = queue.pop(0)
                    if d > max_depth:
                        max_depth = d
                    for nxt in adj.get(cur, []):
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append((nxt, d + 1))
        except Exception:
            pass

        open_car_count = await pool.fetchval("SELECT COUNT(*) FROM dt_corrective_actions WHERE status = 'open'")
        total_car_count = await pool.fetchval("SELECT COUNT(*) FROM dt_corrective_actions")

        total_requirements = await pool.fetchval("SELECT COUNT(*) FROM dt_compliance_requirements")
        compliant_count = await pool.fetchval("SELECT COUNT(*) FROM dt_compliance_requirements WHERE compliance_status = 'compliant'")
        compliance_progress = (compliant_count / total_requirements * 100) if total_requirements > 0 else 0.0

        return {
            "thread_coverage": round(thread_coverage, 1),
            "total_blocks": total_blocks,
            "blocks_traced": blocks_with_material or 0,
            "trace_depth": max_depth,
            "open_cars": open_car_count or 0,
            "total_cars": total_car_count or 0,
            "compliance_progress": round(compliance_progress, 1),
            "total_requirements": total_requirements or 0,
            "compliant_requirements": compliant_count or 0,
        }
    except Exception as e:
        logger.error(f"Dashboard query failed: {e}")
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