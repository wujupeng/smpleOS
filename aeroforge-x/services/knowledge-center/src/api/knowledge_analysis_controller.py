from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from ..domain.services.knowledge_graph_service import KnowledgeGraphService
from ..domain.services.impact_propagation_engine import ImpactPropagationEngine
from ..domain.services.knowledge_inference_engine import KnowledgeInferenceEngine
from ..domain.services.knowledge_quality_service import KnowledgeQualityService
from ..domain.services.knowledge_search_service import KnowledgeSearchService
from ..domain.services.graph_snapshot_service import GraphSnapshotService

router = APIRouter(prefix="/api/v1/knowledge-graph", tags=["Knowledge Analysis"])

_kg_service = KnowledgeGraphService()
_impact_engine = ImpactPropagationEngine()
_inference_engine = KnowledgeInferenceEngine()
_quality_service = KnowledgeQualityService()
_search_service = KnowledgeSearchService()
_snapshot_service = GraphSnapshotService()


class ImpactAnalysisRequest(BaseModel):
    graph_id: str
    source_node_id: str
    depth: int = Field(default=3, ge=1, le=10)
    link_types: list[str] | None = None


class InferenceRequest(BaseModel):
    graph_id: str
    input_node_ids: list[str]
    reasoning_type: str = "transitive"


class SemanticSearchRequest(BaseModel):
    graph_id: str
    query_embedding: list[float]
    top_k: int = Field(default=10, ge=1, le=100)
    node_type: str | None = None
    min_confidence: float = Field(default=0.0, ge=0, le=1)


class HybridSearchRequest(BaseModel):
    graph_id: str
    query: str
    query_embedding: list[float] | None = None
    top_k: int = Field(default=10, ge=1, le=100)
    node_type: str | None = None


class CreateSnapshotRequest(BaseModel):
    graph_id: str
    name: str = ""
    description: str = ""
    created_by: str | None = None


class RestoreSnapshotRequest(BaseModel):
    graph_id: str
    snapshot_id: str


class CompareSnapshotsRequest(BaseModel):
    graph_id: str
    snapshot_a_id: str
    snapshot_b_id: str


@router.post("/impact-analysis")
async def impact_analysis(req: ImpactAnalysisRequest):
    graph = _kg_service.get_graph(req.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    result = _impact_engine.propagate_impact(
        graph, req.source_node_id, depth=req.depth, link_types=req.link_types
    )
    return result.to_dict()


@router.get("/nodes/{node_id}/neighbors")
async def get_neighbors(node_id: str, graph_id: str, depth: int = 1):
    try:
        nodes = _kg_service.get_neighbors(graph_id, node_id, depth)
        return {
            "neighbors": [
                {"node_id": n.node_id, "node_type": n.node_type, "name": n.name}
                for n in nodes
            ],
            "total": len(nodes),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/snapshots")
async def create_snapshot(req: CreateSnapshotRequest):
    graph = _kg_service.get_graph(req.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    snapshot = _snapshot_service.create_snapshot(
        graph, name=req.name, description=req.description, created_by=req.created_by
    )
    return {
        "snapshot_id": snapshot.snapshot_id,
        "name": snapshot.name,
        "node_count": snapshot.node_count,
        "link_count": snapshot.link_count,
        "checksum": snapshot.checksum,
    }


@router.get("/snapshots")
async def list_snapshots(graph_id: str):
    return {"snapshots": [], "total": 0}


@router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, req: RestoreSnapshotRequest):
    return {"status": "restored", "snapshot_id": snapshot_id}


@router.get("/statistics")
async def graph_statistics(graph_id: str):
    graph = _kg_service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    nodes = graph.get_all_nodes()
    links = graph.get_all_links()
    type_dist = {}
    for n in nodes:
        type_dist[n.node_type] = type_dist.get(n.node_type, 0) + 1
    link_type_dist = {}
    for l in links:
        link_type_dist[l.link_type] = link_type_dist.get(l.link_type, 0) + 1
    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "node_type_distribution": type_dist,
        "link_type_distribution": link_type_dist,
    }


@router.post("/search/semantic")
async def semantic_search(req: SemanticSearchRequest):
    graph = _kg_service.get_graph(req.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    results = _search_service.semantic_search(
        graph, req.query_embedding, top_k=req.top_k,
        node_type=req.node_type, min_confidence=req.min_confidence,
    )
    return {
        "results": [
            {"node_id": n.node_id, "node_type": n.node_type, "name": n.name, "score": round(s, 4)}
            for n, s in results
        ],
        "total": len(results),
    }


@router.post("/search/hybrid")
async def hybrid_search(req: HybridSearchRequest):
    graph = _kg_service.get_graph(req.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    results = _search_service.hybrid_search(
        graph, req.query, query_embedding=req.query_embedding,
        top_k=req.top_k, node_type=req.node_type,
    )
    return {
        "results": [
            {"node_id": n.node_id, "node_type": n.node_type, "name": n.name, "score": round(s, 4)}
            for n, s in results
        ],
        "total": len(results),
    }


@router.get("/quality")
async def quality_assessment(graph_id: str):
    graph = _kg_service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    metrics = _quality_service.assess_quality(graph)
    return metrics.to_dict()


@router.get("/anomalies")
async def list_anomalies(graph_id: str):
    graph = _kg_service.get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    anomalies = _quality_service.detect_anomalies(graph)
    return {
        "anomalies": [a.to_dict() for a in anomalies],
        "total": len(anomalies),
    }


@router.post("/inference")
async def run_inference(req: InferenceRequest):
    graph = _kg_service.get_graph(req.graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    result = _inference_engine.infer_links(
        graph, req.input_node_ids, reasoning_type=req.reasoning_type
    )
    return result.to_dict()